import time

import discord
from discord.ext import commands

from items import get_item
from perms import admin_only
from ui import OwnerView, nav_button
from usage import send_usage
from utils import MAX_STRENGTH, fmt, parse_amount, parse_qty, reply

COOLDOWN_COLS = ["last_work", "last_workout", "last_daily", "last_burglary", "last_rob",
                 "last_hack", "last_mine", "last_train", "jail_until", "protect_until"]

# Admin слайд: (гарчиг, emoji, [(команд, тайлбар)])
SLIDES = [
    ("Мөнгө", "💰", "Minecraft-ийн creative горим шиг — админ мөнгийг хязгааргүй удирдана.", [
        ("admin give <@хүн> <дүн>", "Хүнд мөнгө үүсгэж өгөх (татваргүй)"),
        ("admin take <@хүн> <дүн>", "Хүнээс мөнгө хасах (хэтэвчнээс)"),
        ("admin set <@хүн> <дүн>", "Хэтэвчийн мөнгийг яг тэр дүн болгох"),
    ]),
    ("Эд зүйл", "🎒", "Дэлгүүрт зарагддаггүй ч бүх бараа админд нээлттэй (Revive Active, хайрцаг гэх мэт).", [
        ("admin item <@хүн> <ID> [тоо]", "Хүнд эд зүйл өгөх"),
        ("admin remove <@хүн> <ID> [тоо]", "Хүнээс эд зүйл авах"),
    ]),
    ("Тоглогч", "🧍", "Тоглогчийн төлөв байдлыг тохируулна.", [
        ("admin revive <@хүн>", "Үхсэн хүнийг Revive Active-гүйгээр амилуулах"),
        ("admin kill <@хүн>", "Хүнийг үхүүлэх"),
        ("admin feed <@хүн>", "Хүнийг цатгах (өлсөлтийг арилгах)"),
        ("admin jail <@хүн> [минут]", "Шоронд хийх (анхдагч 60 мин)"),
        ("admin free <@хүн>", "Шоронгоос гаргах"),
        ("admin strength <@хүн> <0-30>", "Хүчийг тохируулах"),
        ("admin cooldown <@хүн>", "Бүх хүлээх хугацааг (work, daily, mine...) арилгах"),
        ("admin reset <@хүн>", "Character-ийг устгах (дахин бүртгүүлнэ)"),
    ]),
    ("Сан & Giveaway", "🏛️", "Татварын сан болон giveaway.", [
        ("admin treasury add <дүн>", "Татварын санд мөнгө нэмэх"),
        ("admin treasury take <дүн>", "Сангаас мөнгө авах"),
        ("treasury", "Сангийн үлдэгдэл харах (хүн бүр)"),
        ("giveaway <дүн|all> <30m|2h|1d> [ялагч]", "Сангаас giveaway эхлүүлэх"),
    ]),
]


def slide_embed(i: int, p: str) -> discord.Embed:
    name, emoji, intro, cmds = SLIDES[i]
    lines = [f"`{p}{c}`\n> {d}" for c, d in cmds]
    embed = discord.Embed(
        title=f"{emoji} Admin · {name}",
        description=f"*{intro}*\n\n" + "\n".join(lines),
        color=0xEF4444,
    )
    embed.set_footer(text=f"Слайд {i + 1}/{len(SLIDES)} · Owner эсвэл Administrator эрхтэй хүн ашиглана")
    return embed


class AdminSlides(OwnerView):
    def __init__(self, ctx):
        super().__init__(ctx.author.id, timeout=180)
        self.ctx, self.i = ctx, 0
        self.prev_btn = nav_button("◀", self.on_prev)
        self.label = nav_button(f"1/{len(SLIDES)}", self.on_noop, disabled=True)
        self.next_btn = nav_button("▶", self.on_next)
        for b in (self.prev_btn, self.label, self.next_btn):
            self.add_item(b)
        self._sync()

    def _sync(self):
        self.prev_btn.disabled = self.i <= 0
        self.next_btn.disabled = self.i >= len(SLIDES) - 1
        self.label.label = f"{self.i + 1}/{len(SLIDES)}"

    async def _show(self, interaction):
        self._sync()
        await interaction.response.edit_message(embed=slide_embed(self.i, self.ctx.clean_prefix), view=self)

    async def on_prev(self, interaction):
        self.i -= 1
        await self._show(interaction)

    async def on_next(self, interaction):
        self.i += 1
        await self._show(interaction)

    async def on_noop(self, interaction):
        await interaction.response.defer()


class Admin(commands.Cog):
    """Админы тусгай эрх (Minecraft creative горим шиг)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.group(name="admin", invoke_without_command=True)
    @admin_only()
    async def admin(self, ctx: commands.Context):
        """Admin: тайлбартай слайд харуулна"""
        view = AdminSlides(ctx)
        view.message = await reply(ctx, embed=slide_embed(0, ctx.clean_prefix), view=view)

    @admin.command(name="give")
    @admin_only()
    async def a_give(self, ctx, member: discord.Member, amount: str):
        amt = parse_amount(amount, 0)
        if not amt or amt > 10**12:
            return await send_usage(ctx, self.a_give)
        await self.bot.db.add_balance(member.id, amt)
        await reply(ctx, f"✅ {member.mention}-д **{fmt(amt)}** өглөө.")

    @admin.command(name="take")
    @admin_only()
    async def a_take(self, ctx, member: discord.Member, amount: str):
        user = await self.bot.db.get_user(member.id)
        amt = parse_amount(amount, user["balance"])
        if not amt:
            return await send_usage(ctx, self.a_take)
        new = max(0, user["balance"] - amt)
        await self.bot.db.set_balance(member.id, new)
        await reply(ctx, f"✅ {member.mention}-ийн хэтэвчнээс **{fmt(user['balance'] - new)}** хасагдлаа.")

    @admin.command(name="set")
    @admin_only()
    async def a_set(self, ctx, member: discord.Member, amount: str):
        amt = parse_amount(amount, 0)
        if amt is None:
            return await send_usage(ctx, self.a_set)
        await self.bot.db.set_balance(member.id, amt)
        await reply(ctx, f"✅ {member.mention}-ийн хэтэвч **{fmt(amt)}** боллоо.")

    @admin.command(name="item")
    @admin_only()
    async def a_item(self, ctx, member: discord.Member, item_id: str, qty: str = "1"):
        it, n = get_item(item_id.lower()), parse_qty(qty, 1, 1000)
        if it is None or n is None:
            return await reply(ctx, "❌ Бараа олдсонгүй эсвэл тоо буруу (ID-г `qshop`-оос хар).")
        await self.bot.db.add_item(member.id, it.key, n)
        await reply(ctx, f"✅ {member.mention}-д {it.emoji} **{it.name}** × {n} өглөө.")

    @admin.command(name="remove")
    @admin_only()
    async def a_remove(self, ctx, member: discord.Member, item_id: str, qty: str = "1"):
        it, n = get_item(item_id.lower()), parse_qty(qty, 1, 1000)
        if it is None or n is None:
            return await reply(ctx, "❌ Бараа олдсонгүй эсвэл тоо буруу.")
        ok = await self.bot.db.remove_item(member.id, it.key, n)
        await reply(ctx, f"✅ {it.emoji} {it.name} × {n} авлаа." if ok else "❌ Тэр хүнд хангалттай алга.")

    @admin.command(name="revive")
    @admin_only()
    async def a_revive(self, ctx, member: discord.Member):
        await self.bot.db.set_dead(member.id, False, time.time())
        await reply(ctx, f"💖 {member.mention}-г амилууллаа.")

    @admin.command(name="kill")
    @admin_only()
    async def a_kill(self, ctx, member: discord.Member):
        await self.bot.db.set_dead(member.id, True)
        await reply(ctx, f"💀 {member.mention} нас барлаа.")

    @admin.command(name="feed")
    @admin_only()
    async def a_feed(self, ctx, member: discord.Member):
        await self.bot.db.set_last_fed(member.id, time.time())
        await reply(ctx, f"🍞 {member.mention}-г цатгалаа.")

    @admin.command(name="jail")
    @admin_only()
    async def a_jail(self, ctx, member: discord.Member, minutes: str = "60"):
        n = parse_qty(minutes, 60, 10_080)
        if n is None:
            return await send_usage(ctx, self.a_jail)
        await self.bot.db.jail(member.id, time.time() + n * 60, 0)
        await reply(ctx, f"⛓️ {member.mention}-г {n} минут шоронд хийлээ.")

    @admin.command(name="free")
    @admin_only()
    async def a_free(self, ctx, member: discord.Member):
        await self.bot.db.set_column(member.id, "jail_until", 0)
        await reply(ctx, f"🔓 {member.mention}-г шоронгоос гаргалаа.")

    @admin.command(name="strength")
    @admin_only()
    async def a_strength(self, ctx, member: discord.Member, value: str):
        if not value.isdigit() or int(value) > MAX_STRENGTH:
            return await reply(ctx, f"❌ Хүч 0-{MAX_STRENGTH} хооронд байна.")
        await self.bot.db.set_strength(member.id, int(value))
        await reply(ctx, f"💪 {member.mention}-ийн хүч **{value}** боллоо.")

    @admin.command(name="cooldown", aliases=["cd"])
    @admin_only()
    async def a_cooldown(self, ctx, member: discord.Member):
        for col in COOLDOWN_COLS:
            await self.bot.db.set_column(member.id, col, 0)
        await reply(ctx, f"⏱️ {member.mention}-ийн бүх хүлээх хугацааг арилгалаа.")

    @admin.command(name="reset")
    @admin_only()
    async def a_reset(self, ctx, member: discord.Member):
        await self.bot.db.delete_profile(member.id)
        await reply(ctx, f"🗑️ {member.mention}-ийн character устлаа. Дахин бүртгүүлнэ.")

    @admin.command(name="treasury")
    @admin_only()
    async def a_treasury(self, ctx, action: str = None, amount: str = None):
        pool = await self.bot.db.treasury_get()
        amt = parse_amount(amount, pool) if amount else None
        if action not in ("add", "take") or not amt:
            return await send_usage(ctx, self.a_treasury)
        if action == "add":
            await self.bot.db.treasury_add(amt)
            await reply(ctx, f"🏛️ Санд **{fmt(amt)}** нэмлээ.")
        elif await self.bot.db.treasury_take(amt):
            await reply(ctx, f"🏛️ Сангаас **{fmt(amt)}** авлаа.")
        else:
            await reply(ctx, f"❌ Санд хүрэлцэхгүй. Сан: {fmt(pool)}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
