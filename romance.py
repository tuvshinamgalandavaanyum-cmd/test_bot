import random
import time

import discord
from discord.ext import commands

from ui import nav_button
from utils import MIN_BET, fmt, fmt_duration, jailed, reply

DATE_COST = 30_000
DATE_COOLDOWN = 6 * 3600
DIVORCE_FEE = 100_000

DATE_EVENTS = [
    ("🍽️", "Хоёулаа шөнийн ресторанд хоол идлээ"),
    ("🎬", "Кино үзэж, попкорн хуваалцлаа"),
    ("🌃", "Хотын гэрэлт орчинд алхлаа"),
    ("🎡", "Тоглоомын цэнгэлдэхэд дугуйгаар эргэлдлээ"),
    ("🌅", "Нар жаргахыг хамт харлаа"),
    ("☕", "Кофе уун чимээгүй ярилцлаа"),
    ("🎤", "Караокед хамтдаа дуулж, хөгжилдлөө"),
]


def love_level(love: int) -> str:
    if love >= 100:
        return "💖 Мөнхийн хайр"
    if love >= 50:
        return "❤️ Гүн хайр"
    if love >= 20:
        return "💕 Хайр дурлал"
    if love >= 5:
        return "💗 Дотно"
    return "🌱 Шинэхэн"


class ProposalView(discord.ui.View):
    def __init__(self, cog, proposer, target):
        super().__init__(timeout=90)
        self.cog, self.proposer, self.target = cog, proposer, target
        self.resolved = False
        self.message = None
        self.add_item(nav_button("💍 Зөвшөөрөх", self.on_yes, discord.ButtonStyle.success))
        self.add_item(nav_button("💔 Татгалзах", self.on_no, discord.ButtonStyle.danger))

    async def interaction_check(self, interaction) -> bool:
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Энэ санал танд хамаагүй.", ephemeral=True)
            return False
        return True

    async def on_yes(self, interaction):
        if self.resolved:
            await interaction.response.defer()
            return
        self.resolved = True
        self.stop()
        for c in self.children:
            c.disabled = True
        db = self.cog.bot.db
        if not await db.remove_item(self.proposer.id, "ring", 1):
            embed = discord.Embed(title="❌ Бөгж алга", description="Гэр бүл болох бөгж алга болжээ.", color=0xEF4444)
        elif not await db.marry(self.proposer.id, self.target.id):
            await db.add_item(self.proposer.id, "ring", 1)
            embed = discord.Embed(title="❌ Боломжгүй боллоо", description="Хэн нэг нь аль хэдийн гэрлэсэн байна.", color=0xEF4444)
        else:
            embed = discord.Embed(
                title="💒 Баяр хүргэе!",
                description=f"{self.proposer.mention} 💞 {self.target.mention}\nТанд болон гэр бүлд тань аз жаргал хүсье!",
                color=0xEC4899,
            )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_no(self, interaction):
        if self.resolved:
            await interaction.response.defer()
            return
        self.resolved = True
        self.stop()
        for c in self.children:
            c.disabled = True
        embed = discord.Embed(
            title="💔 Татгалзлаа",
            description=f"{self.target.mention} саналыг татгалзлаа. Дараагийн удаа аз таарна даа.",
            color=0x6B7280,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.resolved:
            return
        for c in self.children:
            c.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(embed=discord.Embed(title="⌛ Хариу ирсэнгүй", color=0x6B7280), view=self)
            except Exception:
                pass


class Romance(commands.Cog):
    """Гэр бүл, романс."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.command(name="marry", aliases=["propose"])
    async def marry(self, ctx: commands.Context, member: discord.Member):
        """Гэр бүл болох санал тавих: marry @хүн (бөгж хэрэгтэй)"""
        p = ctx.clean_prefix
        if member.id == ctx.author.id or member.bot:
            await reply(ctx, "❌ Энэ хүнд санал тавих боломжгүй.")
            return
        me = await self.bot.db.get_user(ctx.author.id)
        other = await self.bot.db.get_user(member.id)
        if await jailed(ctx, me):
            return
        if me["spouse"]:
            await reply(ctx, f"💍 Та аль хэдийн гэрлэсэн байна (<@{me['spouse']}>).")
            return
        if other["spouse"] or not other["registered"]:
            await reply(ctx, "❌ Тэр хүн гэрлэсэн эсвэл бүртгүүлээгүй байна.")
            return
        if await self.bot.db.item_qty(ctx.author.id, "ring") <= 0:
            await reply(ctx, f"💍 Танд бөгж алга. `{p}buy ring` ({fmt(150_000)}) гэж авна уу.")
            return
        embed = discord.Embed(
            title="💍 Гэрлэх санал!",
            description=f"{member.mention}, {ctx.author.mention} таньд гэр бүл болохыг санал болгож байна. 💞",
            color=0xEC4899,
        )
        view = ProposalView(self, ctx.author, member)
        view.message = await reply(ctx, embed=embed, view=view)

    @commands.command(name="divorce")
    async def divorce(self, ctx: commands.Context):
        """Салах (хураамж 100,000₮)"""
        me = await self.bot.db.get_user(ctx.author.id)
        if not me["spouse"]:
            await reply(ctx, "💔 Та гэрлээгүй байна.")
            return
        if not await self.bot.db.spend(ctx.author.id, DIVORCE_FEE):
            await reply(ctx, f"❌ Салах хураамж {fmt(DIVORCE_FEE)} хэрэгтэй (хэтэвчинд).")
            return
        other = await self.bot.db.divorce(ctx.author.id)
        await reply(ctx, f"💔 {ctx.author.mention} ба <@{other}> салалаа. Хураамж: {fmt(DIVORCE_FEE)}.")

    @commands.command(name="couple", aliases=["spouse", "love"])
    async def couple(self, ctx: commands.Context):
        """Гэр бүлийн мэдээлэл"""
        me = await self.bot.db.get_user(ctx.author.id)
        if not me["spouse"]:
            await reply(ctx, f"💔 Та ганц бие байна. `{ctx.clean_prefix}marry @хүн`")
            return
        embed = discord.Embed(title="💞 Манай гэр бүл", color=0xEC4899)
        embed.add_field(name="Хань", value=f"<@{me['spouse']}>", inline=True)
        embed.add_field(name="Хайр", value=f"{me['love']} · {love_level(me['love'])}", inline=True)
        embed.add_field(
            name="Ажлын нэмэгдэл",
            value=f"+{min(me['love'] // 10, 5)}% (хайр 10 тутамд +1%, дээд 5%)",
            inline=False,
        )
        embed.set_footer(text=f"{ctx.clean_prefix}date — болзоо ({fmt(DATE_COST)})")
        await reply(ctx, embed=embed)

    @commands.command(name="date", aliases=["bolzoo"])
    async def date(self, ctx: commands.Context):
        """Ханьтайгаа болзох (30,000₮, 6 цаг тутам)"""
        me = await self.bot.db.get_user(ctx.author.id)
        if await jailed(ctx, me):
            return
        if not me["spouse"]:
            await reply(ctx, f"💔 Эхлээд гэрлэх хэрэгтэй. `{ctx.clean_prefix}marry @хүн`")
            return
        now = time.time()
        if not await self.bot.db.spend(ctx.author.id, DATE_COST):
            await reply(ctx, f"❌ Болзоонд {fmt(DATE_COST)} хэрэгтэй.")
            return
        if not await self.bot.db.start_cooldown(ctx.author.id, "last_date", now, DATE_COOLDOWN):
            await self.bot.db.add_balance(ctx.author.id, DATE_COST)
            left = me["last_date"] + DATE_COOLDOWN - now
            await reply(ctx, f"⏳ Дараагийн болзоо **{fmt_duration(left)}**-ийн дараа.")
            return
        gain = random.randint(2, 5)
        await self.bot.db.add_love(ctx.author.id, me["spouse"], gain)
        emoji, text = random.choice(DATE_EVENTS)
        embed = discord.Embed(
            title=f"{emoji} Болзоо",
            description=f"{ctx.author.mention} 💞 <@{me['spouse']}>\n{text}",
            color=0xEC4899,
        )
        embed.add_field(name="💞 Хайр", value=f"+{gain}", inline=True)
        embed.add_field(name="💸 Зардал", value=fmt(DATE_COST), inline=True)
        await reply(ctx, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Romance(bot))
