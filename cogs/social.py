import random
import time

import discord
from discord.ext import commands

from cogs.fun import fetch_gif
from ui import OwnerView
from usage import send_usage
from utils import fmt_duration, reply

DATE_COOLDOWN = 6 * 3600

DATES = [
    "🍽️ Гоё ресторанд хамт оройн хоол идлээ",
    "🎬 Кино театрт хамт кино үзлээ",
    "🌄 Хамт уул өгсөж нар жаргахыг харлаа",
    "🎡 Зугаа цэнгэлийн парк орж хамт эргэлдлээ",
    "☕ Кофе шопд хэдэн цаг ярилцлаа",
    "🌃 Шөнийн хотоор хамтдаа алхлаа",
    "🏞️ Тэрэлжинд хамт зугаалж, гал түймэр тавилаа",
    "🎤 Караокенд хос дуу дуулав",
]

# +18 сэдэвтэй (шууд бус, зөөлөн) эможи — зөвхөн NSFW сувагт ажиллана. (нэр, текст, өөртөө, emoji, gif төрөл)
ADULT_EMOTES = [
    ("flirt", "{a} {b}-тэй сэтгэл татам сээтэгнэв", "{a} толинд өөртөө сээтэгнэв", "😘", "wink"),
    ("tease", "{a} {b}-г зэхүүн байдлаар шоолж хөгжөөв", "{a} өөрийгөө шоолов", "😈", "smug"),
    ("seduce", "{a} {b}-г сэтгэл татам харцаар ширтэв", "{a} толинд өөрийгөө биширэв", "🔥", "stare"),
    ("lovebite", "{a} {b}-ийг зөөлөн зуув", "{a} уруулаа зуув", "💋", "bite"),
    ("sparkle", "{a} {b}-тэй хайрын шөнө өнгөрөөв", "{a} ганцаараа сарыг харав", "🌙", "cuddle"),
]


class ProposalView(OwnerView):
    """Зөвхөн саналыг хүлээн авагч дарна."""

    def __init__(self, cog, proposer: discord.Member, target: discord.Member):
        super().__init__(target.id, timeout=120)
        self.cog, self.proposer, self.target = cog, proposer, target

    async def finish(self, interaction, text, color):
        self.disable_all()
        self.stop()
        embed = discord.Embed(description=text, color=color)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Зөвшөөрөх", emoji="💍", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.cog.bot.db
        if not await db.remove_item(self.proposer.id, "ring", 1):
            await self.finish(interaction, "❌ Саналын бөгж олдсонгүй. Гэрлэлт болсонгүй.", 0xEF4444)
            return
        if not await db.marry(self.proposer.id, self.target.id, time.time()):
            await db.add_item(self.proposer.id, "ring", 1)
            await self.finish(interaction, "❌ Хэн нэг нь аль хэдийн гэрлэсэн байна.", 0xEF4444)
            return
        await self.finish(
            interaction,
            f"💒 **Баяр хүргэе!** {self.proposer.mention} 💞 {self.target.mention} гэрлэлээ!\n"
            f"Одоо `qdate`-ээр болзож, хайрын оноо цуглуулаарай.",
            0xEC4899,
        )

    @discord.ui.button(label="Татгалзах", emoji="💔", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish(interaction, f"💔 {self.target.mention} саналаас татгалзлаа.", 0x6B7280)


class Social(commands.Cog):
    """Гэрлэлт, болзоо, +18 сэдэвтэй эможи."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        for name, other, selfmsg, emoji, kind in ADULT_EMOTES:
            bot.add_command(self._make_adult(name, other, selfmsg, emoji, kind))

    def cog_unload(self):
        for name, *_ in ADULT_EMOTES:
            self.bot.remove_command(name)

    def _make_adult(self, name, other, selfmsg, emoji, kind):
        @commands.command(name=name, help=f"🔞 {emoji} {name} (NSFW суваг)")
        async def adult(ctx: commands.Context, member: discord.Member = None):
            if ctx.guild is None:
                return
            if not getattr(ctx.channel, "is_nsfw", lambda: False)():
                await reply(ctx, f"🔞 `{ctx.clean_prefix}{name}` зөвхөн **NSFW (18+) сувагт** ажиллана.")
                return
            if member is None:
                await send_usage(ctx)
                return
            a, b = ctx.author.mention, member.mention
            text = (selfmsg if member.id == ctx.author.id else other).format(a=a, b=b)
            embed = discord.Embed(description=f"{emoji} **{text}**", color=0xBE123C)
            gif = await fetch_gif(kind)
            if gif:
                embed.set_image(url=gif)
            embed.set_footer(text="🔞 18+ сэдэвтэй эможи")
            await ctx.send(embed=embed)

        return adult

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.command(name="marry", aliases=["propose", "gerleh"])
    async def marry(self, ctx: commands.Context, member: discord.Member):
        """Гэрлэх санал тавих (бөгж хэрэгтэй): marry <@хүн>"""
        db = self.bot.db
        if member.bot or member.id == ctx.author.id:
            await reply(ctx, "❌ Өөр хүнийг сонгоно уу.")
            return
        mine = await db.get_profile(ctx.author.id)
        theirs = await db.get_profile(member.id)
        if theirs is None:
            await reply(ctx, f"❌ {member.display_name} character үүсгээгүй байна.")
            return
        if mine["spouse_id"]:
            await reply(ctx, "❌ Та аль хэдийн гэрлэсэн. `divorce`-оор салж болно.")
            return
        if theirs["spouse_id"]:
            await reply(ctx, f"❌ {member.display_name} аль хэдийн гэрлэсэн байна.")
            return
        if await db.item_qty(ctx.author.id, "ring") <= 0:
            await reply(ctx, f"💍 Гэрлэх санал тавихад **Бөгж** хэрэгтэй. `{ctx.clean_prefix}shop clothes` → `ring`")
            return
        embed = discord.Embed(
            title="💍 Гэрлэх санал",
            description=f"{ctx.author.mention} → {member.mention}\n**Надтай гэрлэх үү?** 💖",
            color=0xEC4899,
        )
        view = ProposalView(self, ctx.author, member)
        view.message = await ctx.send(content=member.mention, embed=embed, view=view)

    @commands.command(name="divorce", aliases=["salah"])
    async def divorce(self, ctx: commands.Context):
        """Гэрлэлтээ цуцлах"""
        spouse = await self.bot.db.divorce(ctx.author.id)
        if spouse is None:
            await reply(ctx, "❌ Та гэрлээгүй байна.")
            return
        await reply(ctx, f"💔 Та <@{spouse}>-тай гэрлэлтээ цуцлууллаа.")

    @commands.command(name="date", aliases=["bolzoo"])
    async def date(self, ctx: commands.Context):
        """Хосоороо болзох (6 цаг тутам), хайрын оноо нэмнэ"""
        db = self.bot.db
        prof = await db.get_profile(ctx.author.id)
        spouse = prof["spouse_id"]
        if not spouse:
            await reply(ctx, f"💞 Та гэрлээгүй байна. `{ctx.clean_prefix}marry @хүн` гэж санал тавина уу.")
            return
        love = random.randint(1, 3)
        ok = await db.do_date(ctx.author.id, spouse, time.time(), DATE_COOLDOWN, love)
        if not ok:
            left = max(prof["last_date"] + DATE_COOLDOWN - time.time(), 0)
            await reply(ctx, f"⏳ Та нар саяхан болзсон. **{fmt_duration(left)}**-ийн дараа дахин болзоорой.")
            return
        embed = discord.Embed(
            title="💞 Болзоо",
            description=f"{ctx.author.mention} 💕 <@{spouse}>\n{random.choice(DATES)}\n\n💖 Хайрын оноо **+{love}**",
            color=0xEC4899,
        )
        await reply(ctx, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Social(bot))
