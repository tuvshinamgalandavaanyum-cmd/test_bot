import time

import discord

from items import stars
from utils import (
    HUNGER_SECONDS,
    MAX_STRENGTH,
    PROTECT_SECONDS,
    fmt_duration,
    fmt_short,
    hint_use,
    hunger_left,
    reply,
)


async def eat_food(bot, ctx, item, qty: int) -> bool:
    """Цүнхнээс хоол идэж цатгана. Цатгах хугацаа нэмэгдэж, дээд тал нь 7 хоног."""
    db = bot.db
    uid = ctx.author.id
    user = await db.get_user(uid)
    now = time.time()
    if user["dead"]:
        await reply(ctx, "💀 Та үхсэн байна. Revive Active хэрэгтэй.")
        return False
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


async def use_revive(bot, ctx) -> bool:
    """Revive Active: үхсэн хүнийг амилуулна."""
    db = bot.db
    uid = ctx.author.id
    user = await db.get_user(uid)
    if not user["dead"]:
        await reply(ctx, "😌 Та амьд байна. Revive Active-ийг үхсэн үедээ хэрэглээрэй.")
        return False
    if not await db.remove_item(uid, "revive", 1):
        await reply(ctx, "❌ Танд Revive Active алга.")
        return False
    await db.set_dead(uid, False, time.time())
    embed = discord.Embed(
        title="💖 Revive Active!",
        description="Та дахин амьдарлаа! Одоо хоолоо мартваль дахин үхнэ шүү.",
        color=0x22C55E,
    )
    await reply(ctx, embed=embed)
    return True
