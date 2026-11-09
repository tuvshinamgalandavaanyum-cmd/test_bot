import asyncio
import json

import discord
from discord.ext import commands

from avatar import HAIR_COLORS, render_character
from houses import get_house
from items import CLOTHES_STYLE, get_item, get_pet
from ui import OwnerView
from utils import fmt, reply

GENDERS = {"male": "♂️ Эрэгтэй", "female": "♀️ Эмэгтэй"}
SLOT_NAMES = {"top": "Дээд", "bottom": "Доод", "full": "Бүтэн", "shoes": "Гутал",
              "hat": "Малгай", "face": "Нүүр", "neck": "Хүзүү"}


# ---------------------------------------------------------------- бүртгэлийн асуултууд
class HairSelect(discord.ui.Select):
    def __init__(self, cog, owner_id: int, gender: str, age: int, nation: str):
        self.cog, self.gender, self.age, self.nation = cog, gender, age, nation
        super().__init__(
            placeholder="Үсний өнгөө сонгоно уу...",
            options=[discord.SelectOption(label=name, value=key) for key, (name, _) in HAIR_COLORS.items()],
        )

    async def callback(self, interaction: discord.Interaction):
        hair = self.values[0]
        uid = interaction.user.id
        await self.cog.bot.db.save_profile(uid, self.gender, self.age, self.nation, hair)
        await interaction.response.edit_message(
            content="✅ Character амжилттай үүслээ! Одоо бот ашиглаж болно.", embed=None, view=None
        )
        embed, file = await self.cog.build_profile(interaction.user)
        await interaction.followup.send(content=interaction.user.mention, embed=embed, file=file)


class AgeNationModal(discord.ui.Modal, title="Character мэдээлэл"):
    age = discord.ui.TextInput(label="Нас (1-100)", min_length=1, max_length=3, placeholder="20")
    nation = discord.ui.TextInput(label="Ямар улсын хүн бэ?", min_length=2, max_length=30, placeholder="Монгол")

    def __init__(self, cog, gender: str):
        super().__init__()
        self.cog, self.gender = cog, gender

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.age.value.strip()
        if not raw.isdigit() or not (1 <= int(raw) <= 100):
            await interaction.response.send_message(
                "❌ Нас 1-ээс 100 хүртэлх тоо байх ёстой. Дахин эхлүүлнэ үү:",
                view=GenderView(self.cog, interaction.user.id),
                ephemeral=True,
            )
            return
        view = OwnerView(interaction.user.id, timeout=180)
        view.add_item(HairSelect(self.cog, interaction.user.id, self.gender, int(raw), self.nation.value.strip()))
        await interaction.response.send_message(
            "💇 Сүүлийн асуулт: **үсний өнгөө** сонгоно уу.", view=view, ephemeral=True
        )


class GenderView(OwnerView):
    def __init__(self, cog, owner_id: int):
        super().__init__(owner_id, timeout=180)
        self.cog = cog

    @discord.ui.button(label="Эрэгтэй", emoji="♂️", style=discord.ButtonStyle.primary)
    async def male(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AgeNationModal(self.cog, "male"))

    @discord.ui.button(label="Эмэгтэй", emoji="♀️", style=discord.ButtonStyle.danger)
    async def female(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AgeNationModal(self.cog, "female"))


class StartView(OwnerView):
    """'Хариулах' товч: darwal асуултууд эхэлнэ."""

    def __init__(self, cog, owner_id: int):
        super().__init__(owner_id, timeout=300)
        self.cog = cog

    @discord.ui.button(label="Хариулах", emoji="📝", style=discord.ButtonStyle.success)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "👤 **1/3 · Хүйсээ сонгоно уу**",
            view=GenderView(self.cog, interaction.user.id),
            ephemeral=True,
        )


async def send_register_prompt(bot, ctx: commands.Context):
    """Бүртгэлгүй хүн команд бичихэд бот ажиллахгүй, оронд нь асуулт эхлүүлнэ."""
    cog = bot.get_cog("Profile")
    embed = discord.Embed(
        title="👋 Тавтай морил!",
        description=(
            "Ботыг ашиглахаас өмнө **character**-аа үүсгэх хэрэгтэй.\n"
            "Доорх **Хариулах** товчийг дараад хүйс, нас, улс, үсний өнгөө сонгоно уу."
        ),
        color=0x22C55E,
    )
    view = StartView(cog, ctx.author.id)
    view.message = await reply(ctx, embed=embed, view=view)


# ---------------------------------------------------------------- cog
class Profile(commands.Cog):
    """Character профайл, хувцас."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    async def build_profile(self, member: discord.abc.User):
        db = self.bot.db
        prof = await db.get_profile(member.id)
        user = await db.get_user(member.id)
        outfit = json.loads(prof["outfit"] or "{}")
        buf = await asyncio.to_thread(render_character, prof["gender"], prof["age"], prof["hair"], outfit)
        file = discord.File(buf, filename="character.png")

        embed = discord.Embed(title=f"👤 {member.display_name}", color=0x6366F1)
        embed.set_image(url="attachment://character.png")
        embed.add_field(name="Хүйс", value=GENDERS.get(prof["gender"], "?"), inline=True)
        embed.add_field(name="Нас", value=str(prof["age"]), inline=True)
        embed.add_field(name="Улс", value=prof["nationality"], inline=True)
        embed.add_field(name="Үс", value=HAIR_COLORS.get(prof["hair"], ("?",))[0], inline=True)
        embed.add_field(name="💪 Хүч", value=str(user["strength"]), inline=True)
        embed.add_field(name="💰 Нийт", value=fmt(user["balance"] + user["bank"] + user["safe_money"]), inline=True)

        spouse = prof["spouse_id"]
        embed.add_field(
            name="💍 Гэр бүл",
            value=(f"<@{spouse}> · 💖 {prof['love']}" if spouse else "Ганц бие"),
            inline=False,
        )
        extras = []
        house = get_house(user["house"])
        if house:
            extras.append(f"🏠 {house.name}")
        pet = get_pet(user["pet"])
        if pet:
            extras.append(f"{pet.emoji} {pet.name}")
        if user["dead"]:
            extras.append("💀 Үхсэн")
        if extras:
            embed.add_field(name="Бусад", value=" · ".join(extras), inline=False)
        if outfit:
            worn = []
            for slot, key in outfit.items():
                it = get_item(key)
                if it:
                    worn.append(f"{it.emoji} {it.name}")
            embed.add_field(name="👕 Өмссөн", value=" · ".join(worn), inline=False)
        return embed, file

    @commands.command(name="profile", aliases=["prof", "me", "character"])
    async def profile(self, ctx: commands.Context, member: discord.Member = None):
        """Character профайл харах: profile [@хүн]"""
        target = member or ctx.author
        prof = await self.bot.db.get_profile(target.id)
        if prof is None:
            if target.id == ctx.author.id:
                await send_register_prompt(self.bot, ctx)
            else:
                await reply(ctx, f"❌ {target.display_name} character үүсгээгүй байна.")
            return
        embed, file = await self.build_profile(target)
        await reply(ctx, embed=embed, file=file)

    @commands.command(name="wear", aliases=["outfit", "huwtsas"])
    async def wear(self, ctx: commands.Context, *, query: str = None):
        """Хувцас өмсөх: wear <ID> | wear off"""
        from cogs.shop import resolve_item

        db = self.bot.db
        prof = await db.get_profile(ctx.author.id)
        outfit = json.loads(prof["outfit"] or "{}")

        if query is None:
            if not outfit:
                await reply(ctx, f"👕 Та юу ч өмсөөгүй байна. `{ctx.clean_prefix}shop clothes` дээрээс хувцас аваад "
                                 f"`{ctx.clean_prefix}wear <ID>` гэж өмсөөрэй.")
                return
            lines = [f"**{SLOT_NAMES.get(s, s)}**: {get_item(k).emoji} {get_item(k).name}"
                     for s, k in outfit.items() if get_item(k)]
            await reply(ctx, "👕 Таны хувцас:\n" + "\n".join(lines))
            return
        if query.strip().lower() in ("off", "unwear", "бүгд", "тайлах"):
            await db.set_outfit(ctx.author.id, "{}")
            await reply(ctx, "👕 Бүх хувцсаа тайллаа.")
            return

        rows = await db.get_inventory(ctx.author.id)
        pool = [it for it in (get_item(r["item_key"]) for r in rows) if it and it.key in CLOTHES_STYLE]
        if not pool:
            await reply(ctx, f"❌ Танд өмсөх хувцас алга. `{ctx.clean_prefix}shop clothes`")
            return
        item = await resolve_item(ctx, query, pool)
        if item is None:
            return
        slot = CLOTHES_STYLE[item.key][0]
        if slot == "full":
            outfit.pop("top", None)
            outfit.pop("bottom", None)
        elif slot in ("top", "bottom"):
            outfit.pop("full", None)
        outfit[slot] = item.key
        await db.set_outfit(ctx.author.id, json.dumps(outfit))
        await reply(ctx, f"✨ {item.emoji} **{item.name}** өмслөө! `{ctx.clean_prefix}profile` гэж харна уу.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
