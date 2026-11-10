import math
from collections import defaultdict

import discord
from discord.ext import commands

from actions import activate_shield, eat_food, open_box, revive_player, use_potion, wear_item
from items import (
    CATEGORIES,
    CATEGORY_BY_KEY,
    PETS,
    find_items,
    get_item,
    get_pet,
    stars,
)
from ui import OwnerView, nav_button
from usage import send_usage
from utils import fmt, hint_shop, hint_use, parse_qty, reply, shop_day

PER_PAGE = {"home": 10, "digital": 8, "clothes": 6, "house": 5}
DEFAULT_PER_PAGE = 5

CATEGORY_ALIASES = {
    "food": ["food", "хоол", "хүнс", "hunus"],
    "digital": ["digital", "dijital", "дижитал", "utas", "phone", "tech"],
    "home": ["home", "furniture", "гэр", "ахуй", "тавилга", "ger"],
    "house": ["house", "car", "cars", "байшин", "машин", "mashin"],
    "clothes": ["clothes", "cloth", "brand", "хувцас", "брэнд", "huvtsas"],
    "box": ["box", "case", "chest", "хайрцаг", "кейс"],
    "jewel": ["jewel", "jewelry", "үнэт", "эдлэл", "gem"],
    "metal": ["metal", "металл", "ore"],
    "tool": ["tool", "tools", "хэрэгсэл", "shield"],
}


def find_category(query: str) -> str | None:
    q = query.strip().casefold()
    for key, aliases in CATEGORY_ALIASES.items():
        if q == key or q in aliases:
            return key
    for key, _, name, _ in CATEGORIES:
        if name.casefold().startswith(q):
            return key
    return None


async def resolve_item(ctx, query: str, pool=None):
    """ID эсвэл нэрээр бараа олно. Олдохгүй/олон байвал мэдэгдээд None."""
    matches = find_items(query, pool)
    if not matches:
        await reply(ctx, f"❌ `{query}` гэсэн бараа олдсонгүй. `{ctx.clean_prefix}shop` дээрх ID-г ашиглана уу.")
        return None
    if len(matches) > 1:
        names = ", ".join(f"`{m.key}`" for m in matches[:8])
        await reply(ctx, f"🔎 Олон бараа таарч байна: {names}. Яг ID-г бичнэ үү.")
        return None
    return matches[0]


class ShopView(OwnerView):
    def __init__(self, cog, ctx, category: str | None = None):
        super().__init__(ctx.author.id, timeout=180)
        self.cog, self.ctx = cog, ctx
        self.category = category
        self.page = 0
        self.pages = 1
        self.select = discord.ui.Select(
            placeholder="Ангилал сонгоно уу...",
            options=[
                discord.SelectOption(label=name, value=key, emoji=emoji, description=f"{len(items)} бараа")
                for key, emoji, name, items in CATEGORIES
            ],
        )
        self.select.callback = self.on_select
        self.add_item(self.select)
        self.prev_btn = nav_button("◀", self.on_prev)
        self.page_btn = nav_button("1/1", self.on_noop, disabled=True)
        self.next_btn = nav_button("▶", self.on_next)
        self.back_btn = nav_button("Буцах", self.on_back, discord.ButtonStyle.primary)
        for b in (self.prev_btn, self.page_btn, self.next_btn, self.back_btn):
            self.add_item(b)

    def _sync(self):
        menu = self.category is None
        self.prev_btn.disabled = menu or self.page <= 0
        self.next_btn.disabled = menu or self.page >= self.pages - 1
        self.back_btn.disabled = menu
        self.page_btn.label = "—" if menu else f"{self.page + 1}/{self.pages}"

    async def build(self) -> discord.Embed:
        p = self.ctx.clean_prefix
        if self.category is None:
            embed = discord.Embed(
                title="🛍️ Дэлгүүр",
                description=f"Доорх цэснээс ангилал сонгоно уу. `{p}buy <ID>` командаар авна.",
                color=0xFFC933,
            )
            for key, emoji, name, items in CATEGORIES:
                embed.add_field(name=f"{emoji} {name}", value=f"{len(items)} бараа", inline=True)
            embed.set_footer(text=hint_shop(p))
            self.pages = 1
            self._sync()
            return embed

        _, emoji, name, items = CATEGORY_BY_KEY[self.category]
        per = PER_PAGE.get(self.category, DEFAULT_PER_PAGE)
        self.pages = max(1, math.ceil(len(items) / per))
        self.page = max(0, min(self.page, self.pages - 1))
        chunk = items[self.page * per : (self.page + 1) * per]
        sold = await self.cog.bot.db.shop_sold(shop_day())

        lines = []
        for it in chunk:
            stock_txt = ""
            if it.stock is not None:
                left = max(0, it.stock - sold.get(it.key, 0))
                stock_txt = " **[ДУУССАН]**" if left == 0 else f" (Нөөц: {left}/{it.stock})"
            if self.category == "home":
                lines.append(f"{it.emoji} **{it.name}** — {fmt(it.price)}{stock_txt} · `{it.key}`")
            else:
                if it.kind == "food":
                    desc = f"{stars(it.stars)} · {int(it.feeds_days)} хоногийн хоол"
                    if it.strength:
                        desc += f" · хүч +{it.strength}"
                else:
                    desc = it.desc
                lines.append(
                    f"{it.emoji} **{it.name}** - {fmt(it.price)}{stock_txt}\n"
                    f"> {desc}\n> ID: `{it.key}`"
                )
        sep = "\n" if self.category == "home" else "\n\n"
        embed = discord.Embed(
            title=f"🛍️{emoji} {name}",
            description=f"`{p}buy <ID>` командаар бараа авна уу.\n\n" + sep.join(lines),
            color=0xFFC933,
        )
        embed.set_footer(text=f"{hint_shop(p)} · Хуудас {self.page + 1}/{self.pages}")
        self._sync()
        return embed

    async def refresh(self, interaction):
        embed = await self.build()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_select(self, interaction):
        self.category = self.select.values[0]
        self.page = 0
        await self.refresh(interaction)

    async def on_prev(self, interaction):
        self.page -= 1
        await self.refresh(interaction)

    async def on_next(self, interaction):
        self.page += 1
        await self.refresh(interaction)

    async def on_back(self, interaction):
        self.category = None
        self.page = 0
        await self.refresh(interaction)

    async def on_noop(self, interaction):
        await interaction.response.defer()


class Shop(commands.Cog):
    """Дэлгүүр, цүнх, хоол, амьтны дэлгүүр."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    async def _inventory(self, user_id: int) -> dict[str, int]:
        rows = await self.bot.db.get_inventory(user_id)
        return {r["item_key"]: r["qty"] for r in rows}

    # ---------- дэлгүүр ----------
    @commands.command(name="shop")
    async def shop(self, ctx: commands.Context, category: str = None):
        """Дэлгүүр: shop [food | digital | home | house | clothes | jewel | metal | box | tool]"""
        cat = None
        if category is not None:
            cat = find_category(category)
            if cat is None:
                await send_usage(ctx)
                return
        view = ShopView(self, ctx, cat)
        embed = await view.build()
        view.message = await reply(ctx, embed=embed, view=view)

    @commands.command(name="buy", aliases=["purchase"])
    async def buy(self, ctx: commands.Context, item_id: str, qty: str = "1"):
        """Бараа худалдаж авах: buy <ID> [тоо]"""
        n = parse_qty(qty, 1, 100)
        if n is None:
            await reply(ctx, "❌ Тоо 1-ээс 100 хооронд байх ёстой.")
            return
        item = await resolve_item(ctx, item_id)
        if item is None:
            return

        db = self.bot.db
        if item.kind == "realty":
            house_cog = self.bot.get_cog("House")
            await house_cog._buy(ctx, item.key)
            return
        if item.kind == "car":
            if await db.item_qty(ctx.author.id, item.key) > 0:
                await reply(ctx, f"🚗 Танд аль хэдийн **{item.name}** байна.")
                return
            n = 1
        day = shop_day()
        reserved = False
        if item.stock is not None:
            sold = (await db.shop_sold(day)).get(item.key, 0)
            left = max(0, item.stock - sold)
            if left < n or not await db.buy_stock(item.key, day, n, item.stock):
                msg = "[ДУУССАН] Өнөөдрийн нөөц дууссан." if left == 0 else f"Нөөц хүрэлцэхгүй, үлдсэн: {left}."
                await reply(ctx, f"❌ {item.name}: {msg} Нөөц шөнө дундад шинэчлэгдэнэ.")
                return
            reserved = True

        total = item.price * n
        if not await db.spend(ctx.author.id, total):
            if reserved:
                await db.release_stock(item.key, day, n)
            await reply(ctx, f"❌ Мөнгө хүрэлцэхгүй байна. Нийт **{fmt(total)}** шаардлагатай.")
            return
        await db.add_item(ctx.author.id, item.key, n)

        embed = discord.Embed(title="🛒 Худалдан авалт амжилттай", color=0x22C55E)
        embed.add_field(name="Бараа", value=f"{item.emoji} **{item.name}** × {n}", inline=True)
        embed.add_field(name="💸 Төлсөн", value=fmt(total), inline=True)
        if item.stock is not None:
            sold = (await db.shop_sold(day)).get(item.key, 0)
            embed.add_field(name="Нөөц", value=f"{max(0, item.stock - sold)}/{item.stock}", inline=True)
        embed.set_footer(text=hint_use(ctx.clean_prefix))
        await reply(ctx, embed=embed)

    # ---------- цүнх ----------
    @commands.command(name="inv", aliases=["inventory", "bag"])
    async def inventory(self, ctx: commands.Context, action: str = None, item_id: str = None, qty: str = None):
        """Цүнх: inv | inv use <ID> [тоо]"""
        p = ctx.clean_prefix
        inv = await self._inventory(ctx.author.id)

        if action is not None and action.lower() in ("use", "ашиглах"):
            if item_id is None:
                await send_usage(ctx)
                return
            n = parse_qty(qty, 1, 100)
            if n is None:
                await reply(ctx, "❌ Тоо 1-ээс 100 хооронд байх ёстой.")
                return
            pool = [it for it in (get_item(k) for k in inv) if it]
            item = await resolve_item(ctx, item_id, pool)
            if item is None:
                return
            if item.kind == "food":
                await eat_food(self.bot, ctx, item, n)
            elif item.key == "shield":
                await activate_shield(self.bot, ctx)
            elif item.key in ("luck_potion", "money_potion"):
                await use_potion(self.bot, ctx, item)
            elif item.key == "revive":
                await revive_player(self.bot, ctx, ctx.author)
            elif item.kind == "box":
                await open_box(self.bot, ctx, item, n)
            elif item.kind == "clothes":
                await wear_item(self.bot, ctx, item)
            else:
                await reply(
                    ctx,
                    f"ℹ️ **{item.name}**-г шууд ашиглах боломжгүй. "
                    f"Байшинд байрлуулах: `{p}house bedroom use {item.key}` · зарах: `{p}sell {item.key}`",
                )
            return
        if action is not None:
            await send_usage(ctx)
            return

        if not inv:
            await reply(ctx, f"🎒 Таны цүнх хоосон байна. `{p}steal` эсвэл `{p}shop`-оор бараа олно.")
            return

        groups = defaultdict(list)
        total = 0
        for key, qty_ in inv.items():
            it = get_item(key)
            if not it:
                continue
            total += it.sell_price * qty_
            groups[it.kind].append(f"{it.emoji} **{it.name}** × {qty_} — `{it.key}`")

        titles = {"food": "🍞 Хүнс", "house": "🏠 Гэр ахуй", "jewel": "💎 Үнэт эдлэл",
                  "metal": "⛏️ Металл", "tool": "🛡️ Хэрэгсэл", "digital": "📱 Дижитал",
                  "clothes": "👕 Хувцас", "car": "🚗 Машин", "box": "🎁 Хайрцаг"}
        embed = discord.Embed(
            title="🎒 Таны цүнх",
            description=f"Зарвал нийт: **{fmt(total)}**",
            color=0x8B5CF6,
        )
        for kind in ("food", "tool", "box", "clothes", "car", "digital", "jewel", "metal", "house"):
            lines = groups.get(kind)
            if not lines:
                continue
            for i in range(0, len(lines), 12):
                embed.add_field(
                    name=titles[kind] if i == 0 else "​",
                    value="\n".join(lines[i : i + 12]),
                    inline=False,
                )
        embed.set_footer(text=hint_use(p))
        await reply(ctx, embed=embed)

    @commands.command(name="sell")
    async def sell(self, ctx: commands.Context, item_id: str, qty: str = None):
        """Цүнхний барааг зарах: sell <ID | all> [тоо]"""
        inv = await self._inventory(ctx.author.id)

        if item_id.lower() in ("all", "бүгд"):
            earned = 0
            count = 0
            for key, have in inv.items():
                it = get_item(key)
                if it and it.kind in ("house", "digital", "jewel", "metal") and await self.bot.db.remove_item(
                    ctx.author.id, key, have
                ):
                    earned += it.sell_price * have
                    count += have
            if earned == 0:
                await reply(ctx, "❌ Зарах гэр ахуй, дижитал, үнэт эдлэл, металл алга.")
                return
            await self.bot.db.add_balance(ctx.author.id, earned)
            await reply(ctx, f"💰 Нийт **{count}** бараа зарж **{fmt(earned)}** авлаа.")
            return

        pool = [it for it in (get_item(k) for k in inv) if it]
        item = await resolve_item(ctx, item_id, pool)
        if item is None:
            return
        have = inv[item.key]
        n = have if qty is not None and qty.lower() in ("all", "бүгд") else parse_qty(qty, 1, 100000)
        if n is None or n > have:
            await reply(ctx, f"❌ Тоо буруу. Танд {have} ширхэг байна.")
            return
        if not await self.bot.db.remove_item(ctx.author.id, item.key, n):
            await reply(ctx, "❌ Танд хангалттай бараа алга.")
            return
        earned = item.sell_price * n
        await self.bot.db.add_balance(ctx.author.id, earned)
        await reply(ctx, f"💰 **{item.name} × {n}** зарж **{fmt(earned)}** авлаа.")

    @commands.command(name="gift")
    async def gift(self, ctx: commands.Context, item_id: str, member: discord.Member, qty: str = "1"):
        """Бусдад бэлэглэх: gift <ID> @хүн [тоо]"""
        if member.id == ctx.author.id or member.bot:
            await reply(ctx, "❌ Энэ хүнд бэлэглэх боломжгүй.")
            return
        n = parse_qty(qty, 1, 100000)
        if n is None:
            await reply(ctx, "❌ Тоо буруу байна.")
            return
        inv = await self._inventory(ctx.author.id)
        pool = [it for it in (get_item(k) for k in inv) if it]
        item = await resolve_item(ctx, item_id, pool)
        if item is None:
            return
        if not await self.bot.db.remove_item(ctx.author.id, item.key, n):
            await reply(ctx, "❌ Танд хангалттай бараа алга.")
            return
        await self.bot.db.add_item(member.id, item.key, n)
        await reply(
            ctx,
            f"🎁 {ctx.author.mention} → {member.mention}: **{item.name} × {n}** бэлэглэлээ.",
        )

    # ---------- хоол ----------
    @commands.command(name="eat")
    async def eat(self, ctx: commands.Context, item_id: str, qty: str = "1"):
        """Хоол идэх: eat <ID> [тоо]"""
        n = parse_qty(qty, 1, 100)
        if n is None:
            await reply(ctx, "❌ Тоо 1-ээс 100 хооронд байх ёстой.")
            return
        inv = await self._inventory(ctx.author.id)
        pool = [it for it in (get_item(k) for k in inv) if it and it.kind == "food"]
        if not pool:
            await reply(ctx, f"❌ Танд хоол алга. `{ctx.clean_prefix}shop food` дээрээс аваарай.")
            return
        item = await resolve_item(ctx, item_id, pool)
        if item is None:
            return
        await eat_food(self.bot, ctx, item, n)

    # ---------- амьтны дэлгүүр ----------
    @commands.command(name="petshop", aliases=["pets"])
    async def pet_shop(self, ctx: commands.Context):
        """Тэжээвэр амьтны дэлгүүр"""
        embed = discord.Embed(
            title="🐾 Амьтны дэлгүүр",
            description=f"Нэг л амьтантай байж болно. `{ctx.clean_prefix}buypet dog` гэж авна.",
            color=0xF97316,
        )
        for pet in PETS:
            embed.add_field(
                name=f"{pet.emoji} {pet.name} (`{pet.key}`) — {fmt(pet.price)}",
                value=pet.perk,
                inline=False,
            )
        await reply(ctx, embed=embed)

    @commands.command(name="buypet")
    async def buy_pet(self, ctx: commands.Context, pet_name: str):
        """Амьтан худалдаж авах: buypet <dog | cat | falcon>"""
        q = pet_name.lower()
        pet = get_pet(q) or next((p for p in PETS if p.name.lower().startswith(q)), None)
        if pet is None:
            await reply(ctx, f"❌ Ийм амьтан алга. `{ctx.clean_prefix}petshop` командаар харна уу.")
            return
        user = await self.bot.db.get_user(ctx.author.id)
        if user["pet"]:
            current = get_pet(user["pet"])
            await reply(ctx, f"❌ Танд аль хэдийн {current.emoji} **{current.name}** байна.")
            return
        if not await self.bot.db.spend(ctx.author.id, pet.price):
            await reply(ctx, f"❌ Мөнгө хүрэлцэхгүй байна. **{fmt(pet.price)}** хэрэгтэй.")
            return
        await self.bot.db.set_pet(ctx.author.id, pet.key)
        await reply(ctx, f"{pet.emoji} **{pet.name}** авлаа! Онцлог: {pet.perk}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
