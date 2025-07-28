import discord
from discord.ext import commands
import asyncio
import os
from threading import Thread
from flask import Flask

# 환경변수 로드 시도
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Render에서는 dotenv가 필요없음
    pass

# Flask 앱 생성 (웹서비스로 유지하기 위해)
app = Flask(__name__)

@app.route('/')
def home():
    return "Discord Bot is running!"

@app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 봇이 준비되었을 때
@bot.event
async def on_ready():
    print(f'{bot.user}로 로그인했습니다!')
    print(f'봇이 {len(bot.guilds)}개의 서버에 연결되어 있습니다.')
    
    # 모든 길드에서 슬래시 커맨드 동기화
    try:
        synced = await bot.tree.sync()
        print(f"슬래시 커맨드 {len(synced)}개 동기화 완료")
    except Exception as e:
        print(f"슬래시 커맨드 동기화 실패: {e}")

# 멤버가 서버에 참가했을 때
@bot.event
async def on_member_join(member):
    guild = member.guild
    
    try:
        print(f"새 멤버 참가: {member.name} (ID: {member.id})")
        
        # 스튜어디스 역할 찾기 (없으면 생성)
        stewardess_role = discord.utils.get(guild.roles, name="스튜어디스")
        if not stewardess_role:
            try:
                stewardess_role = await guild.create_role(
                    name="스튜어디스", 
                    color=discord.Color.blue(),
                    reason="프라이빗 룸 시스템용 역할 생성"
                )
                print(f"스튜어디스 역할 생성 완료")
            except discord.Forbidden:
                print("역할 생성 권한이 없습니다!")
                return
        
        # 프라이빗 룸 카테고리 찾기 (없으면 생성)
        category = discord.utils.get(guild.categories, name="프라이빗 룸")
        if not category:
            try:
                category = await guild.create_category(
                    "프라이빗 룸",
                    reason="프라이빗 룸 시스템용 카테고리 생성"
                )
                print(f"프라이빗 룸 카테고리 생성 완료")
            except discord.Forbidden:
                print("카테고리 생성 권한이 없습니다!")
                return
        
        # 권한 설정
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            stewardess_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # 채널 생성 (채널명에서 특수문자 제거)
        clean_name = "".join(c for c in member.display_name if c.isalnum() or c in ("-", "_"))
        if not clean_name:
            clean_name = str(member.id)
        
        channel_name = f"괄자-애정듬뿍-{clean_name}"[:100]  # 디스코드 채널명 길이 제한
        
        try:
            private_channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"{member.name}님을 위한 프라이빗 룸 생성"
            )
            print(f"프라이빗 채널 생성 완료: {private_channel.name}")
        except discord.Forbidden:
            print("채널 생성 권한이 없습니다!")
            return
        
        # 첫 번째 안내문
        embed1 = discord.Embed(
            title="# 프라이빗룸",
            description=f"**{member.mention} 고객님의 좌석 등급이 퍼스트로 올라 프라이빗 룸이 생성됐어요**\n\n"
                       f"**이 대화방은 저희 {stewardess_role.mention} 와 당신만 보이는 프라이빗 룸입니다.**\n\n"
                       f"-# 관리자랑 {member.mention}고객님만 보여요!\n\n"
                       f"단 {stewardess_role.mention}의 부름에 대답이 없으실 경우 좌석등급이 하향될수있습니다\n\n"
                       f"-# 좌석 등급 하향은 서버 추방입니다",
            color=discord.Color.gold()
        )
        
        await private_channel.send(embed=embed1)
        print(f"첫 번째 안내문 전송 완료")
        
        # 10초 후 두 번째 안내문과 버튼
        await asyncio.sleep(10)
        
        embed2 = discord.Embed(
            title="# 즐거운 식사시간~!",
            description="**## 서버는 입맛에 맞으신가요?**\n\n"
                       "서버가 입맛에 맞으시다면 **한식** 버튼을\n"
                       "서버가 입맛에 맞지 않으시다면 **승무원** 버튼을 눌러주세요\n\n"
                       "-# 승무원 버튼을 누르시면 고객님을 위한 특별 기내식을 준비해드리겠습니다!",
            color=discord.Color.green()
        )
        
        view = MealButtonView(member, stewardess_role, private_channel)
        await private_channel.send(embed=embed2, view=view)
        print(f"두 번째 안내문과 버튼 전송 완료")
        
    except Exception as e:
        print(f"새 멤버 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

class MealButtonView(discord.ui.View):
    def __init__(self, member, stewardess_role, channel):
        super().__init__(timeout=300)  # 5분 타임아웃
        self.member = member
        self.stewardess_role = stewardess_role
        self.channel = channel

    async def on_timeout(self):
        # 타임아웃 시 버튼 비활성화
        for item in self.children:
            item.disabled = True
        
        try:
            # 마지막 메시지를 찾아서 수정
            async for message in self.channel.history(limit=10):
                if message.author == self.channel.guild.me and message.embeds and len(message.embeds) > 0:
                    if "즐거운 식사시간" in message.embeds[0].title:
                        await message.edit(view=self)
                        break
        except Exception as e:
            print(f"타임아웃 처리 중 오류: {e}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.member:
            await interaction.response.send_message("이 버튼은 당신을 위한 것이 아닙니다.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label='한식', style=discord.ButtonStyle.primary, emoji='🍚')
    async def korean_food(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="# 당신은 공항에 입장하실 수 있습니다",
            description="**## 서버원들과 좀더 친해지고싶으시다면 버튼을 눌러주세요**\n\n"
                       "-# 공항이 보이는건 자율적입니다. 울타리 친목이 존재하는 곳이니 이점 숙지 바랍니다.\n"
                       "추후에 공항 채널을 안보이게 하고싶으시다면 #요청사항 의 티켓을 열어 @정규직 을 태그해 알려주시기 바랍니다",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
        
        # 버튼 비활성화
        for item in self.children:
            item.disabled = True
        
        # 원본 메시지의 버튼 업데이트
        try:
            await interaction.followup.edit_message(interaction.message.id, view=self)
        except:
            pass
        
        # 15초 후 최종 버튼 보내기
        await asyncio.sleep(15)
        await self.send_final_message()

    @discord.ui.button(label='승무원', style=discord.ButtonStyle.secondary, emoji='✈️')
    async def stewardess(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            description=f"**저희 {self.stewardess_role.mention} 가 고객님의 입맛에 맞는 특별 기내식을 준비중입니다! 기대해주세요**\n🍳",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
        
        # 버튼 비활성화
        for item in self.children:
            item.disabled = True
        
        # 원본 메시지의 버튼 업데이트
        try:
            await interaction.followup.edit_message(interaction.message.id, view=self)
        except:
            pass
        
        # 15초 후 최종 버튼 보내기
        await asyncio.sleep(15)
        await self.send_final_message()

    async def send_final_message(self):
        try:
            final_view = FinalButtonView(self.member, self.channel)
            final_embed = discord.Embed(
                title="# 목적지에 도착하셨습니다!",
                description="서버에 적응을 하셨다면 **삭제** 버튼을\n\n"
                           "-# 서버적응에 가이드가 필요하시다면 **유지** 버튼을 눌러주세요! 가이드는 무료입니다!",
                color=discord.Color.purple()
            )
            await self.channel.send(embed=final_embed, view=final_view)
        except Exception as e:
            print(f"최종 메시지 전송 중 오류: {e}")

class FinalButtonView(discord.ui.View):
    def __init__(self, member, channel):
        super().__init__(timeout=None)  # 영구적으로 유지
        self.member = member
        self.channel = channel

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.member:
            await interaction.response.send_message("이 버튼은 당신을 위한 것이 아닙니다.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label='삭제', style=discord.ButtonStyle.danger, emoji='🗑️')
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("프라이빗 룸이 곧 삭제됩니다. 감사합니다! 👋")
        
        await asyncio.sleep(3)
        
        try:
            await self.channel.delete(reason=f"{self.member.name}님이 프라이빗 룸 삭제를 요청했습니다.")
        except discord.NotFound:
            pass  # 채널이 이미 삭제된 경우
        except Exception as e:
            print(f"채널 삭제 중 오류: {e}")

    @discord.ui.button(label='유지', style=discord.ButtonStyle.success, emoji='💚')
    async def keep_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎉 가이드 서비스",
            description="프라이빗 룸이 유지됩니다!\n언제든지 스튜어디스에게 문의하세요! 😊",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        
        # 버튼 비활성화
        for item in self.children:
            item.disabled = True
        
        try:
            await interaction.edit_original_response(view=self)
        except:
            pass

# 슬래시 커맨드들
@bot.tree.command(name="테스트", description="봇이 정상 작동하는지 확인합니다")
async def test_slash(interaction: discord.Interaction):
    await interaction.response.send_message("✅ 봇이 정상적으로 작동중입니다!", ephemeral=True)

@bot.tree.command(name="참가시뮬레이션", description="새 멤버 참가를 시뮬레이션합니다")
async def simulate_join_slash(interaction: discord.Interaction, 멤버: discord.Member = None):
    if not 멤버:
        멤버 = interaction.user
    
    await interaction.response.send_message(f"🔄 {멤버.mention}님의 참가를 시뮬레이션합니다...", ephemeral=True)
    await on_member_join(멤버)

# 기존 명령어들 (호환성을 위해)
@bot.command(name='test')
async def test_command(ctx):
    """테스트 명령어 - 봇이 작동하는지 확인"""
    await ctx.send("✅ 봇이 정상적으로 작동중입니다!")

@bot.command(name='simulate_join')
async def simulate_join(ctx, member: discord.Member = None):
    """새 멤버 참가 시뮬레이션 (테스트용)"""
    if not member:
        member = ctx.author
    
    await ctx.send(f"🔄 {member.mention}님의 참가를 시뮬레이션합니다...")
    await on_member_join(member)

# 에러 핸들링
@bot.event
async def on_error(event, *args, **kwargs):
    print(f'❌ 에러 발생 - 이벤트: {event}')
    import traceback
    traceback.print_exc()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # 존재하지 않는 명령어는 무시
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ 필수 인수가 누락되었습니다.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 이 명령어를 사용할 권한이 없습니다.")
    else:
        print(f'❌ 명령어 에러: {error}')
        await ctx.send("❌ 명령어 처리 중 오류가 발생했습니다.")

# 봇 및 Flask 서버 실행
if __name__ == "__main__":
    # 환경변수에서 토큰 가져오기
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ DISCORD_BOT_TOKEN 환경변수를 설정해주세요!")
        print("💡 .env 파일에 DISCORD_BOT_TOKEN=your_token_here 형식으로 입력하세요.")
        exit(1)
    
    print("🚀 디스코드 프라이빗룸 봇을 시작합니다...")
    print(f"🐍 Python 버전: {os.sys.version}")
    
    # Flask 서버를 별도 스레드에서 실행
    try:
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        print("🌐 Flask 서버가 시작되었습니다.")
    except Exception as e:
        print(f"⚠️ Flask 서버 시작 실패: {e}")
    
    # 디스코드 봇 실행
    try:
        bot.run(TOKEN, log_handler=None)  # 기본 로깅 비활성화
    except discord.LoginFailure:
        print("❌ 잘못된 봇 토큰입니다! 토큰을 다시 확인해주세요.")
    except discord.HTTPException as e:
        print(f"❌ Discord API 오류: {e}")
    except Exception as e:
        print(f"❌ 봇 실행 중 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()

class FinalButtonView(discord.ui.View):
    def __init__(self, member, channel):
        super().__init__(timeout=None)  # 영구적으로 유지
        self.member = member
        self.channel = channel

    @discord.ui.button(label='삭제', style=discord.ButtonStyle.danger, emoji='🗑️')
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.member:
            await interaction.response.send_message("이 버튼은 당신을 위한 것이 아닙니다.", ephemeral=True)
            return
        
        await interaction.response.send_message("프라이빗 룸이 곧 삭제됩니다. 감사합니다!")
        await asyncio.sleep(3)
        try:
            await self.channel.delete()
        except discord.NotFound:
            pass  # 채널이 이미 삭제된 경우
        except Exception as e:
            print(f"채널 삭제 중 오류: {e}")

    @discord.ui.button(label='유지', style=discord.ButtonStyle.success, emoji='💚')
    async def keep_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.member:
            await interaction.response.send_message("이 버튼은 당신을 위한 것이 아닙니다.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="가이드 서비스",
            description="프라이빗 룸이 유지됩니다. 언제든지 스튜어디스에게 문의하세요!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        
        # 버튼 비활성화
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

# 디버깅을 위한 명령어들
@bot.command(name='test')
async def test_command(ctx):
    """테스트 명령어 - 봇이 작동하는지 확인"""
    await ctx.send("봇이 정상적으로 작동중입니다! ✅")

@bot.command(name='simulate_join')
async def simulate_join(ctx, member: discord.Member = None):
    """새 멤버 참가 시뮬레이션 (테스트용)"""
    if not member:
        member = ctx.author
    
    await on_member_join(member)
    await ctx.send(f"{member.mention}의 참가를 시뮬레이션했습니다.")

# 에러 핸들링
@bot.event
async def on_error(event, *args, **kwargs):
    print(f'에러 발생 - 이벤트: {event}, 인수: {args}')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # 존재하지 않는 명령어는 무시
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("필수 인수가 누락되었습니다.")
    else:
        print(f'명령어 에러: {error}')
        await ctx.send("명령어 처리 중 오류가 발생했습니다.")

# 봇 및 Flask 서버 실행
if __name__ == "__main__":
    # 환경변수에서 토큰 가져오기
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_BOT_TOKEN 환경변수를 설정해주세요!")
        exit(1)
    else:
        print("🚀 봇을 시작합니다...")
        
        # Flask 서버를 별도 스레드에서 실행
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        print("🌐 Flask 서버가 시작되었습니다.")
        
        # 디스코드 봇 실행
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            print("❌ 잘못된 봇 토큰입니다!")
        except Exception as e:
            print(f"❌ 봇 실행 중 오류 발생: {e}")
