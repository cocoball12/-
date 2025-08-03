import discord
from discord.ext import commands
import asyncio
import os
from threading import Thread
from flask import Flask
import json
from datetime import datetime

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

# 처리 중인 멤버를 추적하는 집합 (중복 방지용)
processing_members = set()

# 사용자 데이터를 저장할 딕셔너리 (메모리 기반)
user_data = {}

def save_user_join(guild_id, user_id):
    """사용자 입장 기록 저장"""
    key = f"{guild_id}_{user_id}"
    current_time = datetime.now().isoformat()
    
    if key not in user_data:
        user_data[key] = {
            'first_join': current_time,
            'join_count': 1,
            'last_join': current_time
        }
    else:
        user_data[key]['join_count'] += 1
        user_data[key]['last_join'] = current_time

def is_first_join(guild_id, user_id):
    """처음 입장인지 확인"""
    key = f"{guild_id}_{user_id}"
    return key not in user_data

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

# 멤버가 서버에서 나갔을 때
@bot.event
async def on_member_remove(member):
    guild = member.guild
    print(f"멤버 퇴장: {member.name} (ID: {member.id})")
    
    try:
        # 해당 멤버의 프라이빗 룸 찾기 및 삭제
        member_display_name = member.display_name
        deleted_channels = []
        
        # 프라이빗 룸 카테고리에서 해당 멤버의 채널 찾기
        private_category = discord.utils.get(guild.categories, name="프라이빗 룸")
        if private_category:
            for channel in private_category.text_channels:
                # 채널명이 해당 멤버와 관련된지 확인 (새로운 형식)
                if (channel.name.startswith(f"프라이빗룸-") and (f"-{member_display_name}" in channel.name) or
                    member in channel.overwrites):
                    try:
                        await channel.delete(reason=f"{member.name}님이 서버를 나가서 프라이빗 룸 삭제")
                        deleted_channels.append(f"프라이빗 룸: {channel.name}")
                        print(f"프라이빗 룸 삭제: {channel.name}")
                    except Exception as e:
                        print(f"프라이빗 룸 삭제 실패: {channel.name}, 오류: {e}")
        
        # 패키지 여행 카테고리에서 해당 멤버의 채널 찾기
        package_category = discord.utils.get(guild.categories, name="패키지 여행")
        if package_category:
            for channel in package_category.text_channels:
                # 채널명이 해당 멤버와 관련된지 확인
                if (channel.name.startswith(f"패키지여행-{member_display_name}") or
                    member in channel.overwrites):
                    try:
                        await channel.delete(reason=f"{member.name}님이 서버를 나가서 패키지 여행 채널 삭제")
                        deleted_channels.append(f"패키지 여행: {channel.name}")
                        print(f"패키지 여행 채널 삭제: {channel.name}")
                    except Exception as e:
                        print(f"패키지 여행 채널 삭제 실패: {channel.name}, 오류: {e}")
        
        # 닉네임으로도 한번 더 검색 (display_name과 다를 수 있음)
        member_name = member.name
        if member_name != member_display_name:
            # 프라이빗 룸에서 멤버 이름으로 검색
            if private_category:
                for channel in private_category.text_channels:
                    if channel.name.startswith(f"프라이빗룸-") and f"-{member_name}" in channel.name:
                        try:
                            await channel.delete(reason=f"{member.name}님이 서버를 나가서 프라이빗 룸 삭제")
                            deleted_channels.append(f"프라이빗 룸: {channel.name}")
                            print(f"프라이빗 룸 삭제 (이름 기준): {channel.name}")
                        except Exception as e:
                            print(f"프라이빗 룸 삭제 실패 (이름 기준): {channel.name}, 오류: {e}")
            
            # 패키지 여행에서 멤버 이름으로 검색
            if package_category:
                for channel in package_category.text_channels:
                    if channel.name.startswith(f"패키지여행-{member_name}"):
                        try:
                            await channel.delete(reason=f"{member.name}님이 서버를 나가서 패키지 여행 채널 삭제")
                            deleted_channels.append(f"패키지 여행: {channel.name}")
                            print(f"패키지 여행 채널 삭제 (이름 기준): {channel.name}")
                        except Exception as e:
                            print(f"패키지 여행 채널 삭제 실패 (이름 기준): {channel.name}, 오류: {e}")
        
        if deleted_channels:
            print(f"총 {len(deleted_channels)}개 채널 삭제 완료: {', '.join(deleted_channels)}")
        else:
            print(f"{member.name}님과 관련된 채널을 찾지 못했습니다.")
            
    except Exception as e:
        print(f"멤버 퇴장 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

# 멤버가 서버에 참가했을 때
@bot.event
async def on_member_join(member):
    guild = member.guild
    member_key = f"{guild.id}_{member.id}"
    
    # 이미 처리 중인 멤버인지 확인
    if member_key in processing_members:
        print(f"이미 처리 중인 멤버입니다: {member.name}")
        return
    
    # 처리 중 목록에 추가
    processing_members.add(member_key)
    
    try:
        # 처음 입장인지 재입장인지 확인 (데이터 저장 전에 확인)
        is_first = is_first_join(guild.id, member.id)
        join_status = "첫입장" if is_first else "재입장"
        
        print(f"새 멤버 참가: {member.name} (ID: {member.id}) - {join_status}")
        
        # 입장 기록 저장 (확인 후에 저장)
        save_user_join(guild.id, member.id)
        
        # 서버에서 사용하는 실제 닉네임 가져오기 (display_name 사용)
        member_display_name = member.display_name
        
        # 기존 채널 확인 (중복 생성 방지 강화)
        existing_channel = None
        
        # 전체 길드에서 해당 멤버의 프라이빗 룸 검색
        for channel in guild.text_channels:
            if channel.name.startswith("프라이빗룸-"):
                # 채널 권한에서 해당 멤버가 있는지 먼저 확인 (더 정확함)
                overwrites = channel.overwrites
                if member in overwrites:
                    # 권한이 있는 채널 중에서 이름도 매칭되는지 확인
                    if (f"-{member_display_name}" in channel.name or 
                        f"-{member.name}" in channel.name or
                        member.display_name.lower() in channel.name.lower() or
                        member.name.lower() in channel.name.lower()):
                        existing_channel = channel
                        break
        
        # 기존 채널이 있으면 중복 생성하지 않음
        if existing_channel:
            print(f"이미 {member.name}님의 프라이빗 룸이 존재합니다: {existing_channel.name}")
            # 기존 채널에 알림 메시지 전송
            try:
                await existing_channel.send(f"{member.mention}님이 다시 서버에 참가하셨습니다! 🎉")
            except:
                pass
            processing_members.discard(member_key)
            return
        
        # 스튜어디스 역할 찾기 
        stewardess_role = discord.utils.get(guild.roles, name="스튜어디스")
        
        # 스카이호스트 역할 찾기 
        skyhost_role = discord.utils.get(guild.roles, name="스카이호스트")
        
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
                processing_members.discard(member_key)
                return
        
        # 권한 설정 - 본인, 스카이호스트, 스튜어디스만 볼 수 있도록
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),  # 모든 사람 차단
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),  # 본인만 허용
            stewardess_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),  # 스튜어디스 허용
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)  # 봇 자신도 허용
        }
        
        # 스카이호스트 역할이 있으면 권한 추가
        if skyhost_role:
            overwrites[skyhost_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # 새로운 채널명 형식: 프라이빗룸-(첫입장/재입장)-서버닉네임
        channel_name = f"프라이빗룸-{join_status}-{member_display_name}"
        # 특수문자 제거 및 길이 제한
        channel_name = "".join(c for c in channel_name if c.isalnum() or c in ("-", "_"))[:100]
        
        try:
            # 채널 생성 직전에 한 번 더 확인
            for channel in guild.text_channels:
                if (channel.name.startswith("프라이빗룸-") and 
                    (f"-{member_display_name}" in channel.name or f"-{member.name}" in channel.name) and
                    member in channel.overwrites):
                    print(f"채널 생성 직전 중복 발견: {channel.name}")
                    processing_members.discard(member_key)
                    return
            
            private_channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"{member.name}님을 위한 프라이빗 룸 생성"
            )
            print(f"프라이빗 채널 생성 완료: {private_channel.name} (ID: {private_channel.id})")
            
            # 채널 생성 후 충분한 시간 대기 (3초)
            await asyncio.sleep(3)
            
            # 중복 채널 확인 및 정리 (방금 생성한 채널은 절대 삭제하지 않음)
            duplicate_channels = []
            for channel in guild.text_channels:
                if (channel.name.startswith("프라이빗룸-") and 
                    (f"-{member_display_name}" in channel.name or f"-{member.name}" in channel.name) and
                    member in channel.overwrites and
                    channel.id != private_channel.id and  # 방금 생성한 채널은 제외
                    channel.created_at < private_channel.created_at):  # 더 오래된 채널만 선택
                    duplicate_channels.append(channel)
            
            # 중복 채널이 있으면 삭제
            if duplicate_channels:
                print(f"중복 채널 {len(duplicate_channels)}개 발견")
                for old_channel in duplicate_channels:
                    try:
                        print(f"중복 채널 삭제 시도: {old_channel.name} (ID: {old_channel.id})")
                        await old_channel.delete(reason=f"중복 프라이빗 룸 정리 - {member.name}")
                        print(f"중복 채널 삭제 완료: {old_channel.name}")
                    except Exception as e:
                        print(f"중복 채널 삭제 실패: {old_channel.name}, 오류: {e}")
            else:
                print("중복 채널 없음")
                        
        except discord.Forbidden:
            print("채널 생성 권한이 없습니다!")
            processing_members.discard(member_key)
            return
        except Exception as e:
            print(f"채널 생성 중 오류: {e}")
            processing_members.discard(member_key)
            return
        
        # 입장 상태에 따른 메시지 조정
        join_status_emoji = "🎉" if is_first else "🔄"
        join_status_text = "처음 오신 것을 환영합니다!" if is_first else "다시 오신 것을 환영합니다!"
        
        # 첫 번째 안내문 (일반 메시지로 변경)
        message1 = f"**프라이빗룸 {join_status_emoji}**\n\n"
        message1 += f"**이 대화방은 저희 {stewardess_role.mention} 와 당신만 보이는 프라이빗 룸입니다.**\n\n"
        message1 += f"-# 관리자랑 {member.mention}고객님만 보여요!\n\n"
        message1 += f"단 {stewardess_role.mention}의 부름에 대답이 없으실 경우 좌석등급이 하향될수있습니다\n\n"
        message1 += f"-# 좌석 등급 하향은 서버 추방입니다"
        
        await private_channel.send(message1)
        print(f"첫 번째 안내문 전송 완료")
        
        # 10초 후 두 번째 안내문과 버튼
        await asyncio.sleep(10)
        
        message2 = "**즐거운 식사시간~!**\n\n"
        message2 += "**## 서버는 입맛에 맞으신가요?**\n\n"
        message2 += "서버가 입맛에 맞으시다면 **🍚한식** 버튼을\n"
        message2 += "서버가 입맛에 맞지 않으시다면 **🆘승무원** 버튼을 눌러주세요\n\n"
        message2 += "-# 승무원 버튼을 누르시면 고객님을 위한 특별 기내식을 준비해드리겠습니다!"
        
        view = MealButtonView(member, stewardess_role, private_channel, is_first)
        await private_channel.send(message2, view=view)
        print(f"두 번째 안내문과 버튼 전송 완료")
        
    except Exception as e:
        print(f"새 멤버 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 처리 완료 후 목록에서 제거
        processing_members.discard(member_key)

class MealButtonView(discord.ui.View):
    def __init__(self, member, stewardess_role, channel, is_first_join=True):
        super().__init__(timeout=172800)  # 48시간 타임아웃
        self.member = member
        self.stewardess_role = stewardess_role
        self.channel = channel
        self.is_first_join = is_first_join
        self.used = False  # 버튼이 사용되었는지 확인

    async def on_timeout(self):
        # 타임아웃 시 버튼 비활성화
        for item in self.children:
            item.disabled = True
        
        try:
            # 마지막 봇 메시지를 찾아서 수정
            async for message in self.channel.history(limit=10):
                if message.author == self.channel.guild.me and message.view:
                    await message.edit(view=self)
                    break
        except Exception as e:
            print(f"타임아웃 처리 중 오류: {e}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.member:
            await interaction.response.send_message("이 버튼은 당신을 위한 것이 아닙니다.", ephemeral=True)
            return False
        if self.used:
            await interaction.response.send_message("이미 선택하셨습니다.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label='한식', style=discord.ButtonStyle.primary, emoji='🍚')
    async def korean_food(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.used = True  # 버튼 사용됨 표시
        
        # 디생러 역할 찾기 또는 생성
        guild = interaction.guild
        designer_role = discord.utils.get(guild.roles, name="디생러")
        if not designer_role:
            try:
                designer_role = await guild.create_role(
                    name="디생러",
                    color=discord.Color.pink(),
                    reason="한식 버튼 선택자를 위한 역할 생성"
                )
                print(f"디생러 역할 생성 완료")
            except discord.Forbidden:
                print("역할 생성 권한이 없습니다!")
        
        # 디생러 역할 추가
        if designer_role:
            try:
                await self.member.add_roles(designer_role, reason="한식 버튼 선택")
                print(f"{self.member.name}님에게 디생러 역할 추가")
            except discord.Forbidden:
                print(f"역할 추가 권한이 없습니다!")
        
        welcome_text = "서버 적응에 탁월한 당신" if self.is_first_join else "서버에 다시 오신 당신"
        
        response_message = f"{welcome_text} # 공항 채널에 넣어드렸어요. 이곳은 친목 분위기가 형성된 장소지만 친화력 좋은 당신은 잘 녹아들거라 생각합니다.\n\n"
        response_message += "채팅도 잘 치고 사람들과 친해진다면 `마일리지`도 쌓을 수 있어요!!\n"
        response_message += "-# 마일리지는 추후 상품으로 교환 가능합니다.\n\n"
        response_message += "**아직 서버 적응이 더 필요해서** #공항 채널을 안보이게 하고 싶으시면 #요청사항 에서 티켓을 뽑은 뒤 @직장인을 멘션하시고 #공항 채널을 안보이게 해달라고 해주세요."
        
        await interaction.response.send_message(response_message)
        
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

    @discord.ui.button(label='승무원', style=discord.ButtonStyle.secondary, emoji='🆘')
    async def stewardess(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.used = True  # 버튼 사용됨 표시
        
        guild = interaction.guild
        
        # 성별 역할 확인 및 닉네임 변경
        male_role = discord.utils.get(guild.roles, name="남자")
        female_role = discord.utils.get(guild.roles, name="여자")
        
        current_nick = self.member.display_name
        new_nick = current_nick
        
        print(f"승무원 버튼 클릭 - 현재 닉네임: {current_nick}")
        print(f"멤버 역할: {[role.name for role in self.member.roles]}")
        
        # 이미 (애플) 또는 (피치)가 있는지 확인
        if not (current_nick.startswith("(애플)") or current_nick.startswith("(피치)")):
            if male_role and male_role in self.member.roles:
                new_nick = f"(애플) {current_nick}"
                print(f"남자 역할 감지 - 새 닉네임: {new_nick}")
            elif female_role and female_role in self.member.roles:
                new_nick = f"(피치) {current_nick}"
                print(f"여자 역할 감지 - 새 닉네임: {new_nick}")
            else:
                print(f"성별 역할을 찾을 수 없음. 남자 역할: {male_role}, 여자 역할: {female_role}")
            
            # 닉네임 변경 시도
            if new_nick != current_nick:
                try:
                    await self.member.edit(nick=new_nick, reason="승무원 버튼 선택으로 인한 닉네임 변경")
                    print(f"닉네임 변경 성공: {current_nick} -> {new_nick}")
                except discord.Forbidden:
                    print("닉네임 변경 권한이 없습니다.")
                except discord.HTTPException as e:
                    print(f"닉네임 변경 중 HTTP 오류: {e}")
                except Exception as e:
                    print(f"닉네임 변경 중 예상치 못한 오류: {e}")
            else:
                print("닉네임 변경이 필요하지 않습니다.")
        else:
            print("이미 성별 표시가 있는 닉네임입니다.")
        
        response_message = f"**저희 {self.stewardess_role.mention} 가 고객님의 입맛에 맞는 특별 기내식을 준비중입니다! 기대해주세요**🍳\n\n"
        response_message += "    ⠀⣠⡴⣖⡶⣤⣀⠀  ⠀\n"
        response_message += "⠀⠀⣸⢷⣌⣨⣳⠛⣼⡆⠀⠀\n"
        response_message += "⠀⢠⣿⡙⠞⠃⠡⠂⢸⣇⠀⠀\n"
        response_message += "⠀⠈⡄⠠⠘⢀⡄⠃⢌⠠⠀⠀\n"
        response_message += "⠀⠀⠀⠓⣄⠙⢂⡨⠌⠀⠀⠀\n"
        response_message += "⠀⣠⡴⣼⣿⠓⢞⣳⣦⣴⡀⠀\n"
        response_message += "⢠⢿⣽⣳⢿⡈⢠⣿⢚⣱⣿⠀\n"
        response_message += "⣸⣟⡶⢯⣻⣆⢼⡯⢯⡷⣯⡇\n"
        response_message += "⠿⣼⣻⣏⡷⣯⢿⣹⢯⣽⡳⣯\n"
        response_message += "⠈⠳⣗⡯⡷⠯⠏⢿⣽⡺⠝⠀\n"
        response_message += "⠀⠀⣯⠿⣵⣚⣤⣞⠷⣯⠀⠀"
        
        await interaction.response.send_message(response_message)
        
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
            final_message = "**목적지에 도착하셨습니다!**\n\n"
            final_message += "서버에 완벽 적응을 하셨다면 자유여행 버튼🧍을\n\n"
            final_message += "서버적응에 도움이 필요하시다면 패키지 여행버튼👫을 눌러주세요!"
            final_message += " -# 단 가이드는 무료로 제공해드립니다.
            # 각 메시지마다 새로운 뷰 인스턴스 생성
            final_view = FinalButtonView(self.member, self.channel)
            message = await self.channel.send(final_message, view=final_view)
            
            # 메시지 ID를 뷰에 저장하여 나중에 수정할 수 있도록 함
            final_view.message = message
            
            print(f"최종 메시지 전송 완료: {message.id}")
            
        except Exception as e:
            print(f"최종 메시지 전송 중 오류: {e}")
            import traceback
            traceback.print_exc()

class FinalButtonView(discord.ui.View):
    def __init__(self, member, channel):
        super().__init__(timeout=None)  # 영구적으로 유지
        self.member = member
        self.channel = channel
        self.used = False  # 버튼이 사용되었는지 확인
        self.message = None  # 메시지 객체를 저장할 변수

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.member:
            await interaction.response.send_message("본인만 선택할 수 있습니다.", ephemeral=True)
            return False
        if self.used:
            await interaction.response.send_message("이미 선택하셨습니다.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label='자유여행', style=discord.ButtonStyle.danger, emoji='🧍')
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            self.used = True  # 버튼 사용됨 표시
            
            # 버튼 비활성화
            for item in self.children:
                item.disabled = True
            
            # 닉네임에서 (피치), (애플) 제거
            current_nick = self.member.display_name
            new_nick = current_nick
            nick_changed = False
            
            if current_nick.startswith("(피치) "):
                new_nick = current_nick[4:]  # "(피치) " 제거 (4글자)
                nick_changed = True
            elif current_nick.startswith("(애플) "):
                new_nick = current_nick[4:]  # "(애플) " 제거 (4글자)
                nick_changed = True
            
            # 닉네임 변경 시도
            if nick_changed:
                try:
                    await self.member.edit(nick=new_nick, reason="프라이빗 룸 삭제 시 성별 표시 제거")
                    print(f"{self.member.name}님의 닉네임에서 성별 표시 제거: {current_nick} -> {new_nick}")
                    await interaction.response.send_message("프라이빗 룸이 곧 삭제됩니다. 감사합니다! 👋")
                except discord.Forbidden:
                    print("닉네임 변경 권한이 없습니다.")
                    await interaction.response.send_message("프라이빗 룸이 곧 삭제됩니다. 감사합니다! 👋")
                except discord.HTTPException:
                    print("닉네임 변경 중 오류가 발생했습니다.")
                    await interaction.response.send_message("프라이빗 룸이 곧 삭제됩니다. 감사합니다! 👋")
            else:
                # 닉네임에 성별 표시가 없는 경우
                await interaction.response.send_message("프라이빗 룸이 곧 삭제됩니다. 감사합니다! 👋")
            
            # 원본 메시지의 버튼 비활성화
            if self.message:
                try:
                    await self.message.edit(view=self)
                except Exception as e:
                    print(f"메시지 수정 중 오류: {e}")
            
            await asyncio.sleep(3)
            
            # 채널 삭제
            await self.channel.delete(reason=f"{self.member.name}님이 프라이빗 룸 삭제를 요청했습니다.")
            
        except discord.NotFound:
            pass  # 채널이 이미 삭제된 경우
        except Exception as e:
            print(f"채널 삭제 중 오류: {e}")
            import traceback
            traceback.print_exc()

    @discord.ui.button(label='패키지 여행', style=discord.ButtonStyle.success, emoji='👫')
    async def keep_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            self.used = True  # 버튼 사용됨 표시
            
            guild = interaction.guild
            
            # 스튜어디스 역할 찾기
            stewardess_role = discord.utils.get(guild.roles, name="스튜어디스")
            
            # 스카이호스트 역할 찾기
            skyhost_role = discord.utils.get(guild.roles, name="스카이호스트")
            
            # 가이드 역할 찾기 
            guide_role = discord.utils.get(guild.roles, name="가이드")
               
            # 패키지 여행 카테고리 찾기 (없으면 생성)
            package_category = discord.utils.get(guild.categories, name="패키지 여행")
            if not package_category:
                try:
                    package_category = await guild.create_category(
                        "패키지 여행",
                        reason="패키지 여행 시스템용 카테고리 생성"
                    )
                    print(f"패키지 여행 카테고리 생성 완료")
                except discord.Forbidden:
                    await interaction.response.send_message("❌ 카테고리 생성 권한이 없습니다!")
                    return
            
            # 기존 패키지 여행 채널 확인
            existing_package_channel = None
            member_display_name = self.member.display_name
            for channel in package_category.text_channels:
                if channel.name.startswith(f"패키지여행-{member_display_name}"):
                    # 채널 권한에서 해당 멤버가 있는지 확인
                    overwrites = channel.overwrites
                    if self.member in overwrites:
                        existing_package_channel = channel
                        break
            
            if existing_package_channel:
                await interaction.response.send_message(
                    f"✅ 이미 패키지 여행 채널이 존재합니다: {existing_package_channel.mention}\n"
                    f"프라이빗 룸이 곧 삭제됩니다. 패키지 여행 채널을 이용해주세요! 👋"
                )
            else:
                # 패키지 여행 채널 생성 - 본인, 스카이호스트, 가이드, 스튜어디스만 볼 수 있도록
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),  # 모든 사람 차단
                    self.member: discord.PermissionOverwrite(read_messages=True, send_messages=True),  # 본인만 허용
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)  # 봇 자신도 허용
                }
                
                # 각 역할이 있으면 권한 추가
                if stewardess_role:
                    overwrites[stewardess_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                if skyhost_role:
                    overwrites[skyhost_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                if guide_role:
                    overwrites[guide_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
                # 채널명 생성
                package_channel_name = f"패키지여행-{member_display_name}"
                # 특수문자 제거 및 길이 제한
                package_channel_name = "".join(c for c in package_channel_name if c.isalnum() or c in ("-", "_"))[:100]
                
                try:
                    package_channel = await guild.create_text_channel(
                        package_channel_name,
                        category=package_category,
                        overwrites=overwrites,
                        reason=f"{self.member.name}님을 위한 패키지 여행 채널 생성"
                    )
                    print(f"패키지 여행 채널 생성 완료: {package_channel.name}")
                    
                    # 패키지 여행 채널에 환영 메시지 전송 (일반 메시지로 변경)
                    welcome_message = "**🎒 패키지 여행에 오신 것을 환영합니다!**\n\n"
                    welcome_message += f"**{self.member.mention}님을 위한 개인 가이드 입니다.**\n\n"
                    welcome_message += f"이곳은 {self.member.mention}님과 관리자만 볼 수 있는 방입니다.\n\n"
                    welcome_message += f"**🎯 가이드 내용:**\n"
                    welcome_message += f"• 서버 규칙 및 이용 방법 안내\n"
                    welcome_message += f"• 각종 채널 소개 및 활용법\n"
                    welcome_message += f"• 서버 내 활동 가이드\n"
                    welcome_message += f"• 애플 피치 제거하는 법\n"
                    welcome_message += f"• 코인 활용법\n"
                    welcome_message += f"• 기타 궁금한 사항 \n"
                    welcome_message += f"언제든지 편하게 질문해주세요! 😊"
                    
                    await package_channel.send(welcome_message)
                    
                    await interaction.response.send_message(
                        f"✅ 패키지 여행 채널이 생성되었습니다: {package_channel.mention}\n"
                        f"프라이빗 룸이 곧 삭제됩니다. 패키지 여행 채널을 이용해주세요! 😊"
                    )
                    
                except discord.Forbidden:
                    await interaction.response.send_message("❌ 패키지 여행 채널 생성 권한이 없습니다!")
                    return
                except Exception as e:
                    await interaction.response.send_message(f"❌ 패키지 여행 채널 생성 중 오류: {e}")
                    print(f"패키지 여행 채널 생성 중 오류: {e}")
                    return
            
            # 버튼 비활성화
            for item in self.children:
                item.disabled = True
            
            # 원본 메시지의 버튼 비활성화
            if self.message:
                try:
                    await self.message.edit(view=self)
                except Exception as e:
                    print(f"메시지 수정 중 오류: {e}")
            
            # 3초 후 프라이빗 룸 삭제
            await asyncio.sleep(3)
            
            # 프라이빗 룸 삭제
            try:
                await self.channel.delete(reason=f"{self.member.name}님이 가이드 서비스를 선택하여 패키지 여행 채널로 이동")
                print(f"프라이빗 룸 삭제 완료: {self.channel.name}")
            except discord.NotFound:
                pass  # 이미 삭제된 경우
            except Exception as e:
                print(f"프라이빗 룸 삭제 중 오류: {e}")
                    
        except Exception as e:
            print(f"유지 버튼 처리 중 오류: {e}")
            import traceback
            traceback.print_exc()

# 슬래시 커맨드들 (모두 관리자 전용으로 수정)
@bot.tree.command(name="테스트", description="봇이 정상 작동하는지 확인합니다 (관리자 전용)")
@discord.app_commands.default_permissions(administrator=True)
async def test_slash(interaction: discord.Interaction):
    await interaction.response.send_message("✅ 봇이 정상적으로 작동중입니다!", ephemeral=True)

@bot.tree.command(name="참가시뮬레이션", description="새 멤버 참가를 시뮬레이션합니다 (관리자 전용)")  
@discord.app_commands.default_permissions(administrator=True)
async def simulate_join_slash(interaction: discord.Interaction, 멤버: discord.Member = None):
    if not 멤버:
        멤버 = interaction.user
    
    await interaction.response.send_message(f"🔄 {멤버.mention}님의 참가를 시뮬레이션합니다...", ephemeral=True)
    await on_member_join(멤버)

@bot.tree.command(name="사용자정보", description="사용자의 입장 정보를 확인합니다 (관리자 전용)")
@discord.app_commands.default_permissions(administrator=True)
async def user_info_slash(interaction: discord.Interaction, 멤버: discord.Member = None):
    if not 멤버:
        멤버 = interaction.user
    
    guild_id = interaction.guild.id
    user_id = 멤버.id
    key = f"{guild_id}_{user_id}"
    
    if key in user_data:
        data = user_data[key]
        info_message = f"**{멤버.display_name}님의 서버 정보**\n\n"
        info_message += f"**첫 입장**: {data['first_join'][:19].replace('T', ' ')}\n"
        info_message += f"**총 입장 횟수**: {data['join_count']}회\n"
        info_message += f"**마지막 입장**: {data['last_join'][:19].replace('T', ' ')}"
    else:
        info_message = f"**{멤버.display_name}님의 서버 정보**\n\n아직 입장 기록이 없습니다."
    
    await interaction.response.send_message(info_message, ephemeral=True)

@bot.tree.command(name="중복채널정리", description="중복된 프라이빗 룸을 정리합니다 (관리자 전용)")
@discord.app_commands.default_permissions(administrator=True)
async def cleanup_duplicate_channels(interaction: discord.Interaction):
    guild = interaction.guild
    await interaction.response.defer(ephemeral=True)
    
    # 프라이빗 룸 카테고리 찾기
    category = discord.utils.get(guild.categories, name="프라이빗 룸")
    if not category:
        await interaction.followup.send("프라이빗 룸 카테고리를 찾을 수 없습니다.", ephemeral=True)
        return
    
    # 채널별로 그룹화 (새로운 형식 기준)
    channel_groups = {}
    for channel in category.text_channels:
        if channel.name.startswith("프라이빗룸-"):
            # 기본 이름으로 그룹화 (닉네임 부분만)
            parts = channel.name.split("-")
            if len(parts) >= 3:
                base_name = f"{parts[0]}-{parts[2]}"  # 프라이빗룸-닉네임
            else:
                base_name = channel.name
            
            if base_name not in channel_groups:
                channel_groups[base_name] = []
            channel_groups[base_name].append(channel)
    
    deleted_count = 0
    for base_name, channels in channel_groups.items():
        if len(channels) > 1:
            # 가장 오래된 채널을 제외하고 나머지 삭제
            channels.sort(key=lambda x: x.created_at)
            for channel in channels[1:]:
                try:
                    await channel.delete(reason="중복 채널 정리")
                    deleted_count += 1
                    print(f"중복 채널 삭제: {channel.name}")
                except Exception as e:
                    print(f"채널 삭제 실패: {channel.name}, 오류: {e}")
    
    await interaction.followup.send(f"✅ {deleted_count}개의 중복 채널을 정리했습니다.", ephemeral=True)

# 버튼 재활성화 명령어 (관리자 전용으로 수정)
@bot.tree.command(name="버튼재활성화", description="비활성화된 최종 버튼을 재활성화합니다 (관리자 전용)")
@discord.app_commands.default_permissions(administrator=True)
async def reactivate_buttons(interaction: discord.Interaction, 멤버: discord.Member = None):
    channel = interaction.channel
    
    # 채널 이름이 프라이빗 룸인지 확인 (새로운 형식)
    if not channel.name.startswith("프라이빗룸-"):
        await interaction.response.send_message("이 명령어는 프라이빗 룸에서만 사용할 수 있습니다.", ephemeral=True)
        return
    
    # 멤버가 지정되지 않았다면 채널 권한에서 찾기
    if not 멤버:
        # 채널 권한에서 일반 멤버 찾기 (봇, @everyone, 역할 제외)
        for user, overwrite in channel.overwrites.items():
            if isinstance(user, discord.Member) and user != interaction.guild.me:
                멤버 = user
                break
        
        if not 멤버:
            await interaction.response.send_message("해당 채널의 소유자를 찾을 수 없습니다. 멤버를 직접 지정해주세요.", ephemeral=True)
            return
    
    # 마지막 봇 메시지 찾기
    target_message = None
    async for message in channel.history(limit=20):
        if (message.author == bot.user and 
            message.view and
            "목적지에 도착하셨습니다" in message.content):
            target_message = message
            break
    
    if not target_message:
        await interaction.response.send_message("최종 버튼 메시지를 찾을 수 없습니다.", ephemeral=True)
        return
    
    # 새로운 버튼 뷰 생성 및 메시지 수정
    new_view = FinalButtonView(멤버, channel)
    new_view.message = target_message
    
    try:
        await target_message.edit(view=new_view)
        await interaction.response.send_message(f"✅ {멤버.mention}님을 위한 버튼이 재활성화되었습니다!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ 버튼 재활성화 중 오류가 발생했습니다: {e}", ephemeral=True)
        print(f"버튼 재활성화 오류: {e}")

# 패키지 여행 채널 정리 명령어 추가 (관리자 전용)
@bot.tree.command(name="패키지여행정리", description="패키지 여행 채널을 정리합니다 (관리자 전용)")
@discord.app_commands.default_permissions(administrator=True)
async def cleanup_package_channels(interaction: discord.Interaction):
    guild = interaction.guild
    await interaction.response.defer(ephemeral=True)
    
    # 패키지 여행 카테고리 찾기
    category = discord.utils.get(guild.categories, name="패키지 여행")
    if not category:
        await interaction.followup.send("패키지 여행 카테고리를 찾을 수 없습니다.", ephemeral=True)
        return
    
    # 중복 채널 그룹화
    channel_groups = {}
    for channel in category.text_channels:
        if channel.name.startswith("패키지여행"):
            parts = channel.name.split("-")
            if len(parts) >= 2:
                base_name = f"{parts[0]}-{parts[1]}"  # 패키지여행-닉네임
            else:
                base_name = channel.name
            
            if base_name not in channel_groups:
                channel_groups[base_name] = []
            channel_groups[base_name].append(channel)
    
    deleted_count = 0
    for base_name, channels in channel_groups.items():
        if len(channels) > 1:
            # 가장 오래된 채널을 제외하고 나머지 삭제
            channels.sort(key=lambda x: x.created_at)
            for channel in channels[1:]:
                try:
                    await channel.delete(reason="중복 패키지 여행 채널 정리")
                    deleted_count += 1
                    print(f"중복 패키지 여행 채널 삭제: {channel.name}")
                except Exception as e:
                    print(f"패키지 여행 채널 삭제 실패: {channel.name}, 오류: {e}")
    
    await interaction.followup.send(f"✅ {deleted_count}개의 중복 패키지 여행 채널을 정리했습니다.", ephemeral=True)

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
