import random
import time
from collections import Counter
from dataclasses import dataclass

import discord
from discord.ext import commands

from actions import activate_shield
from items import get_pet, random_loot
from ui import OwnerView, nav_button
from usage import send_usage
from utils import (
    JAIL_SECONDS,
    fmt,
    fmt_duration,
    fmt_short,
    hint_use,
    jailed,
    reply,
)

BURGLARY_COOLDOWN = 60 * 60  # 1 цаг
ROB_COOLDOWN = 30 * 60
HACK_COOLDOWN = 60 * 60
FALCON_CASH_BONUS = 1.25
DOG_BONUS = 10

ROB_PCT = (0.01, 0.04)  # дээрэмдэх хувь (өмчлөгчийн хэтэвчнээс)
ROB_CAP = 250_000
ROB_MIN_TARGET = 20_000
ROB_FAIL_FINE = (20_000, 60_000)

HACK_PCT = (0.01, 0.03)  # хакердах хувь (банкнаас)
HACK_CAP = 200_000
HACK_MIN_TARGET = 50_000
HACK_FAIL_FINE = (30_000, 80_000)

FINE_MIN, FINE_MAX = 60_000, 250_000


@dataclass(frozen=True)
class Target:
    key: str
    emoji: str
    name: str
    base: int  # суурь амжилтын магадлал, %
    items: tuple[int, int]  # олох барааны тоо
    cash: tuple[int, int]  # олох бэлэн мөнгө
    rare: float  # металл, үнэт эдлэл олох магадлал


TARGETS = [
    Target("ger", "🛖", "Хуучин гэр", 75, (1, 2), (5_000, 20_000), 0.02),
    Target("flat", "🏢", "Орон сууц", 60, (2, 3), (10_000, 40_000), 0.04),
    Target("yard", "🏡", "Хашаа байшин", 50, (2, 4), (20_000, 70_000), 0.06),
    Target("cottage", "🏘️", "Хоёр давхар коттедж", 35, (3, 5), (50_000, 150_000), 0.10),
    Target("mansion", "🏰", "Баян айлын харш", 20, (4, 7), (100_000, 300_000), 0.18),
]


def find_target(arg: str) -> Target | None:
    a = arg.strip().casefold()
    if a.isdigit() and 1 <= int(a) <= len(TARGETS):
        return TARGETS[int(a) - 1]
    for t in TARGETS:
        if a == t.key or a in t.name.casefold():
            return t
    return None


def success_chance(base: int, strength: int, pet_key: str | None) -> int:
    chance = base + strength + (DOG_BONUS if pet_key == "dog" else 0)
    return max(5, min(90, chance))


def calc_fine(wallet: int) -> int:
    """Торгууль: хэтэвчний мөнгөнөөс хамаарч 60,000-250,000₮ хооронд санамсаргүй."""
    raw = int(wallet * random.uniform(0.10, 0.30))
    return max(FINE_MIN, min(FINE_MAX, round(raw, -3)))


def calc_bail(fine: int) -> int:
    return max(FINE_MIN, round(int(fine * 1.5), -3))


class CaughtView(OwnerView):
    """Баригдсан үед: шорон суух эсвэл шууд торгууль төлөх."""

    def __init__(self, cog, ctx, fine: int, bail: int):
        super().__init__(ctx.author.id, timeout=60)
        self.cog, self.ctx, self.fine, self.bail = cog, ctx, fine, bail
        self.resolved = False
        self.add_item(
            nav_button(f"⛓️ Шорон суух ({fmt_short(JAIL_SECONDS)})", self.on_jail, discord.ButtonStyle.secondary)
        )
        self.add_item(
            nav_button(f"💸 Торгууль төлөх ({fmt(fine)})", self.on_pay, discord.ButtonStyle.danger)
        )

    def _jail_embed(self, auto: bool = False) -> discord.Embed:
        p = self.ctx.clean_prefix
        note = " (хугацаандаа сонголт хийгээгүй тул)" if auto else ""
        return discord.Embed(
            title="⛓️ Шоронд суулаа",
            description=(
                f"Та **{fmt_short(JAIL_SECONDS)}** шоронд суух болно{note}.\n"
                f"Эрт гарах: `{p}bail` ({fmt(self.bail)})"
            ),
            color=0x6B7280,
        )

    async def on_jail(self, interaction):
        if self.resolved:
            await interaction.response.defer()
            return
        self.resolved = True
        await self.cog.bot.db.jail(self.ctx.author.id, time.time() + JAIL_SECONDS, self.bail)
        self.disable_all()
        self.stop()
        await interaction.response.edit_message(embed=self._jail_embed(), view=self)

    async def on_pay(self, interaction):
        if self.resolved:
            await interaction.response.defer()
            return
        if not await self.cog.bot.db.spend(self.ctx.author.id, self.fine):
            await interaction.response.send_message(
                f"❌ Хэтэвчинд **{fmt(self.fine)}** хүрэлцэхгүй байна. Шорон суух сонголтыг ашиглана уу.",
                ephemeral=True,
            )
            return
        self.resolved = True
        embed = discord.Embed(
            title="💸 Торгууль төлөв",
            description=f"Та **{fmt(self.fine)}** төлж суллагдлаа. Дахиж баригдахгүй байхыг хичээгээрэй!",
            color=0xF59E0B,
        )
        self.disable_all()
        self.stop()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.resolved:
            return
        self.resolved = True
        await self.cog.bot.db.jail(self.ctx.author.id, time.time() + JAIL_SECONDS, self.bail)
        self.disable_all()
        if self.message is not None:
            try:
                await self.message.edit(embed=self._jail_embed(auto=True), view=self)
            except Exception:
                pass


class Crime(commands.Cog):
    """Хулгай, дээрэм, хакер, шорон, хамгаалалт."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    # ---------- байшин дээрэмдэх ----------
    @commands.command(name="steal", aliases=["hulgai"])
    async def steal(self, ctx: commands.Context, house: str = None):
        """Байшинд нууцаар орох: steal [1-5]. Хоосон бол жагсаалт"""
        p = ctx.clean_prefix
        user = await self.bot.db.get_user(ctx.author.id)
        pet_key = user["pet"]

        if house is None:
            lines = [
                f"`{n}` {t.emoji} **{t.name}** — амжилт {success_chance(t.base, user['strength'], pet_key)}%"
                for n, t in enumerate(TARGETS, 1)
            ]
            embed = discord.Embed(
                title="🏠 Аль байшинд орох вэ?",
                description="\n".join(lines),
                color=0x6B7280,
            )
            embed.set_footer(
                text=f"Жишээ: {p}steal 3 · баригдвал шорон суух эсвэл торгууль төлнө · хүч нэмэх: {p}workout"
            )
            await reply(ctx, embed=embed)
            return

        target = find_target(house)
        if target is None:
            await reply(ctx, f"❌ Байшин олдсонгүй. `{p}steal` гэж жагсаалтыг харна уу.")
            return
        if await jailed(ctx, user):
            return

        now = time.time()
        if not await self.bot.db.start_cooldown(ctx.author.id, "last_burglary", now, BURGLARY_COOLDOWN):
            left = user["last_burglary"] + BURGLARY_COOLDOWN - now
            await reply(ctx, f"🕵️ Цагдаа тойрон эргэлдэж байна. **{fmt_duration(left)}**-ийн дараа дахин оролдоно.")
            return

        chance = success_chance(target.base, user["strength"], pet_key)
        pet = get_pet(pet_key)

        if random.randint(1, 100) <= chance:
            loot = random_loot(random.randint(*target.items), target.rare)
            cash = random.randint(*target.cash)
            if pet and pet.key == "falcon":
                cash = int(cash * FALCON_CASH_BONUS)
            for it in loot:
                await self.bot.db.add_item(ctx.author.id, it.key, 1)
            await self.bot.db.add_balance(ctx.author.id, cash)

            counts = Counter(it.key for it in loot)
            by_key = {it.key: it for it in loot}
            lines = [f"{by_key[k].emoji} {by_key[k].name} × {c}" for k, c in counts.items()]
            value = sum(it.price for it in loot)

            embed = discord.Embed(
                title=f"{target.emoji} Хулгай амжилттай!",
                description=f"**{target.name}**-д шөнө нууцаар орлоо.",
                color=0x22C55E,
            )
            embed.add_field(name="🎒 Олсон бараа", value="\n".join(lines), inline=False)
            embed.add_field(name="💵 Бэлэн мөнгө", value=fmt(cash), inline=True)
            embed.add_field(name="💎 Барааны үнэ", value=fmt(value), inline=True)
            embed.set_footer(text=f"Амжилтын магадлал {chance}% · {hint_use(p)}")
            await reply(ctx, embed=embed)
            return

        fine = calc_fine(user["balance"])
        bail = calc_bail(fine)
        embed = discord.Embed(
            title="🚔 Баригдлаа!",
            description=f"**{target.name}**-ийн эзэн сэрж, цагдаа дуудлаа.\nТа юу хийх вэ? (60 секундэд сонгоно)",
            color=0xEF4444,
        )
        embed.add_field(name="💸 Торгууль", value=fmt(fine), inline=True)
        embed.add_field(name="⛓️ Шорон", value=f"{fmt_short(JAIL_SECONDS)} (барьцаа {fmt(bail)})", inline=True)
        embed.set_footer(text=f"Амжилтын магадлал {chance}% байсан")
        view = CaughtView(self, ctx, fine, bail)
        view.message = await reply(ctx, embed=embed, view=view)

    # ---------- хүнийг дээрэмдэх ----------
    async def _precheck_target(self, ctx, member: discord.Member):
        """Хамгаалагдсан эсэх зэргийг шалгана. (victim_row) эсвэл None."""
        if member.id == ctx.author.id:
            await reply(ctx, "❌ Өөрийгөө дээрэмдэх боломжгүй.")
            return None
        if member.bot:
            await reply(ctx, "❌ Бот дээрэмдэх боломжгүй.")
            return None
        victim = await self.bot.db.get_user(member.id)
        left = victim["protect_until"] - time.time()
        if left > 0:
            await reply(
                ctx,
                f"🛡️ {member.mention} хамгаалагдсан байна ({fmt_short(left)} үлдсэн). Дараа оролдоорой.",
            )
            return None
        return victim

    @commands.command(name="rob", aliases=["mug"])
    async def rob(self, ctx: commands.Context, member: discord.Member):
        """Хүний халаасыг дээрэмдэх: rob @хүн"""
        user = await self.bot.db.get_user(ctx.author.id)
        if await jailed(ctx, user):
            return
        victim = await self._precheck_target(ctx, member)
        if victim is None:
            return
        if victim["balance"] < ROB_MIN_TARGET:
            await reply(ctx, f"💨 {member.mention}-ийн халаасанд дээрэмдэх хэмжээний мөнгө алга.")
            return

        now = time.time()
        if not await self.bot.db.start_cooldown(ctx.author.id, "last_rob", now, ROB_COOLDOWN):
            left = user["last_rob"] + ROB_COOLDOWN - now
            await reply(ctx, f"🕵️ Анхааруулга ихэссэн байна. **{fmt_duration(left)}**-ийн дараа дахин оролдоно.")
            return

        pet = get_pet(user["pet"])
        chance = success_chance(45, user["strength"], user["pet"])
        embed = discord.Embed(title="🥷 Дээрэм", color=0x22C55E)
        head = f"**{ctx.author.display_name}** хөдөлж эхэллээ..."

        if random.randint(1, 100) <= chance:
            pct = random.uniform(*ROB_PCT)
            amount = max(1, min(int(victim["balance"] * pct), ROB_CAP))
            if pet and pet.key == "falcon":
                amount = int(amount * FALCON_CASH_BONUS)
            if not await self.bot.db.steal_wallet(ctx.author.id, member.id, amount):
                embed.description = f"{head}\n\n💨 {member.display_name}-ийн халаас хоосон байлаа."
                embed.colour = discord.Colour(0x6B7280)
            else:
                embed.description = (
                    f"{head}\n\n✅ **Цэвэрхэн ажиллагаа!**\n"
                    f"Та {member.display_name}-ийн халааснаас **{fmt(amount)} ({pct * 100:.1f}%)** авчихлаа!"
                )
        else:
            fine = random.randint(*ROB_FAIL_FINE)
            paid = await self.bot.db.pay_to(ctx.author.id, member.id, fine)
            embed.description = (
                f"{head}\n\n🚔 **Алдлаа!** {member.display_name} таныг барьчихлаа.\n"
                f"Та хохирол болгож **{fmt(paid)}** төллөө."
            )
            embed.colour = discord.Colour(0xEF4444)
        embed.set_footer(text=f"Амжилтын магадлал {chance}% · дараагийн дээрэм 30 минутын дараа")
        await reply(ctx, embed=embed)

    @commands.command(name="hack")
    async def hack(self, ctx: commands.Context, member: discord.Member):
        """Банкны данс руу хакердах: hack @хүн (байшиндаа компьютертой байх ёстой)"""
        p = ctx.clean_prefix
        user = await self.bot.db.get_user(ctx.author.id)
        if await jailed(ctx, user):
            return
        placed = await self.bot.db.get_house_items(ctx.author.id)
        if not any(r["item_key"] == "computer" for r in placed):
            await reply(
                ctx,
                f"💻 Хакердахын тулд байшиндаа компьютер байрлуулсан байх ёстой.\n"
                f"`{p}buy computer` → `{p}house office use computer`",
            )
            return
        victim = await self._precheck_target(ctx, member)
        if victim is None:
            return
        if victim["bank"] < HACK_MIN_TARGET:
            await reply(ctx, f"💨 {member.mention}-ийн банкны данс хакердах хэмжээнд хүрээгүй байна.")
            return

        now = time.time()
        if not await self.bot.db.start_cooldown(ctx.author.id, "last_hack", now, HACK_COOLDOWN):
            left = user["last_hack"] + HACK_COOLDOWN - now
            await reply(ctx, f"⌛ Систем халсан байна. **{fmt_duration(left)}**-ийн дараа дахин хакердана.")
            return

        chance = max(5, min(80, 40 + user["strength"] // 2))
        embed = discord.Embed(title="💻 Хакердалт", color=0x22C55E)
        head = f"**{ctx.author.display_name}** сүлжээнд нэвтэрч байна..."
        if random.randint(1, 100) <= chance:
            pct = random.uniform(*HACK_PCT)
            amount = max(1, min(int(victim["bank"] * pct), HACK_CAP))
            if not await self.bot.db.steal_bank(ctx.author.id, member.id, amount):
                embed.description = f"{head}\n\n💨 Данс хоосон байлаа."
                embed.colour = discord.Colour(0x6B7280)
            else:
                embed.description = (
                    f"{head}\n\n✅ **Хакердалт амжилттай!**\n"
                    f"Та {member.display_name}-ийн банкнаас **{fmt(amount)} ({pct * 100:.1f}%)** шилжүүллээ!"
                )
        else:
            fine = random.randint(*HACK_FAIL_FINE)
            paid = await self.bot.db.pay_to(ctx.author.id, member.id, fine)
            embed.description = (
                f"{head}\n\n🚨 **Хакердалт илэрлээ!** Галт хана таныг барьчихлаа.\n"
                f"Та хохирол болгож **{fmt(paid)}** төллөө."
            )
            embed.colour = discord.Colour(0xEF4444)
        embed.set_footer(text=f"Амжилтын магадлал {chance}% · дараагийн хакердалт 1 цагийн дараа")
        await reply(ctx, embed=embed)

    # ---------- хамгаалалт ----------
    @commands.command(name="block")
    async def block(self, ctx: commands.Context):
        """Хамгаалалтын бамбай ашиглах (2.5 цаг)"""
        await activate_shield(self.bot, ctx)

    # ---------- шорон ----------
    @commands.command(name="bail")
    async def bail(self, ctx: commands.Context):
        """Барьцаа төлж шоронгоос гарах"""
        user = await self.bot.db.get_user(ctx.author.id)
        now = time.time()
        left = user["jail_until"] - now
        if left <= 0:
            await reply(ctx, "✅ Та шоронд байхгүй байна.")
            return

        bail = user["jail_bail"]
        embed = discord.Embed(
            title="⛓️ Шороноос гарах",
            description=f"Та **{fmt_short(left)}** шоронд үлдэж байна.",
            color=0x6B7280,
        )
        embed.add_field(name="💸 Bail төлбөр", value=fmt(bail), inline=True)
        embed.add_field(name="💰 Таны түрийвч", value=fmt(user["balance"]), inline=True)
        if user["balance"] < bail:
            embed.add_field(
                name="❌ Мөнгө хүрэлцэхгүй", value="Шорон хоригдох хугацааг хүлээнэ үү.", inline=False
            )
            await reply(ctx, embed=embed)
            return
        result = await self.bot.db.pay_bail(ctx.author.id, now)
        if result != "ok":
            embed.add_field(name="❌ Мөнгө хүрэлцэхгүй", value="Шорон хоригдох хугацааг хүлээнэ үү.", inline=False)
            await reply(ctx, embed=embed)
            return
        done = discord.Embed(
            title="✅ Батлан даалтад гарлаа",
            description=f"Та **{fmt(bail)}** төлж шоронгоос суллагдлаа.",
            color=0x22C55E,
        )
        await reply(ctx, embed=done)


async def setup(bot: commands.Bot):
    await bot.add_cog(Crime(bot))
