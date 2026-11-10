import math
import random
import time

import discord
from discord.ext import commands

from houses import get_house
from items import get_pet
from ui import OwnerView, nav_button
from usage import send_usage
from utils import (
    BANK_FEE,
    MAX_STRENGTH,
    apply_tax,
    boost_mult,
    fmt,
    fmt_duration,
    fmt_short,
    hunger_left,
    parse_amount,
    reply,
)

DAILY_COOLDOWN = 24 * 3600
DAILY_MIN = 40_000
DAILY_MAX = 80_000
DAILY_STEP = 3_000  # дараалан авсан өдөр бүрт нэмэгдэх шагнал
DAILY_MAX_STEPS = 10

METRICS = {
    "bank": ("🏛️ Банк Топ", "🏛️ Банк"),
    "wallet": ("💵 Хэтэвч Топ", "💵 Хэтэвч"),
    "total": ("💎 Нийт Хөрөнгө Топ", "💎 Нийт"),
}
PER_PAGE = 10


def tx_embed(title: str, route: str, got: int, fee: int, balance_label: str, balance: int, who: str):
    """Гүйлгээний карт."""
    embed = discord.Embed(title=f"✅ {title}", color=0x22C55E)
    embed.description = f"```diff\n- {route}\n```"
    embed.add_field(name="💵 Авсан дүн", value=f"`{got:,} ₮`", inline=True)
    embed.add_field(name="💳 Шимтгэл", value=f"`{fee:,} ₮`", inline=True)
    embed.add_field(name=f"🏛️ {balance_label}", value=f"`{balance:,} ₮`", inline=False)
    embed.set_footer(text=who)
    return embed


class LeaderboardView(OwnerView):
    def __init__(self, cog, ctx, metric: str = "bank", page: int = 0):
        super().__init__(ctx.author.id, timeout=120)
        self.cog, self.ctx, self.metric, self.page = cog, ctx, metric, page
        self.pages = 1
        self.prev_btn = nav_button("◀", self.on_prev)
        self.next_btn = nav_button("▶", self.on_next)
        self.bank_btn = nav_button("🏛️ Банк", self.on_bank, discord.ButtonStyle.primary)
        self.wallet_btn = nav_button("💵 Хэтэвч", self.on_wallet)
        self.total_btn = nav_button("💎 Нийт", self.on_total)
        for b in (self.prev_btn, self.next_btn, self.bank_btn, self.wallet_btn, self.total_btn):
            self.add_item(b)

    async def build(self) -> discord.Embed:
        db = self.cog.bot.db
        total = await db.count_users()
        self.pages = max(1, math.ceil(total / PER_PAGE))
        self.page = max(0, min(self.page, self.pages - 1))
        rows = await db.top(self.metric, PER_PAGE, self.page * PER_PAGE)
        lines = [
            f"**{self.page * PER_PAGE + i + 1}.** <@{r['user_id']}> — `{r['value']:,}₮`"
            for i, r in enumerate(rows)
        ]
        guild = self.ctx.guild.name if self.ctx.guild else "Сервер"
        embed = discord.Embed(
            title=f"📊 {guild} - {METRICS[self.metric][0]}",
            description="\n".join(lines) or "Одоогоор тоглогч алга.",
            color=0xFFC933,
        )
        embed.set_footer(text=f"Хуудас {self.page + 1}/{self.pages}")
        self.prev_btn.disabled = self.page <= 0
        self.next_btn.disabled = self.page >= self.pages - 1
        for key, btn in (("bank", self.bank_btn), ("wallet", self.wallet_btn), ("total", self.total_btn)):
            btn.style = discord.ButtonStyle.primary if key == self.metric else discord.ButtonStyle.secondary
        return embed

    async def refresh(self, interaction):
        embed = await self.build()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_prev(self, interaction):
        self.page -= 1
        await self.refresh(interaction)

    async def on_next(self, interaction):
        self.page += 1
        await self.refresh(interaction)

    async def on_bank(self, interaction):
        self.metric, self.page = "bank", 0
        await self.refresh(interaction)

    async def on_wallet(self, interaction):
        self.metric, self.page = "wallet", 0
        await self.refresh(interaction)

    async def on_total(self, interaction):
        self.metric, self.page = "total", 0
        await self.refresh(interaction)


class Economy(commands.Cog):
    """Данс, банк, шилжүүлэг, өдрийн шагнал, тэргүүлэгчид."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.command(name="bal", aliases=["balance", "b"])
    async def balance(self, ctx: commands.Context, member: discord.Member = None):
        """Санхүүгийн тайлан: bal [@хэрэглэгч]"""
        target = member or ctx.author
        user = await self.bot.db.get_user(target.id)
        now = time.time()
        left = hunger_left(user["last_fed"], now)

        embed = discord.Embed(title="🏦 Таны санхүүгийн тайлан", color=0x2BFF7A)
        embed.description = (
            "```\n═══════════════════════\n💰 САНХҮҮГИЙН МЭДЭЭЛЭЛ\n═══════════════════════\n```"
        )
        embed.add_field(name="💵 Хэтэвч", value=f"`{user['balance']:,}₮`", inline=True)
        embed.add_field(name="🏛️ Банкны данс", value=f"`{user['bank']:,}₮`", inline=True)
        embed.add_field(name="🔐 Сейф", value=f"`{user['safe_money']:,}₮`", inline=True)
        total = user["balance"] + user["bank"] + user["safe_money"]
        embed.add_field(name="💎 Нийт хөрөнгө", value=f"`{total:,}₮`", inline=False)

        if user["dead"]:
            hunger = "💀 Үхсэн (Revive Active хэрэгтэй)"
        elif left <= 0:
            hunger = f"⚠️ Өлсөж байна! `{ctx.clean_prefix}shop food` → `{ctx.clean_prefix}eat`"
        else:
            hunger = f"🍞 {fmt_duration(left)}-ийн дараа өлсөнө"
        embed.add_field(name="Хоол", value=hunger, inline=True)
        embed.add_field(name="💪 Хүч", value=f"{user['strength']}/{MAX_STRENGTH}", inline=True)
        pet = get_pet(user["pet"])
        embed.add_field(name="🐾 Амьтан", value=f"{pet.emoji} {pet.name}" if pet else "Байхгүй", inline=True)
        house = get_house(user["house"])
        embed.add_field(name="🏠 Байшин", value=f"{house.emoji} {house.name}" if house else "Байхгүй", inline=True)
        if user["protect_until"] > now:
            embed.add_field(
                name="🛡️ Хамгаалалт", value=f"{fmt_short(user['protect_until'] - now)} үлдсэн", inline=True
            )
        if user["jail_until"] > now:
            embed.add_field(
                name="⛓️ Шорон", value=f"{fmt_short(user['jail_until'] - now)} үлдсэн", inline=True
            )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"{target.display_name}-ийн санхүү")
        await reply(ctx, embed=embed)

    @commands.command(name="bank")
    async def bank(self, ctx: commands.Context):
        """Банкны дансны мэдээлэл"""
        user = await self.bot.db.get_user(ctx.author.id)
        p = ctx.clean_prefix
        embed = discord.Embed(title="🏦 Банкны үйлчилгээ", color=0x3B82F6)
        embed.add_field(name="🏛️ Банкны данс", value=f"`{user['bank']:,}₮`", inline=True)
        embed.add_field(name="💵 Хэтэвч", value=f"`{user['balance']:,}₮`", inline=True)
        embed.add_field(name="💳 Шимтгэл", value=f"`{BANK_FEE:,}₮` / гүйлгээ", inline=True)
        embed.add_field(
            name="ℹ️ Мэдэх зүйл",
            value=(
                "• Казино зөвхөн банкны данснаас тоглоно.\n"
                "• Банкны мөнгийг хакердаж болно, `qblock` бамбай хамгаална.\n"
                "• Хэтэвчний мөнгийг дээрэмдэж болно."
            ).replace("qblock", f"{p}block"),
            inline=False,
        )
        embed.set_footer(text=f"Хийх: {p}dep <дүн> | Авах: {p}with <дүн> | all гэвэл бүгдийг")
        await reply(ctx, embed=embed)

    @commands.command(name="dep", aliases=["deposit"])
    async def deposit(self, ctx: commands.Context, amount: str = "all"):
        """Хэтэвчнээс банкинд хийх: dep [дүн | all]"""
        user = await self.bot.db.get_user(ctx.author.id)
        amt = parse_amount(amount, user["balance"] - BANK_FEE)
        if amt is None:
            await send_usage(ctx)
            return
        if amt <= 0 or user["balance"] < amt + BANK_FEE:
            await reply(ctx, f"❌ Хэтэвчинд мөнгө хүрэлцэхгүй байна (шимтгэл {fmt(BANK_FEE)} хамт).")
            return
        if not await self.bot.db.deposit(ctx.author.id, amt, BANK_FEE):
            await reply(ctx, "❌ Хэтэвчинд мөнгө хүрэлцэхгүй байна.")
            return
        after = await self.bot.db.get_user(ctx.author.id)
        await reply(
            ctx,
            embed=tx_embed(
                "Гүйлгээ амжилттай", "Хэтэвч → Банкны данс", amt, BANK_FEE,
                "Дансны үлдэгдэл", after["bank"], ctx.author.display_name,
            ),
        )

    @commands.command(name="with", aliases=["withdraw", "wd"])
    async def withdraw(self, ctx: commands.Context, amount: str = "all"):
        """Банкнаас хэтэвчид авах: with [дүн | all]"""
        user = await self.bot.db.get_user(ctx.author.id)
        amt = parse_amount(amount, user["bank"] - BANK_FEE)
        if amt is None:
            await send_usage(ctx)
            return
        if amt <= 0 or user["bank"] < amt + BANK_FEE:
            await reply(ctx, f"❌ Банкны дансанд мөнгө хүрэлцэхгүй байна (шимтгэл {fmt(BANK_FEE)} хамт).")
            return
        if not await self.bot.db.withdraw(ctx.author.id, amt, BANK_FEE):
            await reply(ctx, "❌ Банкны дансанд мөнгө хүрэлцэхгүй байна.")
            return
        after = await self.bot.db.get_user(ctx.author.id)
        await reply(
            ctx,
            embed=tx_embed(
                "Гүйлгээ амжилттай", "Банкны данс → Хэтэвч", amt, BANK_FEE,
                "Дансны үлдэгдэл", after["bank"], ctx.author.display_name,
            ),
        )

    @commands.command(name="give", aliases=["pay", "transfer"])
    async def give(self, ctx: commands.Context, member: discord.Member, amount: str):
        """Бусдад мөнгө шилжүүлэх: give @хүн <дүн>"""
        if member.id == ctx.author.id:
            await reply(ctx, "❌ Өөртөө мөнгө шилжүүлэх боломжгүй.")
            return
        if member.bot:
            await reply(ctx, "❌ Ботод мөнгө шилжүүлэх боломжгүй.")
            return
        user = await self.bot.db.get_user(ctx.author.id)
        amt = parse_amount(amount, user["balance"] - BANK_FEE)
        if amt is None:
            await send_usage(ctx)
            return
        if amt <= 0 or not await self.bot.db.transfer(ctx.author.id, member.id, amt, BANK_FEE):
            await reply(ctx, f"❌ Таны хэтэвчинд мөнгө хүрэлцэхгүй байна (шимтгэл {fmt(BANK_FEE)} хамт).")
            return
        after = await self.bot.db.get_user(ctx.author.id)
        embed = tx_embed(
            "Шилжүүлэг амжилттай", f"Хэтэвч → {member.display_name}", amt, BANK_FEE,
            "Таны хэтэвч", after["balance"], ctx.author.display_name,
        )
        await reply(ctx, embed=embed)

    @commands.command(name="daily")
    async def daily(self, ctx: commands.Context):
        """24 цаг тутамд өдрийн цалингаа авах"""
        user = await self.bot.db.get_user(ctx.author.id)
        now = time.time()
        since = now - user["last_daily"]
        if user["last_daily"] > 0 and since < DAILY_COOLDOWN:
            await reply(
                ctx,
                f"⏳ Өнөөдрийн цалингаа авсан байна. **{fmt_duration(DAILY_COOLDOWN - since)}**-ийн дараа дахин авна.",
            )
            return

        # 48 цагийн дотор дахин авбал дараалал үргэлжилнэ
        if user["last_daily"] > 0 and since < 2 * DAILY_COOLDOWN:
            streak = user["daily_streak"] + 1
        else:
            streak = 1
        gross = random.randint(DAILY_MIN, DAILY_MAX) + min(streak - 1, DAILY_MAX_STEPS) * DAILY_STEP
        gross = int(gross * boost_mult(user))
        net, tax = apply_tax(gross)
        reward = net

        ok = await self.bot.db.claim_daily(ctx.author.id, now, net, streak, user["last_daily"])
        if not ok:
            await reply(ctx, "⏳ Дахин оролдоно уу.")
            return
        embed = discord.Embed(
            title="🎁 Өдрийн цалин буулаа!",
            description="Та өнөөдрийн ажлын хөлсөө авлаа. Баяр хүргэе!",
            color=0x22C55E,
        )
        await self.bot.db.add_setting("pool", tax)
        embed.add_field(name="💵 Орлого", value=f"```diff\n+{reward:,} ₮\n```", inline=False)
        embed.add_field(name="🧾 Татвар (10%)", value=f"-{tax:,} ₮", inline=True)
        embed.add_field(name="🔥 Дараалсан өдөр", value=str(streak), inline=True)
        embed.add_field(
            name="ℹ️", value="Амжилттай ажилласан тул хэтэвчинд тань орлого нэмэгдлээ.", inline=False
        )
        embed.set_footer(text=f"{ctx.author.display_name} · дараагийнх нь 24 цагийн дараа")
        await reply(ctx, embed=embed)

    @commands.command(name="lb", aliases=["top", "leaderboard"])
    async def leaderboard(self, ctx: commands.Context, metric: str = "bank"):
        """Хамгийн баян хэрэглэгчид: lb [bank | wallet | total]"""
        metric = metric.lower()
        if metric not in METRICS:
            metric = "bank"
        view = LeaderboardView(self, ctx, metric)
        embed = await view.build()
        view.message = await reply(ctx, embed=embed, view=view)

    @commands.command(name="setmoney", aliases=["setbal"])
    @commands.is_owner()
    async def setmoney(self, ctx: commands.Context, member: discord.Member, amount: str):
        """Bot Owner: хэрэглэгчийн хэтэвчийн мөнгө тохируулах"""
        amt = parse_amount(amount, 0)
        if amt is None:
            await send_usage(ctx)
            return
        await self.bot.db.set_balance(member.id, amt)
        await reply(ctx, f"✅ {member.mention}-ийн хэтэвчийг **{fmt(amt)}** болголоо.")

    @commands.command(name="addmoney", aliases=["devgive", "mint"])
    @commands.is_owner()
    async def addmoney(self, ctx: commands.Context, member: discord.Member, amount: str):
        """Bot Owner: хэрэглэгчийн хэтэвчид мөнгө нэмэх (төлбөргүй)"""
        amt = parse_amount(amount, 10**12)
        if not amt or amt <= 0:
            await send_usage(ctx)
            return
        await self.bot.db.add_balance(member.id, amt)
        await reply(ctx, f"✅ {member.mention}-д **{fmt(amt)}** нэмлээ.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
