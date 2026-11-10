import asyncio
import io

import discord
from discord.ext import commands

from actions import wear_item
from houses import get_house
from items import ITEMS, SLOT_NAMES, find_items, get_pet
from ui import OwnerView, nav_button
from usage import send_usage
from utils import MAX_STRENGTH, fmt, reply

GENDERS = {"male": ("👨", "Эрэгтэй"), "female": ("👩", "Эмэгтэй")}
# (түлхүүр, нэр, hex)
SKINS = [
    ("fair", "Маш цайвар", "#f5d5b8"),
    ("light", "Цайвар", "#e8be98"),
    ("tan", "Шаргал", "#c68e5e"),
    ("brown", "Бор", "#8d5a38"),
    ("dark", "Хар", "#5c3a21"),
]
SKIN_HEX = {k: h for k, _, h in SKINS}
SKIN_NAME = {k: n for k, n, _ in SKINS}

DEFAULT_OUTFIT = {"top": "#9ca3af", "bottom": "#374151", "shoes": "#e5e7eb"}


# ======================= 2D дүр зурах =======================
def render_character(gender: str, skin_hex: str, outfit: dict[str, str], dead: bool = False) -> bytes:
    from PIL import Image, ImageDraw, ImageOps

    W, H = 400, 520
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):  # босоо градиент дэвсгэр
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(18 + 22 * t), int(20 + 14 * t), int(38 + 30 * t)))
    d.ellipse((90, 440, 310, 495), fill=(10, 10, 18))  # сүүдэр

    col = {**DEFAULT_OUTFIT, **outfit}
    skin = skin_hex
    hair = "#2b1b12"

    # хөл
    d.rounded_rectangle((158, 330, 198, 455), 10, fill=col["bottom"])
    d.rounded_rectangle((202, 330, 242, 455), 10, fill=col["bottom"])
    # гутал
    d.ellipse((148, 440, 206, 475), fill=col["shoes"])
    d.ellipse((194, 440, 252, 475), fill=col["shoes"])
    # гар
    d.rounded_rectangle((100, 205, 142, 325), 18, fill=col["top"])
    d.rounded_rectangle((258, 205, 300, 325), 18, fill=col["top"])
    d.ellipse((102, 315, 140, 350), fill=skin)
    d.ellipse((260, 315, 298, 350), fill=skin)
    # бие
    d.rounded_rectangle((138, 200, 262, 345), 22, fill=col["top"])
    if gender == "female":
        d.polygon([(138, 330), (262, 330), (280, 372), (120, 372)], fill=col["top"])
    # хүзүү, толгой
    d.rectangle((184, 172, 216, 208), fill=skin)
    # үс (арын хэсэг)
    if gender == "female":
        d.rounded_rectangle((136, 90, 264, 250), 40, fill=hair)
    d.ellipse((148, 85, 252, 192), fill=skin)
    # үс (урд)
    if gender == "female":
        d.pieslice((144, 78, 256, 170), 180, 360, fill=hair)
        d.rectangle((144, 124, 160, 150), fill=hair)
        d.rectangle((240, 124, 256, 150), fill=hair)
    else:
        d.pieslice((146, 78, 254, 160), 180, 360, fill=hair)
    # нүүр
    if dead:
        for cx in (183, 217):
            d.line((cx - 7, 126, cx + 7, 140), fill="#ef4444", width=3)
            d.line((cx - 7, 140, cx + 7, 126), fill="#ef4444", width=3)
        d.line((186, 165, 214, 165), fill="#1f2937", width=3)
    else:
        d.ellipse((177, 128, 189, 142), fill="#111827")
        d.ellipse((211, 128, 223, 142), fill="#111827")
        d.arc((184, 148, 216, 172), 20, 160, fill="#7f1d1d", width=3)
    # малгай
    if "hat" in col:
        d.rounded_rectangle((146, 58, 254, 104), 14, fill=col["hat"])
        d.rounded_rectangle((128, 96, 272, 112), 8, fill=col["hat"])
    # гоёл / цүнх
    if "acc" in col:
        d.rounded_rectangle((262, 300, 312, 350), 10, fill=col["acc"])
        d.line((200, 205, 296, 305), fill=col["acc"], width=5)

    if dead:
        img = ImageOps.grayscale(img).convert("RGB")
        d = ImageDraw.Draw(img)
        d.ellipse((165, 40, 235, 55), outline="#e5e7eb", width=3)  # гэрлэн
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ======================= бүртгэл =======================
class InfoModal(discord.ui.Modal, title="Нас, улсаа бичнэ үү"):
    age = discord.ui.TextInput(label="Нас (1-100)", placeholder="Жишээ: 22", max_length=3)
    country = discord.ui.TextInput(label="Аль улсын хүн бэ?", placeholder="Монгол", max_length=30)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction):
        raw = str(self.age.value).strip()
        if not raw.isdigit() or not 1 <= int(raw) <= 100:
            await interaction.response.send_message("❌ Нас 1-100 хооронд тоо байх ёстой.", ephemeral=True)
            return
        country = str(self.country.value).strip()
        if not country:
            await interaction.response.send_message("❌ Улсаа бичнэ үү.", ephemeral=True)
            return
        self.view.age = int(raw)
        self.view.country = country
        await self.view.refresh(interaction)


class OnboardingView(OwnerView):
    def __init__(self, cog, owner_id: int, prefix: str):
        super().__init__(owner_id, timeout=300)
        self.cog, self.prefix = cog, prefix
        self.gender = self.skin = self.country = None
        self.age = 0
        self.done = False

        self.gender_sel = discord.ui.Select(
            placeholder="1️⃣ Хүйсээ сонгоно уу",
            options=[discord.SelectOption(label=n, value=k, emoji=e) for k, (e, n) in GENDERS.items()],
        )
        self.gender_sel.callback = self.on_gender
        self.skin_sel = discord.ui.Select(
            placeholder="2️⃣ Арьсны өнгөө сонгоно уу",
            options=[discord.SelectOption(label=n, value=k) for k, n, _ in SKINS],
        )
        self.skin_sel.callback = self.on_skin
        self.info_btn = nav_button("3️⃣ Нас, улс бичих", self.on_info, discord.ButtonStyle.primary)
        self.finish_btn = nav_button("✅ Бүртгүүлэх", self.on_finish, discord.ButtonStyle.success, disabled=True)
        for c in (self.gender_sel, self.skin_sel, self.info_btn, self.finish_btn):
            self.add_item(c)

    def ready(self) -> bool:
        return bool(self.gender and self.skin and self.age and self.country)

    def embed(self) -> discord.Embed:
        def mark(v, text):
            return f"✅ {text}" if v else "⬜ сонгоогүй"

        embed = discord.Embed(
            title="📝 Дүрээ бүтээцгээе!",
            description=(
                "Ботыг ашиглахын өмнө өөрийн дүрийг бүртгүүлэх шаардлагатай.\n"
                "Доорх 3 алхмыг бөглөөд **Бүртгүүлэх** дарна уу."
            ),
            color=0x3B82F6,
        )
        embed.add_field(
            name="Хүйс",
            value=mark(self.gender, f"{GENDERS[self.gender][0]} {GENDERS[self.gender][1]}") if self.gender else "⬜ сонгоогүй",
            inline=True,
        )
        embed.add_field(
            name="Арьсны өнгө",
            value=mark(self.skin, SKIN_NAME.get(self.skin, "")) if self.skin else "⬜ сонгоогүй",
            inline=True,
        )
        embed.add_field(
            name="Нас, улс",
            value=f"✅ {self.age} нас · {self.country}" if self.age and self.country else "⬜ бөглөөгүй",
            inline=True,
        )
        return embed

    async def refresh(self, interaction):
        self.finish_btn.disabled = not self.ready()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def on_gender(self, interaction):
        self.gender = self.gender_sel.values[0]
        await self.refresh(interaction)

    async def on_skin(self, interaction):
        self.skin = self.skin_sel.values[0]
        await self.refresh(interaction)

    async def on_info(self, interaction):
        await interaction.response.send_modal(InfoModal(self))

    async def on_finish(self, interaction):
        if self.done or not self.ready():
            await interaction.response.defer()
            return
        self.done = True
        await self.cog.bot.db.register(self.owner_id, self.gender, self.age, self.country, self.skin)
        self.disable_all()
        self.stop()
        embed = discord.Embed(
            title="🎉 Бүртгэл амжилттай!",
            description=(
                f"Тавтай морил! Эхлэх мөнгө: **10,000₮**\n"
                f"`{self.prefix}help` — цэс · `{self.prefix}profile` — дүр · `{self.prefix}work` — ажил хийх\n\n"
                "Одоо командаа дахин бичээрэй."
            ),
            color=0x22C55E,
        )
        await interaction.response.edit_message(embed=embed, view=self)


class Profile(commands.Cog):
    """Бүртгэл, дүр (profile), хувцас."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    async def send_onboarding(self, ctx):
        view = OnboardingView(self, ctx.author.id, ctx.clean_prefix)
        view.message = await reply(ctx, embed=view.embed(), view=view)

    @commands.command(name="register", aliases=["reg"])
    async def register(self, ctx: commands.Context):
        """Дүрээ бүртгүүлэх"""
        user = await self.bot.db.get_user(ctx.author.id)
        if user["registered"]:
            await reply(ctx, f"✅ Та бүртгэлтэй байна. `{ctx.clean_prefix}profile` гэж дүрээ хараарай.")
            return
        await self.send_onboarding(ctx)

    async def outfit_colors(self, user_id: int) -> tuple[dict[str, str], list[str]]:
        equipped = await self.bot.db.get_equipped(user_id)
        inv = {r["item_key"] for r in await self.bot.db.get_inventory(user_id)}
        colors, names = {}, []
        for slot, key in equipped.items():
            it = ITEMS.get(key)
            if it and key in inv:
                colors[slot] = it.color
                names.append(f"{it.emoji} {it.name}")
        return colors, names

    @commands.command(name="profile", aliases=["p", "me", "char"])
    async def profile(self, ctx: commands.Context, member: discord.Member = None):
        """Дүрийн профайл: profile [@хүн]"""
        target = member or ctx.author
        user = await self.bot.db.get_user(target.id)
        if not user["registered"]:
            await reply(ctx, f"❌ {target.mention} бүртгүүлээгүй байна.")
            return
        colors, names = await self.outfit_colors(target.id)
        png = await asyncio.to_thread(
            render_character, user["gender"], SKIN_HEX.get(user["skin"], "#e8be98"), colors, bool(user["dead"])
        )
        file = discord.File(io.BytesIO(png), filename="profile.png")
        g_emoji, g_name = GENDERS.get(user["gender"], ("🧑", "?"))
        status = "💀 Үхсэн" if user["dead"] else "🟢 Амьд"
        spouse = f"<@{user['spouse']}> 💞" if user["spouse"] else "Ганц бие"
        pet = get_pet(user["pet"])
        house = get_house(user["house"])
        total = user["balance"] + user["bank"] + user["safe_money"]

        embed = discord.Embed(title=f"{g_emoji} {target.display_name}", color=0x3B82F6)
        embed.add_field(name="Хүйс", value=g_name, inline=True)
        embed.add_field(name="Нас", value=str(user["age"]), inline=True)
        embed.add_field(name="Улс", value=user["country"] or "—", inline=True)
        embed.add_field(name="Төлөв", value=status, inline=True)
        embed.add_field(name="Гэр бүл", value=spouse, inline=True)
        embed.add_field(name="💎 Хөрөнгө", value=fmt(total), inline=True)
        embed.add_field(name="💪 Хүч", value=f"{user['strength']}/{MAX_STRENGTH}", inline=True)
        embed.add_field(name="🏠 Байшин", value=f"{house.emoji} {house.name}" if house else "Байхгүй", inline=True)
        embed.add_field(name="🐾 Амьтан", value=f"{pet.emoji} {pet.name}" if pet else "Байхгүй", inline=True)
        embed.add_field(
            name="👕 Өмссөн хувцас",
            value="\n".join(names) if names else f"Байхгүй · `{ctx.clean_prefix}shop clothes`",
            inline=False,
        )
        embed.set_image(url="attachment://profile.png")
        embed.set_footer(text=f"{ctx.clean_prefix}wear <ID> | {ctx.clean_prefix}undress <slot>")
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.command(name="wear", aliases=["өмс"])
    async def wear(self, ctx: commands.Context, item_id: str):
        """Хувцас өмсөх: wear <ID>"""
        matches = [i for i in find_items(item_id) if i.kind == "clothes"]
        if not matches:
            await reply(ctx, f"❌ Хувцас олдсонгүй. `{ctx.clean_prefix}shop clothes` дээрх ID-г ашиглана уу.")
            return
        await wear_item(self.bot, ctx, matches[0])

    @commands.command(name="undress", aliases=["unwear", "tuh"])
    async def undress(self, ctx: commands.Context, what: str):
        """Хувцас тайлах: undress <hat | top | bottom | shoes | acc | ID>"""
        slot = what.lower()
        if slot not in SLOT_NAMES:
            matches = [i for i in find_items(what) if i.kind == "clothes"]
            if not matches:
                await send_usage(ctx)
                return
            slot = matches[0].slot
        if await self.bot.db.unequip(ctx.author.id, slot):
            await reply(ctx, f"👕 {SLOT_NAMES[slot]}-ээ тайллаа.")
        else:
            await reply(ctx, "❌ Энэ хэсэгт хувцас өмсөөгүй байна.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
