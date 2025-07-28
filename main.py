import discord
from discord.ext import commands, tasks
import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

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

# 멤버가 서버에 참가했을 때
@bot.event
async def on_member_join(member):
    guild = member.guild
    
    # 스튜어디스 역할 찾기 (없으면 생성)
    stewardess_role = discord.utils.get(guild.roles, name="스튜어디스")
    if not stewardess_role:
        stewardess_role = await guild.create_role(name="스튜어디스", color=discord.Color.blue())
    
    # 프라이빗 룸 카테고리 찾기 (없으면 생성)
    category = discord.utils.get(guild.categories, name="프라이빗 룸")
    if not category:
        category = await guild.create_category("프라이빗 룸")
    
    # 권한 설정
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        stewardess_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    # 채널 생성
    channel_name = f"괄자-애정듬뿍-{member.name}"
    private_channel = await guild.create_text_channel(
        channel_name,
        category=category,
        overwrites=overwrites
    )
    
    # 첫 번째 안내문
    embed1 = discord.Embed(
        title="# 프라이빗룸",
        description=f"**{member.mention} 고객님의 좌석 등급이 퍼스트로 올라 프라이빗 룸이 생성됐어요**\n"
                   f"**이 대화방은 저희 {stewardess_role.mention} 와 당신만 보이는 프라이빗 룸입니다.**\n"
                   f"-# 관리자랑 {member.mention}고객님만 보여요!\n\n"
                   f"단 {stewardess_role.mention}의 부름에 대답이 없으실 경우 좌석등급이 하향될수있습니다\n\n"
                   f"-# 좌석 등급 하향은 서버 추방입니다",
        color=discord.Color.gold()
    )
    
    await private_channel.send(embed=embed1)
    
    # 10초 후 두 번째 안내문과 버튼
    await asyncio.sleep(10)
    
    embed2 = discord.Embed(
        title="# 즐거운 식사시간~!",
        description="**## 서버는 입맞에 맞으신가요?**\n"
                   "서버가 입맛에 맞으시다면 한식 버튼을\n"
                   "서버가 입맛에 맞지 않으시다면 승무원 버튼을 눌러주세요\n"
                   "-# 승무원 버튼을 누르시면 고객님을 위한 특별 기내식을 준비해드리겠습니다!",
        color=discord.Color.green()
    )
    
    view = MealButtonView(member, stewardess_role, private_channel)
    await private_channel.send(embed=embed2, view=view)

class MealButtonView(discord.ui.View):
    def __init__(self, member, stewardess_role, channel):
        super().__init__(timeout=None)
        self.member = member
        self.stewardess_role = stewardess_role
        self.channel = channel

    @discord.ui.button(label='한식', style=discord.ButtonStyle.primary)
    async def korean_food(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.member:
            await interaction.response.send_message("이 버튼은 당신을 위한 것이 아닙니다.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="# 당신은 공항에 입장하실 수 있습니다",
            description="**## 서버원들과좀더 친해지고싶으시다면 버튼을 눌러주세요**\n"
                       "-# 공항이 보이는건 자율적입니다. 울타리 친목이 존재하는 곳이니 이점 숙지 바랍니다."
                       "추후에 공항 채널을 안보이게 하고싶으시다면 #요청사항 의 티켓을 열어 @정규직 을 태그해 알려주시기 바랍니다",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
        
        # 15초 후 최종 버튼 보내기
        await asyncio.sleep(15)
        final_view = FinalButtonView(self.member, self.channel)
        final_embed = discord.Embed(
            title="# 목적지에 도착하셨습니다!",
            description="서버에 적응을 하셨다면 삭제버튼을\n"
                       "-# 서버적응에 가이드가 필요하시다면 유지버튼을 눌러주세요! 가이드는 무료입니다!",
            color=discord.Color.purple()
        )
        await self.channel.send(embed=final_embed, view=final_view)

    @discord.ui.button(label='승무원', style=discord.ButtonStyle.secondary)
    async def stewardess(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.member:
            await interaction.response.send_message("이 버튼은 당신을 위한 것이 아닙니다.", ephemeral=True)
            return
        
        embed = discord.Embed(
            description=f"**저희 {self.stewardess_role.mention} 가 고객님의 입맛에 맞는 특별 기내식을 준비중입니다! 기대해주세요**\n🍳",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
        
        # 15초 후 최종 버튼 보내기
        await asyncio.sleep(15)
        final_view = FinalButtonView(self.member, self.channel)
        final_embed = discord.Embed(
            title="# 목적지에 도착하셨습니다!",
            description="서버에 적응을 하셨다면 삭제버튼을\n"
                       "-# 서버적응에 가이드가 필요하시다면 유지버튼을 눌러주세요! 가이드는 무료입니다!",
            color=discord.Color.purple()
        )
        await self.channel.send(embed=final_embed, view=final_view)

class FinalButtonView(discord.ui.View):
    def __init__(self, member, channel):
        super().__init__(timeout=None)
        self.member = member
        self.channel = channel

    @discord.ui.button(label='삭제', style=discord.ButtonStyle.danger)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.member:
            await interaction.response.send_message("이 버튼은 당신을 위한 것이 아닙니다.", ephemeral=True)
            return
        
        await interaction.response.send_message("프라이빗 룸이 곧 삭제됩니다. 감사합니다!")
        await asyncio.sleep(3)
        await self.channel.delete()

    @discord.ui.button(label='유지', style=discord.ButtonStyle.success)
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

# 봇 실행
if __name__ == "__main__":
    # 환경변수에서 토큰 가져오기 (보안을 위해)
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("DISCORD_BOT_TOKEN 환경변수를 설정해주세요!")
    else:
        bot.run(TOKEN)
