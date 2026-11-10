import re
import time

import discord
from discord.ext import commands

from items import find_items
from perms import is_admin
from ui import OwnerView, nav_button
from utils import fmt, parse_amount, parse_qty, reply

# слайд бүр: (гарчиг, emoji, тайлбар, [(команд, тайлбар)])
SLIDES = [
    ("Танилцуулга", "🛠️",
     "Админ бол Minecraft-ийн creative/op шиг тусгай эрхтэй хүн. Ботын эзэн бүх админ эрхтэй.\n"
     "`<>` заавал, `[]` заавал биш. `@хүн` гэдэгт Discord-оор дурдсан хүн эсвэл ID бичнэ.\n\n"
     "◀ ▶ товчоор слайдуудыг эргүүлнэ, цэснээс шууд сонгож болно.",
     [("admin", "Энэ цэс"), ("admin list", "Админуудын жагсаалт")]),
    ("Мөнгө", "💰", "Хүний мөнгийг нэмэх, хураах, тохируулах.",
     [("admin give @хүн <дүн>", "Хэтэвчинд мөнгө өгөх"),
      ("admin take @хүн <дүн|all>", "Мөнгө хураах (хэтэвч, дараа нь банкнаас). Хураасан нь татварын санд орно"),
      ("admin set @хүн <дүн>", "Хэтэвчийн мөнгийг яг тэр дүн болгох")]),
    ("Бараа", "🎒", "Цүнхэнд бараа өгөх, авах. ID нь `shop` дээрх ID (жишээ нь `revive`, `gold`).",
     [("admin item @хүн <ID> [тоо]", "Бараа өгөх"),
      ("admin takeitem @хүн <ID> [тоо]", "Бараа хураах")]),
    ("Амьдрал", "💖", "Үхсэн дүрийг амилуулах, хоолны хугацааг шинэчлэх.",
     [("admin revive @хүн", "Revive Active-гүйгээр амилуулах"),
      ("admin kill @хүн", "Дүрийг үхүүлэх"),
      ("admin feed @хүн", "Бүрэн цатгах")]),
    ("Шорон", "⛓️", "Хүнийг шоронд хийх, суллах.",
     [("admin jail @хүн [цаг]", "Шоронд хийх (анхдагч 12 цаг)"),
      ("admin unjail @хүн", "Суллах")]),
    ("Сан, Giveaway", "🏛️", "Татвар (10%) болон хураасан мөнгө татварын санд хуримтлагдана.",
     [("pool", "Сангийн үлдэгдэл (бүгд харна)"),
      ("admin pool add <дүн>", "Санд мөнгө нэмэх"),
      ("admin pool take <дүн>", "Сангаас хасах"),
      ("giveaway <дүн|pool> <10m|2h|1d> [ялагч]", "Giveaway эхлүүлэх")]),
    ("Админ томилох", "👮", "Зөвхөн ботын эзэн.",
     [("admin op @хүн", "Админ болгох"), ("admin deop @хүн", "Админ эрхийг авах"),
      ("admin reset @хүн confirm", "Хүний бүх өгөгдлийг устгах (аюултай!)")]),
]


class AdminView(OwnerView):
    def __init__(self, owner_id: int, prefix: str):
        super().__init__(owner_id, timeout=180)
        self.prefix, self.page = prefix, 0
        self.select = discord.ui.Select(
            placeholder="Хэсэг сонгох",
            options=[discord.SelectOption(label=t, value=str(i), emoji=e) for i, (t, e, _, _) in enumerate(SLIDES)],
        )
        self.select.callback = self.on_select
        self.prev = nav_button("◀", self.on_prev)
        self.nxt = nav_button("▶", self.on_next)
        for c in (self.select, self.prev, self.nxt):
            self.add_item(c)
        self._sync()

    def _sync(self):
        self.prev.disabled = self.page <= 0
        self.nxt.disabled = self.page >= len(SLIDES) - 1

    def embed(self) -> discord.Embed:
        title, emoji, desc, cmds = SLIDES[self.page]
        embed = discord.Embed(title=f"{emoji} Админ: {title}", description=desc, color=0xEF4444)
        embed.add_field(
            name="Командууд",
            value="\n".join(f"`{self.prefix}{c}`\n> {d}" for c, d in cmds),
            inline=False,
        )
        embed.set_footer(text=f"Слайд {self.page + 1}/{len(SLIDES)}")
        return embed

    async def _show(self, interaction):
        self._sync()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def on_select(self, interaction):
        self.page = int(self.select.values[0])
        await self._show(interaction)

    async def on_prev(self, interaction):
        self.page = max(0, self.page - 1)
        await self._show(interaction)

    async def on_next(self, interaction):
        self.page = min(len(SLIDES) - 1, self.page + 1)
        await self._show(interaction)


async def get_member(ctx, text: str):
    m = re.fullmatch(r"<@!?(\d+)>|(\d{15,25})", text.strip())
    if not m:
        return None
    uid = int(m.group(1) or m.group(2))
    member = ctx.guild.get_member(uid)
    if member is None:
        try:
            member = await ctx.guild.fetch_member(uid)
        except Exception:
            return None
    return member


class Admin(commands.Cog):
    """Админы тусгай эрх (Minecraft-ийн op шиг)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    async def _deny(self, ctx):
        await reply(ctx, "🚫 Энэ командыг зөвхөн админ ашиглана.")

    @commands.command(name="admin", aliases=["adm"])
    async def admin(self, ctx: commands.Context, *args: str):
        """Админы цэс ба командууд: admin [give | take | set | item | revive | ...]"""
        if not await is_admin(self.bot, ctx.author):
            await self._deny(ctx)
            return
        if not args:
            view = AdminView(ctx.author.id, ctx.clean_prefix)
            view.message = await reply(ctx, embed=view.embed(), view=view)
            return
        sub, rest = args[0].lower(), list(args[1:])
        handler = getattr(self, f"_do_{sub}", None)
        if handler is None:
            await reply(ctx, f"❓ Ийм админ команд алга. `{ctx.clean_prefix}admin` гэж цэсийг хараарай.")
            return
        await handler(ctx, rest)

    # ---- туслах ----
    async def _target(self, ctx, rest, need: int):
        if len(rest) < need or not rest:
            await reply(ctx, f"❌ Дутуу байна. `{ctx.clean_prefix}admin` цэснээс хэрэглээг хараарай.")
            return None
        member = await get_member(ctx, rest[0])
        if member is None:
            await reply(ctx, "❌ Хүн олдсонгүй. @дурдаж эсвэл ID бичнэ үү.")
            return None
        return member

    # ---- мөнгө ----
    async def _do_give(self, ctx, rest):
        m = await self._target(ctx, rest, 2)
        if m is None:
            return
        amt = parse_amount(rest[1], 0)
        if not amt:
            await reply(ctx, "❌ Дүн буруу.")
            return
        await self.bot.db.add_balance(m.id, amt)
        await reply(ctx, f"✅ {m.mention}-д **{fmt(amt)}** өглөө.")

    async def _do_take(self, ctx, rest):
        m = await self._target(ctx, rest, 2)
        if m is None:
            return
        amt = parse_amount(rest[1], 10**15)
        if not amt:
            await reply(ctx, "❌ Дүн буруу.")
            return
        taken = await self.bot.db.confiscate(m.id, amt)
        await reply(ctx, f"🧾 {m.mention}-аас **{fmt(taken)}** хураалаа (татварын санд орлоо).")

    async def _do_set(self, ctx, rest):
        m = await self._target(ctx, rest, 2)
        if m is None:
            return
        raw = rest[1].strip().lower()
        amt = 0 if raw in ("0", "zero") else parse_amount(raw, 0)
        if amt is None:
            await reply(ctx, "❌ Дүн буруу.")
            return
        await self.bot.db.set_balance(m.id, amt)
        await reply(ctx, f"✅ {m.mention}-ийн хэтэвч **{fmt(amt)}** боллоо.")

    # ---- бараа ----
    async def _item(self, ctx, rest):
        m = await self._target(ctx, rest, 2)
        if m is None:
            return None
        found = find_items(rest[1])
        if len(found) != 1:
            await reply(ctx, "❌ Бараа олдсонгүй эсвэл олон байна. Яг ID бичнэ үү.")
            return None
        qty = parse_qty(rest[2] if len(rest) > 2 else None, 1, 10000)
        if qty is None:
            await reply(ctx, "❌ Тоо буруу.")
            return None
        return m, found[0], qty

    async def _do_item(self, ctx, rest):
        res = await self._item(ctx, rest)
        if res is None:
            return
        m, it, qty = res
        await self.bot.db.add_item(m.id, it.key, qty)
        await reply(ctx, f"🎁 {m.mention}-д {it.emoji} **{it.name} × {qty}** өглөө.")

    async def _do_takeitem(self, ctx, rest):
        res = await self._item(ctx, rest)
        if res is None:
            return
        m, it, qty = res
        if not await self.bot.db.remove_item(m.id, it.key, qty):
            await reply(ctx, "❌ Тэр хүнд хангалттай бараа алга.")
            return
        await reply(ctx, f"🧾 {m.mention}-аас {it.emoji} **{it.name} × {qty}** хураалаа.")

    # ---- амьдрал ----
    async def _do_revive(self, ctx, rest):
        m = await self._target(ctx, rest, 1)
        if m is None:
            return
        await self.bot.db.set_dead(m.id, False, time.time())
        await reply(ctx, f"💖 {m.mention}-г амилууллаа.")

    async def _do_kill(self, ctx, rest):
        m = await self._target(ctx, rest, 1)
        if m is None:
            return
        await self.bot.db.set_dead(m.id, True, time.time())
        await reply(ctx, f"💀 {m.mention}-ийн дүр үхлээ.")

    async def _do_feed(self, ctx, rest):
        m = await self._target(ctx, rest, 1)
        if m is None:
            return
        await self.bot.db.set_last_fed(m.id, time.time())
        await reply(ctx, f"🍞 {m.mention} бүрэн цатгалаа.")

    # ---- шорон ----
    async def _do_jail(self, ctx, rest):
        m = await self._target(ctx, rest, 1)
        if m is None:
            return
        hours = int(rest[1]) if len(rest) > 1 and rest[1].isdigit() else 12
        await self.bot.db.jail(m.id, time.time() + hours * 3600, 0)
        await reply(ctx, f"⛓️ {m.mention}-г **{hours} цаг** шоронд хийлээ.")

    async def _do_unjail(self, ctx, rest):
        m = await self._target(ctx, rest, 1)
        if m is None:
            return
        await self.bot.db.jail(m.id, 0, 0)
        await reply(ctx, f"🔓 {m.mention}-г суллалаа.")

    # ---- сан ----
    async def _do_pool(self, ctx, rest):
        db = self.bot.db
        if len(rest) >= 2 and rest[0].lower() in ("add", "take"):
            amt = parse_amount(rest[1], 0)
            if not amt:
                await reply(ctx, "❌ Дүн буруу.")
                return
            if rest[0].lower() == "add":
                await db.add_setting("pool", amt)
            elif not await db.take_pool(amt):
                await reply(ctx, "❌ Санд хангалттай мөнгө алга.")
                return
        await reply(ctx, f"🏛️ Татварын сан: **{fmt(await db.get_setting('pool'))}**")

    # ---- админ томилгоо (зөвхөн эзэн) ----
    async def _owner_only(self, ctx) -> bool:
        if not await self.bot.is_owner(ctx.author):
            await reply(ctx, "🚫 Зөвхөн ботын эзэн админ томилно.")
            return False
        return True

    async def _do_op(self, ctx, rest):
        if not await self._owner_only(ctx):
            return
        m = await self._target(ctx, rest, 1)
        if m is None:
            return
        await self.bot.db.add_admin(m.id)
        await reply(ctx, f"👮 {m.mention} админ боллоо.")

    async def _do_deop(self, ctx, rest):
        if not await self._owner_only(ctx):
            return
        m = await self._target(ctx, rest, 1)
        if m is None:
            return
        ok = await self.bot.db.remove_admin(m.id)
        await reply(ctx, f"✅ {m.mention}-ийн админ эрх хасагдлаа." if ok else "ℹ️ Энэ хүн админ биш байна.")

    async def _do_list(self, ctx, rest):
        ids = await self.bot.db.list_admins()
        text = "\n".join(f"<@{i}>" for i in ids) or "*Томилогдсон админ алга. Ботын эзэн бүх эрхтэй.*"
        await reply(ctx, embed=discord.Embed(title="👮 Админууд", description=text, color=0xEF4444))

    async def _do_reset(self, ctx, rest):
        if not await self._owner_only(ctx):
            return
        m = await self._target(ctx, rest, 2)
        if m is None:
            return
        if rest[1].lower() != "confirm":
            await reply(ctx, f"⚠️ Баталгаажуулахдаа `{ctx.clean_prefix}admin reset @хүн confirm` гэж бичнэ.")
            return
        await self.bot.db.reset_user(m.id)
        await reply(ctx, f"🗑️ {m.mention}-ийн өгөгдлийг устгалаа.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
