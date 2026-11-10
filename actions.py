import random
import time

import discord

from items import JEWELS, METALS, SLOT_NAMES, ITEMS, LOOT_POOL, get_item, random_loot, stars
from utils import (
    HUNGER_SECONDS,
    MAX_STRENGTH,
    POTION_SECONDS,
    PROTECT_SECONDS,
    fmt,
    fmt_duration,
    fmt_short,
    hint_use,
    hunger_left,
    luck_bonus,
    reply,
)


async def eat_food(bot, ctx, item, qty: int) -> bool:
    """Цүнхнээс хоол идэж цатгана. Цатгах хугацаа нэмэгдэж, дээд тал нь 7 хоног."""
    db = bot.db
    uid = ctx.author.id
    user = await db.get_user(uid)
    now = time.time()
    have = await db.item_qty(uid, item.key)
    if have <= 0:
        await reply(ctx, f"❌ Танд **{item.name}** алга. `{ctx.clean_prefix}buy {item.key}` гэж авна уу.")
        return False

    remaining = max(0.0, hunger_left(user["last_fed"], now))
    eaten = 0
    for _ in range(min(qty, have)):
        if remaining >= HUNGER_SECONDS - 60:
            break
        remaining = min(float(HUNGER_SECONDS), remaining + item.feeds_days * 86400)
        eaten += 1
    if eaten == 0:
        await reply(ctx, "😌 Та аль хэдийн бүрэн цатгалантай байна.")
        return False
    if not await db.remove_item(uid, item.key, eaten):
        await reply(ctx, "❌ Танд хангалттай хоол алга.")
        return False

    await db.set_last_fed(uid, now - (HUNGER_SECONDS - remaining))
    gained = item.strength * eaten
    if gained:
        await db.add_strength(uid, gained, MAX_STRENGTH)

    embed = discord.Embed(title="😋 Идлээ", color=0xF59E0B)
    embed.add_field(
        name="🍽️ Хоол", value=f"{item.emoji} **{item.name}** × {eaten}\n{stars(item.stars)}", inline=True
    )
    embed.add_field(name="🍞 Цатгах хугацаа", value=fmt_duration(remaining), inline=True)
    if gained:
        embed.add_field(name="💪 Хүч", value=f"+{gained}", inline=True)
    embed.set_footer(text=hint_use(ctx.clean_prefix))
    await reply(ctx, embed=embed)
    return True


async def activate_shield(bot, ctx) -> bool:
    """Хамгаалалтын бамбай ашиглаж 2.5 цаг дээрэм, хакераас хамгаална."""
    db = bot.db
    uid = ctx.author.id
    user = await db.get_user(uid)
    now = time.time()
    if user["protect_until"] > now:
        await reply(
            ctx,
            f"🛡️ Таны хамгаалалт идэвхтэй байна. **{fmt_short(user['protect_until'] - now)}** үлдсэн.",
        )
        return False
    if not await db.remove_item(uid, "shield", 1):
        await reply(
            ctx,
            f"❌ Танд хамгаалалтын бамбай алга. `{ctx.clean_prefix}buy shield` гэж авна уу.",
        )
        return False
    await db.set_protect(uid, now + PROTECT_SECONDS)
    embed = discord.Embed(
        title="🛡️ Хамгаалалт идэвхжлээ!",
        description="Та 2.5 цагийн турш дээрэм, хакердалтаас хамгаалагдлаа.\nАмжилт хүсье!",
        color=0x22C55E,
    )
    await reply(ctx, embed=embed)
    return True


# ================= potion =================
async def use_potion(bot, ctx, item) -> bool:
    db = bot.db
    uid = ctx.author.id
    column = "luck_until" if item.key == "luck_potion" else "boost_until"
    user = await db.get_user(uid)
    now = time.time()
    if not await db.remove_item(uid, item.key, 1):
        await reply(ctx, f"❌ Танд **{item.name}** алга.")
        return False
    until = max(now, user[column]) + POTION_SECONDS
    await db.set_potion(uid, column, until)
    what = "азын магадлал +10%" if column == "luck_until" else "ажил, өдрийн цалин +10%"
    embed = discord.Embed(
        title=f"{item.emoji} {item.name} уулаа",
        description=f"**{what}**\nҮлдсэн хугацаа: **{fmt_duration(until - now)}**",
        color=0x22C55E,
    )
    await reply(ctx, embed=embed)
    return True


# ================= амилуулах =================
async def revive_player(bot, ctx, target) -> bool:
    """Өөрийн Revive Active-ээр target-ийг (Member) амилуулна."""
    db = bot.db
    victim = await db.get_user(target.id)
    if not victim["dead"]:
        await reply(ctx, "😇 Энэ хүн амьд байна, амилуулах шаардлагагүй.")
        return False
    if not await db.remove_item(ctx.author.id, "revive", 1):
        await reply(ctx, "❌ Танд **Revive Active** алга. Хайрцгаас 2%, тоглоомоор 0.1% олдоно, эсвэл админаас хүснэ.")
        return False
    await db.set_dead(target.id, False, time.time())
    embed = discord.Embed(
        title="💖 Амилууллаа!",
        description=f"{target.mention} дахин амьдарлаа. Хоолоо идэхээ мартуузай! 🍞",
        color=0xEC4899,
    )
    await reply(ctx, embed=embed)
    return True


async def maybe_revive_drop(bot, ctx, chance: float = 0.001) -> bool:
    """Тоглоомын явцад 0.1% магадлалтай Revive Active олдоно."""
    if random.random() >= chance:
        return False
    await bot.db.add_item(ctx.author.id, "revive", 1)
    embed = discord.Embed(
        title="💖 Ховор олдвор!",
        description=f"{ctx.author.mention} **Revive Active** олж авлаа! (магадлал 0.1%)\n`{ctx.clean_prefix}inv use revive`",
        color=0xEC4899,
    )
    try:
        await ctx.send(embed=embed)
    except Exception:
        pass
    return True


# ================= хувцас =================
async def wear_item(bot, ctx, item) -> bool:
    if item.kind != "clothes":
        await reply(ctx, f"❌ **{item.name}**-г өмсөх боломжгүй.")
        return False
    if await bot.db.item_qty(ctx.author.id, item.key) <= 0:
        await reply(ctx, f"❌ Танд **{item.name}** алга.")
        return False
    await bot.db.equip(ctx.author.id, item.slot, item.key)
    await reply(
        ctx,
        f"{item.emoji} **{item.name}**-г өмслөө ({SLOT_NAMES[item.slot]}). `{ctx.clean_prefix}profile` дээр хар!",
    )
    return True


# ================= хайрцаг, кейс =================
EMPTY_JOKES = [
    "Хоосон байна... Дотор нь зөвхөн агаар л байлаа 🌬️",
    "Дотор нь хуучин оймс л байна 🧦 (бохир)",
    "«Дараагийн удаа аз таарна» гэсэн цаас л гарлаа 📝",
    "Хулгайч урьдаас аваад явчихжээ 🥷",
    "Хайрцаг нээтэл дотроос чинь хэн нэг «Сайн уу?» гэв... Хоосон шүү 👻",
    "Энэ удаа азгүй. Аз чинь кофе уухаар явсан бололтой ☕",
    "Дотор нь ганц гуравдахь жилийн ногоон сонгино л байлаа 🧅",
    "Хоосон. Харин хайрцгийн үнэртэй нь гайгүй шүү 📦",
]

CASE_TABLE = [  # (үржвэр, жин)
    (0.0, 25), (0.4, 30), (0.9, 25), (1.8, 14), (4.0, 5), (10.0, 1),
]


def roll_case(luck: int) -> float:
    mults = [m for m, _ in CASE_TABLE]
    weights = [w for _, w in CASE_TABLE]
    result = random.choices(mults, weights=weights)[0]
    if luck and random.random() < luck / 100:  # аз: дахин эргүүлж, дээр нь авна
        result = max(result, random.choices(mults, weights=weights)[0])
    return result


async def open_box(bot, ctx, item, qty: int) -> bool:
    db = bot.db
    uid = ctx.author.id
    if not await db.remove_item(uid, item.key, qty):
        await reply(ctx, f"❌ Танд {qty} ширхэг **{item.name}** алга.")
        return False
    user = await db.get_user(uid)
    luck = luck_bonus(user)
    lines: list[str] = []
    money = 0
    got: dict[str, int] = {}
    revive = 0

    for _ in range(qty):
        if item.key == "box":
            if random.random() < 0.02:
                got["revive"] = got.get("revive", 0) + 1
                revive += 1
            elif random.random() < 0.15 - luck / 1000:
                lines.append(random.choice(EMPTY_JOKES))
            else:
                for it in random_loot(random.randint(1, 3), 0.05 + luck / 500):
                    got[it.key] = got.get(it.key, 0) + 1
        elif item.key == "case":
            mult = roll_case(luck)
            prize = int(item.price * mult)
            if prize == 0:
                lines.append(random.choice(EMPTY_JOKES))
            money += prize
        else:  # chest
            if random.random() < 0.15 - luck / 1000:
                lines.append(random.choice(EMPTY_JOKES))
            else:
                rare = JEWELS + METALS
                weights = [1 / it.price for it in rare]
                for it in random.choices(rare, weights=weights, k=random.randint(1, 2)):
                    got[it.key] = got.get(it.key, 0) + 1

    for key, n in got.items():
        await db.add_item(uid, key, n)
    if money:
        await db.add_balance(uid, money)

    embed = discord.Embed(title=f"{item.emoji} {item.name} × {qty} нээлээ", color=0xF59E0B)
    if got:
        embed.add_field(
            name="🎁 Олсон бараа",
            value="\n".join(
                f"{ITEMS[k].emoji} **{ITEMS[k].name}** × {n}" + (" 💖" if k == "revive" else "")
                for k, n in got.items()
            ),
            inline=False,
        )
    if item.key == "case":
        net = money - item.price * qty
        sign = "+" if net >= 0 else "-"
        embed.add_field(name="💵 Хожсон", value=fmt(money), inline=True)
        embed.add_field(name="📊 Ашиг/алдагдал", value=f"```diff\n{sign}{abs(net):,} ₮\n```", inline=True)
    if lines:
        embed.add_field(name="😅", value="\n".join(lines[:5]), inline=False)
    if not got and not money and not lines:
        embed.description = random.choice(EMPTY_JOKES)
    if revive:
        embed.set_footer(text="💖 Revive Active олдлоо! Ховор азтай юм аа!")
    await reply(ctx, embed=embed)
    return True
