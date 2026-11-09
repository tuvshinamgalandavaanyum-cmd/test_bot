import time

import discord
from discord.ext import commands

from houses import get_house
from ui import OwnerView
from utils import HUNGER_SECONDS, DEAD_SECONDS, fmt, fmt_duration, hunger_left, reply

REQUIRE_PHONE = False  # True болговол цүнхэнд "phone" бараа байх ёстой

APPS = [
    ("bank", "🏦", "Банк"),
    ("health", "🍞", "Эрүүл мэнд"),
    ("tax", "🏛️", "Татвар"),
    ("server", "📡", "Сервер"),
]


class PhoneView(OwnerView):
    def __init__(self, cog, ctx):
        super().__init__(ctx.author.id, timeout=180)
        self.cog, self.ctx = cog, ctx
        self.select = discord.ui.Select(
            placeholder="📱 Апп сонгоно уу...",
            options=[discord.SelectOption(label=name, value=key, emoji=emoji) for key, emoji, name in APPS],
        )
        self.select.callback = self.on_select
        self.add_item(self.select)

    async def on_select(self, interaction: discord.Interaction):
        embed = await self.cog.app_embed(self.select.values[0], self.ctx)
        await interaction.response.edit_message(embed=embed, view=self)


class Phone(commands.Cog):
    """Утас (апп-уудтай) болон серверийн мэдээлэл."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.started = time.time()

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    async def server_embed(self, ctx) -> discord.Embed:
        db = self.bot.db
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(title=f"📡 {ctx.guild.name}", color=0x0EA5E9)
        embed.add_field(name="🏓 Ping", value=f"{latency} ms", inline=True)
        embed.add_field(name="⏱️ Ажилласан", value=fmt_duration(time.time() - self.started), inline=True)
        embed.add_field(name="👥 Гишүүд", value=str(ctx.guild.member_count), inline=True)
        embed.add_field(name="👤 Character", value=str(await db.count_profiles()), inline=True)
        embed.add_field(name="💰 Бүртгэлтэй хэрэглэгч", value=str(await db.count_users()), inline=True)
        embed.add_field(name="🏛️ Татварын сан", value=fmt(await db.treasury_get()), inline=True)
        embed.set_footer(text=f"Угтвар: {ctx.clean_prefix} · {ctx.clean_prefix}help")
        return embed

    async def app_embed(self, key: str, ctx) -> discord.Embed:
        db = self.bot.db
        user = await db.get_user(ctx.author.id)
        if key == "bank":
            embed = discord.Embed(title="🏦 Банкны апп", color=0x22C55E)
            embed.add_field(name="💵 Хэтэвч", value=fmt(user["balance"]), inline=True)
            embed.add_field(name="🏛️ Банк", value=fmt(user["bank"]), inline=True)
            embed.add_field(name="🔐 Сейф", value=fmt(user["safe_money"]), inline=True)
            house = get_house(user["house"])
            embed.add_field(name="🏠 Байшин", value=house.name if house else "Байхгүй", inline=True)
            embed.add_field(name="💎 Нийт", value=fmt(user["balance"] + user["bank"] + user["safe_money"]), inline=True)
            return embed
        if key == "health":
            embed = discord.Embed(title="🍞 Эрүүл мэндийн апп", color=0xF59E0B)
            if user["dead"]:
                embed.description = "💀 **Та нас барсан.** Revive Active хэрэгтэй."
            else:
                now = time.time()
                since = now - user["last_fed"]
                left = hunger_left(user["last_fed"], now)
                if left > 0:
                    embed.description = f"😋 Цатгалан. Өлсөх хүртэл: **{fmt_duration(left)}**"
                else:
                    to_dead = max(0, DEAD_SECONDS - since)
                    embed.description = (
                        f"🍞 **Та өлсөж байна!** 2 цаг тутам хэтэвчнээс 2.5% хасагдана.\n"
                        f"Үхэх хүртэл: **{fmt_duration(to_dead)}**"
                    )
            embed.add_field(name="💪 Хүч", value=str(user["strength"]), inline=True)
            return embed
        if key == "tax":
            embed = discord.Embed(title="🏛️ Татварын апп", color=0x0EA5E9)
            embed.description = (
                "Өдрийн орлогоос (**daily**, **work**) 10% татвар авна.\n"
                f"Татварын сан: **{fmt(await db.treasury_get())}**\n"
                "Сангаас owner giveaway зохион явуулдаг."
            )
            return embed
        return await self.server_embed(ctx)

    @commands.command(name="phone", aliases=["utas", "qutas"])
    async def phone(self, ctx: commands.Context):
        """Утас: банк, эрүүл мэнд, татвар, сервер апп"""
        if REQUIRE_PHONE and await self.bot.db.item_qty(ctx.author.id, "phone") <= 0:
            await reply(ctx, f"📵 Танд утас алга. `{ctx.clean_prefix}shop digital` дээрээс `phone` авна уу.")
            return
        view = PhoneView(self, ctx)
        embed = discord.Embed(
            title="📱 Утас",
            description="Доорх цэснээс апп сонгоно уу:\n🏦 Банк · 🍞 Эрүүл мэнд · 🏛️ Татвар · 📡 Сервер",
            color=0x1F2937,
        )
        embed.set_footer(text=time.strftime("%H:%M", time.gmtime(time.time() + 8 * 3600)) + " (УБ)")
        view.message = await reply(ctx, embed=embed, view=view)

    @commands.command(name="info", aliases=["server", "serverinfo"])
    async def info(self, ctx: commands.Context):
        """Серверийн мэдээлэл, ping"""
        await reply(ctx, embed=await self.server_embed(ctx))

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        """Ботын ping"""
        await reply(ctx, f"🏓 Pong! **{round(self.bot.latency * 1000)} ms**")


async def setup(bot: commands.Bot):
    await bot.add_cog(Phone(bot))
