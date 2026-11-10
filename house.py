import discord
from discord.ext import commands

from houses import (
    HOUSE_SELL_RATE,
    HOUSES,
    MAX_SAFE_LEVEL,
    ROOM_BY_KEY,
    comfort_pct,
    find_house,
    find_room,
    get_house,
    house_rooms,
    safe_money_cap,
    safe_next_price,
    safe_slot_cap,
)
from items import ITEMS, find_items, get_item
from usage import send_usage
from utils import fmt, parse_amount, parse_qty, reply


async def resolve_in(ctx, query: str, pool):
    matches = find_items(query, pool)
    if not matches:
        await reply(ctx, f"❌ `{query}` гэсэн бараа олдсонгүй.")
        return None
    if len(matches) > 1:
        names = ", ".join(f"`{m.key}`" for m in matches[:8])
        await reply(ctx, f"🔎 Олон бараа таарч байна: {names}. Яг ID-г бичнэ үү.")
        return None
    return matches[0]


class HouseCog(commands.Cog, name="House"):
    """Байшин, өрөө, эд зүйл байрлуулах, сейф."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    # ---------- байшин ----------
    async def _overview(self, ctx):
        p = ctx.clean_prefix
        user = await self.bot.db.get_user(ctx.author.id)
        house = get_house(user["house"])
        if house is None:
            await reply(
                ctx,
                f"🏠 Танд байшин алга. `{p}house shop` гэж үзээд `{p}house buy <ID>` гэж авна уу "
                f"(хамгийн хямд нь {fmt(HOUSES[0].price)}).",
            )
            return
        rows = await self.bot.db.get_house_items(ctx.author.id)
        per_room: dict[str, int] = {}
        total_value = 0
        for r in rows:
            per_room[r["room"]] = per_room.get(r["room"], 0) + r["qty"]
            it = ITEMS.get(r["item_key"])
            if it:
                total_value += it.price * r["qty"]

        embed = discord.Embed(title=f"{house.emoji} {house.name}", color=0x8B5CF6)
        lines = []
        for key, emoji, name in house_rooms(house):
            lines.append(f"{emoji} **{name}** (`{key}`) — {per_room.get(key, 0)}/{house.slots}")
        embed.add_field(name="🚪 Өрөөнүүд", value="\n".join(lines), inline=False)
        embed.add_field(name="💎 Эд зүйлсийн үнэ", value=fmt(total_value), inline=True)
        embed.add_field(name="🏠 Ажлын нэмэгдэл", value=f"+{comfort_pct(total_value)}%", inline=True)
        safe = f"Түвшин {user['safe_level']}" if user["safe_level"] else "Байхгүй"
        embed.add_field(name="🔐 Сейф", value=safe, inline=True)
        embed.set_footer(text=f"{p}house bedroom | {p}house bedroom use <ID> | {p}safe")
        await reply(ctx, embed=embed)

    async def _shop(self, ctx):
        p = ctx.clean_prefix
        user = await self.bot.db.get_user(ctx.author.id)
        current = get_house(user["house"])
        lines = []
        for h in HOUSES:
            mark = " ✅" if current and current.key == h.key else ""
            lines.append(
                f"{h.emoji} **{h.name}**{mark} — {fmt(h.price)}\n"
                f"> {h.rooms} өрөө · өрөө бүрт {h.slots} эд зүйл · ID: `{h.key}`"
            )
        embed = discord.Embed(
            title="🏘️ Байшингийн зар",
            description="\n\n".join(lines),
            color=0x8B5CF6,
        )
        embed.set_footer(
            text=f"Авах: {p}house buy <ID> · Сайжруулахад хуучин байшингийн {int(HOUSE_SELL_RATE * 100)}% буцаан тооцогдоно"
        )
        await reply(ctx, embed=embed)

    async def _buy(self, ctx, query: str):
        target = find_house(query)
        if target is None:
            await reply(ctx, f"❌ Байшин олдсонгүй. `{ctx.clean_prefix}house shop` гэж харна уу.")
            return
        user = await self.bot.db.get_user(ctx.author.id)
        current = get_house(user["house"])
        refund = 0
        if current:
            if target.price <= current.price:
                await reply(ctx, f"❌ Танд аль хэдийн **{current.name}** байна. Илүү үнэтэй байшинг сонгоно уу.")
                return
            refund = int(current.price * HOUSE_SELL_RATE)
        cost = target.price - refund
        if not await self.bot.db.buy_house(ctx.author.id, target.key, cost):
            await reply(ctx, f"❌ Мөнгө хүрэлцэхгүй байна. **{fmt(cost)}** хэрэгтэй (хэтэвчинд).")
            return
        embed = discord.Embed(
            title="🏠 Шинэ байшинтай боллоо!",
            description=f"{target.emoji} **{target.name}**",
            color=0x22C55E,
        )
        embed.add_field(name="💸 Төлсөн", value=fmt(cost), inline=True)
        if refund:
            embed.add_field(name="↩️ Хуучин байшингийн буцаалт", value=fmt(refund), inline=True)
        embed.add_field(name="🚪 Өрөө", value=f"{target.rooms} өрөө · {target.slots} эд зүйл/өрөө", inline=False)
        embed.set_footer(text=f"{ctx.clean_prefix}house bedroom use <ID> гэж эд зүйлээ байрлуулаарай")
        await reply(ctx, embed=embed)

    async def _room(self, ctx, room_key: str, args: list[str]):
        p = ctx.clean_prefix
        user = await self.bot.db.get_user(ctx.author.id)
        house = get_house(user["house"])
        if house is None:
            await reply(ctx, f"🏠 Танд байшин алга. `{p}house shop`-оор үзнэ үү.")
            return
        rooms = {r[0] for r in house_rooms(house)}
        if room_key not in rooms:
            await reply(
                ctx,
                f"❌ **{house.name}**-д {ROOM_BY_KEY[room_key][2]} байхгүй. Илүү том байшин авбал нэмэгдэнэ.",
            )
            return
        _, emoji, name = ROOM_BY_KEY[room_key]

        if args:
            action = args[0].lower()
            if action not in ("use", "unuse", "place", "remove", "байрлуулах", "авах"):
                await send_usage(ctx)
                return
            if len(args) < 2:
                await send_usage(ctx)
                return
            use = action in ("use", "place", "байрлуулах")
            qty = parse_qty(args[2] if len(args) > 2 else None, 1, 100)
            if qty is None:
                await reply(ctx, "❌ Тоо буруу байна.")
                return
            if use:
                inv = {r["item_key"] for r in await self.bot.db.get_inventory(ctx.author.id)}
                pool = [it for it in (get_item(k) for k in inv) if it]
                item = await resolve_in(ctx, args[1], pool)
                if item is None:
                    return
                if not item.placeable:
                    await reply(ctx, f"❌ **{item.name}**-г байшинд байрлуулах боломжгүй (зөвхөн тавилга, цахилгаан бараа).")
                    return
                res = await self.bot.db.place_item(ctx.author.id, room_key, item.key, qty, house.slots)
                if res == "no_item":
                    await reply(ctx, f"❌ Цүнхэнд {qty} ширхэг **{item.name}** алга.")
                    return
                if res == "full":
                    await reply(ctx, f"❌ {name} дүүрсэн байна (дээд тал нь {house.slots} эд зүйл).")
                    return
                await reply(ctx, f"{emoji} **{item.name} × {qty}**-г {name}-д байрлууллаа.")
            else:
                rows = await self.bot.db.get_house_items(ctx.author.id, room_key)
                pool = [ITEMS[r["item_key"]] for r in rows if r["item_key"] in ITEMS]
                item = await resolve_in(ctx, args[1], pool)
                if item is None:
                    return
                if not await self.bot.db.unplace_item(ctx.author.id, room_key, item.key, qty):
                    await reply(ctx, f"❌ {name}-д {qty} ширхэг **{item.name}** алга.")
                    return
                await reply(ctx, f"🎒 **{item.name} × {qty}**-г {name}-с цүнхэнд буцаалаа.")
            return

        rows = await self.bot.db.get_house_items(ctx.author.id, room_key)
        used = sum(r["qty"] for r in rows)
        if rows:
            body = "\n".join(
                f"{ITEMS[r['item_key']].emoji} **{ITEMS[r['item_key']].name}** × {r['qty']} — `{r['item_key']}`"
                for r in rows
                if r["item_key"] in ITEMS
            )
        else:
            body = "*Хоосон байна.*"
        embed = discord.Embed(
            title=f"{emoji} {name} ({used}/{house.slots})",
            description=f"**Таны өрөөнд:**\n{body}",
            color=0x8B5CF6,
        )
        embed.set_footer(text=f"{p}house {room_key} use <ID> | {p}house {room_key} unuse <ID>")
        await reply(ctx, embed=embed)

    @commands.command(name="house", aliases=["home"])
    async def house(self, ctx: commands.Context, *args: str):
        """Байшин: house [shop | buy <ID> | <өрөө> [use|unuse <ID> [тоо]]]"""
        if not args:
            await self._overview(ctx)
            return
        first = args[0].lower()
        if first in ("shop", "list", "market"):
            await self._shop(ctx)
        elif first == "buy":
            if len(args) < 2:
                await send_usage(ctx)
                return
            await self._buy(ctx, args[1])
        else:
            room = find_room(first)
            if room is None:
                await reply(
                    ctx,
                    "❌ Өрөө олдсонгүй. Өрөөнүүд: `living`, `bedroom`, `kitchen`, `bathroom`, `office`.",
                )
                return
            await self._room(ctx, room, list(args[1:]))

    # ---------- сейф ----------
    async def _safe_overview(self, ctx):
        p = ctx.clean_prefix
        user = await self.bot.db.get_user(ctx.author.id)
        level = user["safe_level"]
        if level == 0:
            price = safe_next_price(0)
            await reply(
                ctx,
                f"🔐 Танд сейф алга. Байшинтай байх ёстой. `{p}safe buy` ({fmt(price)}) гэж авна.",
            )
            return
        items = await self.bot.db.get_safe_items(ctx.author.id)
        used = sum(r["qty"] for r in items)
        if items:
            body = "\n".join(
                f"{ITEMS[r['item_key']].emoji} **{ITEMS[r['item_key']].name}** × {r['qty']} — `{r['item_key']}`"
                for r in items
                if r["item_key"] in ITEMS
            )
        else:
            body = "*Эд зүйл алга.*"
        embed = discord.Embed(title=f"🔐 Таны сейф · түвшин {level}", color=0xF59E0B)
        embed.add_field(
            name="💰 Мөнгө",
            value=f"{fmt(user['safe_money'])} / {fmt(safe_money_cap(level))}",
            inline=False,
        )
        embed.add_field(name=f"🎒 Эд зүйл ({used}/{safe_slot_cap(level)})", value=body, inline=False)
        nxt = safe_next_price(level)
        extra = f" · Сайжруулах: {p}safe buy ({fmt(nxt)})" if nxt else " · Хамгийн дээд түвшин"
        embed.set_footer(text=f"{p}safe put|take <ID|money> <тоо>{extra}")
        embed.description = "Сейф доторх мөнгө, эд зүйлийг дээрэмдэх, хакердах боломжгүй."
        await reply(ctx, embed=embed)

    @commands.command(name="safe", aliases=["sef"])
    async def safe(self, ctx: commands.Context, *args: str):
        """Сейф: safe [buy | put <ID|money> <тоо> | take <ID|money> <тоо>]"""
        p = ctx.clean_prefix
        if not args:
            await self._safe_overview(ctx)
            return
        action = args[0].lower()
        user = await self.bot.db.get_user(ctx.author.id)

        if action in ("buy", "upgrade"):
            if get_house(user["house"]) is None:
                await reply(ctx, f"🏠 Сейф авахын тулд эхлээд байшинтай байх ёстой. `{p}house shop`")
                return
            level = user["safe_level"]
            price = safe_next_price(level)
            if price is None:
                await reply(ctx, f"🔐 Таны сейф хамгийн дээд түвшинд ({MAX_SAFE_LEVEL}) байна.")
                return
            if not await self.bot.db.buy_safe_level(ctx.author.id, level + 1, price):
                await reply(ctx, f"❌ Мөнгө хүрэлцэхгүй байна. **{fmt(price)}** хэрэгтэй (хэтэвчинд).")
                return
            await reply(
                ctx,
                f"🔐 Сейф түвшин **{level + 1}** боллоо! Мөнгө: {fmt(safe_money_cap(level + 1))} · "
                f"эд зүйл: {safe_slot_cap(level + 1)}.",
            )
            return

        if action not in ("put", "take", "оруулах", "авах"):
            await send_usage(ctx)
            return
        if len(args) < 2:
            await send_usage(ctx)
            return
        level = user["safe_level"]
        if level == 0:
            await reply(ctx, f"🔐 Танд сейф алга. `{p}safe buy` гэж авна уу.")
            return
        put = action in ("put", "оруулах")
        target = args[1].lower()

        if target in ("money", "мөнгө", "cash"):
            if put:
                amt = parse_amount(args[2] if len(args) > 2 else None, user["balance"])
                if amt is None or amt <= 0:
                    await send_usage(ctx)
                    return
                if not await self.bot.db.safe_put_money(ctx.author.id, amt, safe_money_cap(level)):
                    await reply(
                        ctx,
                        f"❌ Хэтэвчинд мөнгө хүрэхгүй эсвэл сейф дүүрнэ (дээд {fmt(safe_money_cap(level))}).",
                    )
                    return
                await reply(ctx, f"🔐 Сейфэнд **{fmt(amt)}** хийлээ.")
            else:
                amt = parse_amount(args[2] if len(args) > 2 else None, user["safe_money"])
                if amt is None or amt <= 0:
                    await send_usage(ctx)
                    return
                if not await self.bot.db.safe_take_money(ctx.author.id, amt):
                    await reply(ctx, "❌ Сейфэнд мөнгө хүрэлцэхгүй байна.")
                    return
                await reply(ctx, f"💵 Сейфнээс **{fmt(amt)}** авч хэтэвчиндээ хийлээ.")
            return

        qty = parse_qty(args[2] if len(args) > 2 else None, 1, 100000)
        if qty is None:
            await reply(ctx, "❌ Тоо буруу байна.")
            return
        if put:
            inv = {r["item_key"] for r in await self.bot.db.get_inventory(ctx.author.id)}
            pool = [it for it in (get_item(k) for k in inv) if it]
            item = await resolve_in(ctx, args[1], pool)
            if item is None:
                return
            res = await self.bot.db.safe_put_item(ctx.author.id, item.key, qty, safe_slot_cap(level))
            if res == "no_item":
                await reply(ctx, f"❌ Цүнхэнд {qty} ширхэг **{item.name}** алга.")
            elif res == "full":
                await reply(ctx, f"❌ Сейф дүүрсэн байна (дээд {safe_slot_cap(level)} эд зүйл).")
            else:
                await reply(ctx, f"🔐 **{item.name} × {qty}**-г сейфэнд хийлээ.")
        else:
            rows = await self.bot.db.get_safe_items(ctx.author.id)
            pool = [ITEMS[r["item_key"]] for r in rows if r["item_key"] in ITEMS]
            item = await resolve_in(ctx, args[1], pool)
            if item is None:
                return
            if not await self.bot.db.safe_take_item(ctx.author.id, item.key, qty):
                await reply(ctx, f"❌ Сейфэнд {qty} ширхэг **{item.name}** алга.")
            else:
                await reply(ctx, f"🎒 **{item.name} × {qty}**-г сейфнээс цүнхэнд авлаа.")


async def setup(bot: commands.Bot):
    await bot.add_cog(HouseCog(bot))
