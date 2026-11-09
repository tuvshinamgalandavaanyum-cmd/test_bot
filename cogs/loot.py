import random
import time
from collections import Counter

import discord
from discord.ext import commands

from items import BOX_ALIASES, BOXES, get_item, random_loot
from usage import send_usage
from utils import MAX_STRENGTH, fmt, fmt_duration, jailed, parse_qty, reply

MINE_COOLDOWN = 90 * 60  # 1.5 цаг
MINE_CHANCE = 0.40  # алт олох магадлал
POISON_SECONDS = 3600
TRAIN_COOLDOWN = 4 * 3600
TRAIN_PRICE = 200_000
TRAIN_GAIN = 3

# Box: 2% Revive Active, 10% азын хор, 10% мөнгөний хор
BOX_REVIVE = 0.02
BOX_POISON_LUCK = 0.10
BOX_POISON_MONEY = 0.10
POISON_MONEY_RATE = 0.10

# Case "Big Cash": (үржвэр, магадлал) — дундаж нь ~96% (мөнгө шатаадаг)
CASE_TIERS = [
    (0.4, 0.525, "🟫 Хүрэл"),
    (0.9, 0.28, "⬜ Мөнгөн"),
    (1.5, 0.13, "🟨 Алтан"),
    (3.0, 0.05, "🟦 Алмаз"),
    (8.0, 0.013, "🟥 Гал"),
    (25.0, 0.002, "🌈 BIG CASH"),
]

MINE_FAILS = [
    "⛏️ Хоосон... Зөвхөн чулуу олдлоо.",
    "🪨 Нэг том чулуу гарлаа. Баяр хүргэе, чи чулуутай боллоо!",
    "🦇 Нэг сарьсан багваахай л гарч ирлээ. Алт алга.",
    "🕳️ Нүх ухсан чинь өөрийнхөө хөлийг дарчихлаа. Алт алга.",
    "😵 Энэ удаа азгүй байна. Дараагийн удаа заавал олно!",
    "🧦 Нэг хуучин оймс олдлоо. Алт биш.",
    "🐀 Хулгана хөөцөлдсөөр алтыг мартчихлаа.",
    "💨 Хоосон агаар... Хүрз хугарсан юм шиг санагдлаа.",
    "🌧️ Бороо орж уурхай шавар болчихлоо. Юу ч олдсонгүй.",
    "🪙 Харин нэг хуучин зоос л олдлоо... 5 төгрөг. Хөөрхий.",
    "🧱 Алтны оронд тоосго гарлаа. Хэн нэгэн энд барилга барьсан бололтой.",
    "🤡 Алт гэж бодсон чинь шар өнгийн хоолны сав болж таарлаа.",
]


def _norm_box(query: str | None):
    if query is None:
        return None
    key = BOX_ALIASES.get(query.strip().lower())
    return get_item(key) if key else None


class Loot(commands.Cog):
    """Хайрцаг/кейс/авдар, алтны уурхай, дасгалжуулагч."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    # ------------------------------------------------------------ box shop
    @commands.command(name="box", aliases=["boxes", "case", "chest"])
    async def box(self, ctx: commands.Context, action: str = None, kind: str = None, qty: str = "1"):
        """Хайрцгийн дэлгүүр: box | box buy <box|case|chest> [тоо]"""
        p = ctx.clean_prefix
        if action is None:
            lines = []
            for b in BOXES:
                short = b.key.lstrip("m")
                lines.append(f"{b.emoji} **{b.name}** — {fmt(b.price)} · `{short}`\n> {b.desc}")
            embed = discord.Embed(
                title="🎁 Хайрцгийн дэлгүүр",
                description="\n\n".join(lines),
                color=0xF59E0B,
            )
            embed.add_field(
                name="Юу гарах вэ?",
                value=(
                    "📦 **Box** — мөнгө, эд зүйл, 2% **Revive Active**, 10% ☠️ азын хор, 10% ☠️ мөнгөний хор\n"
                    "💼 **Case** — Big Cash: мөнгө хожиж/хожигдож болно (x0.4 → x25)\n"
                    "🧰 **Chest** — 3-6 эд зүйл, ховор үнэт эдлэл"
                ),
                inline=False,
            )
            embed.set_footer(text=f"Авах: {p}box buy <box|case|chest> [тоо] · Нээх: {p}open <box|case|chest> [тоо]")
            await reply(ctx, embed=embed)
            return
        if action.lower() not in ("buy", "авах"):
            await send_usage(ctx)
            return
        item = _norm_box(kind)
        n = parse_qty(qty, 1, 20)
        if item is None or n is None:
            await send_usage(ctx)
            return
        total = item.price * n
        if not await self.bot.db.spend(ctx.author.id, total):
            await reply(ctx, f"❌ Мөнгө хүрэлцэхгүй. Нийт **{fmt(total)}** хэрэгтэй.")
            return
        await self.bot.db.add_item(ctx.author.id, item.key, n)
        await reply(ctx, f"🛒 {item.emoji} **{item.name}** × {n} авлаа ({fmt(total)}). Нээх: `{p}open {item.key.lstrip('m')}`")

    # ------------------------------------------------------------ open
    async def _open_box(self, uid: int, summary: dict):
        r = random.random()
        if r < BOX_REVIVE:
            summary["revive"] += 1
        elif r < BOX_REVIVE + BOX_POISON_LUCK:
            summary["poison_luck"] += 1
        elif r < BOX_REVIVE + BOX_POISON_LUCK + BOX_POISON_MONEY:
            summary["poison_money"] += 1
        elif random.random() < 0.5:
            summary["cash"] += random.randint(8, 80) * 1_000
        else:
            for it in random_loot(random.randint(1, 3), rare_chance=0.03):
                summary["items"][it.key] += 1

    def _open_case(self, price: int, summary: dict):
        roll, acc = random.random(), 0.0
        for mult, prob, name in CASE_TIERS:
            acc += prob
            if roll < acc:
                break
        win = int(price * mult)
        summary["cash"] += win
        summary["tiers"][name] += 1

    def _open_chest(self, summary: dict):
        for it in random_loot(random.randint(3, 6), rare_chance=0.25):
            summary["items"][it.key] += 1

    @commands.command(name="open", aliases=["unbox"])
    async def open(self, ctx: commands.Context, kind: str = None, qty: str = "1"):
        """Хайрцаг нээх: open <box|case|chest> [тоо]"""
        item = _norm_box(kind)
        n = parse_qty(qty, 1, 10)
        if item is None or n is None:
            await send_usage(ctx)
            return
        db, uid = self.bot.db, ctx.author.id
        if not await db.remove_item(uid, item.key, n):
            await reply(ctx, f"❌ Танд **{item.name}** × {n} алга. `{ctx.clean_prefix}box buy {item.key.lstrip('m')}`")
            return

        summary = {"cash": 0, "items": Counter(), "revive": 0, "poison_luck": 0, "poison_money": 0, "tiers": Counter()}
        for _ in range(n):
            if item.key == "mbox":
                await self._open_box(uid, summary)
            elif item.key == "mcase":
                self._open_case(item.price, summary)
            else:
                self._open_chest(summary)

        lines = []
        if summary["cash"]:
            await db.add_balance(uid, summary["cash"])
            lines.append(f"💵 **+{fmt(summary['cash'])}**")
        for tier, cnt in summary["tiers"].items():
            lines.append(f"{tier} × {cnt}")
        for key, cnt in summary["items"].items():
            await db.add_item(uid, key, cnt)
            it = get_item(key)
            lines.append(f"{it.emoji} **{it.name}** × {cnt}")
        if summary["revive"]:
            await db.add_item(uid, "revive", summary["revive"])
            lines.append(f"💖 **REVIVE ACTIVE** × {summary['revive']} — ховор олдвор!")
        if summary["poison_luck"]:
            await db.set_column(uid, "poison_until", time.time() + POISON_SECONDS)
            lines.append(f"☠️ **Азын хор** × {summary['poison_luck']} — 1 цаг алт олох магадлал буурна")
        if summary["poison_money"]:
            total = 0
            for _ in range(summary["poison_money"]):
                total += await db.lose_percent(uid, POISON_MONEY_RATE)
            lines.append(f"☠️ **Мөнгөний хор** × {summary['poison_money']} — хэтэвчнээс **{fmt(total)}** (10%) гарлаа")
        if not lines:
            lines.append("🕸️ Хоосон...")

        embed = discord.Embed(
            title=f"{item.emoji} {item.name} × {n} нээлээ",
            description="\n".join(lines),
            color=0xF59E0B,
        )
        if item.key == "mcase":
            net = summary["cash"] - item.price * n
            embed.set_footer(text=f"Үр дүн: {'+' if net >= 0 else ''}{net:,}₮")
        await reply(ctx, embed=embed)

    # ------------------------------------------------------------ mine
    @commands.command(name="mine", aliases=["dig", "alt"])
    async def mine(self, ctx: commands.Context):
        """Алтны уурхайд алт хайх (40% олох магадлал)"""
        db = self.bot.db
        user = await db.get_user(ctx.author.id)
        if await jailed(ctx, user):
            return
        now = time.time()
        if not await db.start_cooldown(ctx.author.id, "last_mine", now, MINE_COOLDOWN):
            left = user["last_mine"] + MINE_COOLDOWN - now
            await reply(ctx, f"⏳ Хүрз ядарлаа. **{fmt_duration(left)}**-ийн дараа дахин ухна.")
            return
        poisoned = user["poison_until"] > now
        chance = MINE_CHANCE / 2 if poisoned else MINE_CHANCE
        if random.random() < chance:
            qty = 2 if random.random() < 0.05 else 1
            await db.add_item(ctx.author.id, "gold", qty)
            gold = get_item("gold")
            embed = discord.Embed(
                title="⛏️ Алт олдлоо!",
                description=f"{gold.emoji} **{gold.name}** × {qty}\n💰 Зарвал: {fmt(gold.sell_price * qty)}",
                color=0xFACC15,
            )
        else:
            embed = discord.Embed(title="⛏️ Уурхай", description=random.choice(MINE_FAILS), color=0x6B7280)
        footer = f"Олох магадлал {int(chance * 100)}%" + (" · ☠️ азын хор үйлчилж байна" if poisoned else "")
        embed.set_footer(text=footer)
        await reply(ctx, embed=embed)

    # ------------------------------------------------------------ paid gym
    @commands.command(name="coach", aliases=["train", "pt"])
    async def coach(self, ctx: commands.Context):
        """Хувийн дасгалжуулагч: мөнгө төлж хүчээ илүү хурдан нэмэх"""
        db = self.bot.db
        user = await db.get_user(ctx.author.id)
        if await jailed(ctx, user):
            return
        if user["strength"] >= MAX_STRENGTH:
            await reply(ctx, f"💪 Таны хүч дээд түвшиндээ ({MAX_STRENGTH}) хүрсэн.")
            return
        now = time.time()
        left = user["last_train"] + TRAIN_COOLDOWN - now
        if left > 0:
            await reply(ctx, f"⏳ Дасгалжуулагч амарч байна. **{fmt_duration(left)}**-ийн дараа ирээрэй.")
            return
        if not await db.spend(ctx.author.id, TRAIN_PRICE):
            await reply(ctx, f"❌ Хувийн дасгалжуулагч **{fmt(TRAIN_PRICE)}** авдаг. Мөнгө хүрэлцэхгүй.")
            return
        await db.set_cooldown(ctx.author.id, "last_train", now)
        await db.add_strength(ctx.author.id, TRAIN_GAIN, MAX_STRENGTH)
        s = min(MAX_STRENGTH, user["strength"] + TRAIN_GAIN)
        embed = discord.Embed(
            title="🏋️ Хувийн дасгалжуулагч",
            description=f"💸 {fmt(TRAIN_PRICE)} төлөөд хүчтэй дасгал хийлээ!\n💪 Хүч **+{TRAIN_GAIN}** → **{s}/{MAX_STRENGTH}**",
            color=0xF97316,
        )
        embed.set_footer(text="Хүч нэмэгдэх тусам ажлын орлого өснө")
        await reply(ctx, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Loot(bot))
