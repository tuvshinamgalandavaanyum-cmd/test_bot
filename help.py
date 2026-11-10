import time
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from ui import OwnerView, nav_button
from utils import reply

UB = timezone(timedelta(hours=8))

# (түлхүүр, emoji, нэр, тайлбар, [(команд, тайлбар)])
APPS = [
    ("bank", "🏦", "Банк", "Мөнгө, данс", [
        ("bal [@хүн]", "Хэтэвч, банк, хөрөнгө"),
        ("daily", "Өдрийн цалин (10% татвартай)"),
        ("dep / with <дүн|all>", "Банкинд хийх / авах (шимтгэл 200₮)"),
        ("give <@хүн> <дүн>", "Мөнгө шилжүүлэх"),
        ("lb [bank|wallet|total]", "Тэргүүлэгчид"),
        ("pool", "Татварын сан"),
    ]),
    ("work", "💼", "Ажил", "Ажил, дасгал, малтлага", [
        ("work", "Ажил хийх (1 цаг, 10% татвар)"),
        ("jobs", "Ажлын жагсаалт"),
        ("workout", "Дасгал: хүч нэмэгдэж цалин өснө"),
        ("mine", "Алт малтах (40%)"),
    ]),
    ("shop", "🛍️", "Дэлгүүр", "Бараа, хоол, хайрцаг", [
        ("shop [ангилал]", "food, digital, home, house, clothes, jewel, metal, box, tool"),
        ("buy <ID> [тоо]", "Авах"),
        ("inv [use <ID>]", "Цүнх / ашиглах"),
        ("sell <ID|all>", "Зарах (70%)"),
        ("gift <ID> <@хүн>", "Бэлэглэх"),
        ("eat <ID>", "Хоол идэх"),
        ("open <box|case|chest>", "Хайрцаг нээх"),
        ("petshop / buypet", "Амьтан"),
    ]),
    ("casino", "🎰", "Казино", "Зөвхөн банкнаас", [
        ("cf <дүн> [сүүл|тоо]", "Зоос шидэх"),
        ("dice <дүн> <1-6>", "Шоо"),
        ("slots <дүн>", "Слот"),
        ("mf <дүн>", "Minefield"),
        ("duel <@хүн> <дүн>", "Чулуу-хайч-даавуу"),
        ("draw <@хүн> <дүн>", "Quick Draw"),
    ]),
    ("house", "🏠", "Байшин", "Байшин, сейф", [
        ("house", "Байшингаа харах"),
        ("house shop / buy <ID>", "Байшин авах"),
        ("house <өрөө> use|unuse <ID>", "Эд зүйл байрлуулах"),
        ("safe [buy|put|take]", "Сейф"),
    ]),
    ("crime", "🥷", "Гэмт хэрэг", "Хулгай, дээрэм, хакер", [
        ("steal [1-5]", "Байшин руу хулгай (house rob)"),
        ("rob <@хүн>", "Дээрэм"),
        ("hack <@хүн>", "Хакердалт (компьютер хэрэгтэй)"),
        ("block", "Бамбай 2.5 цаг"),
        ("bail", "Шоронгоос гарах"),
    ]),
    ("profile", "👤", "Дүр", "Профайл, хувцас", [
        ("profile [@хүн]", "2D дүр, мэдээлэл"),
        ("wear <ID>", "Хувцас өмсөх"),
        ("undress <slot>", "Тайлах (hat/top/bottom/shoes/acc)"),
    ]),
    ("love", "💞", "Харилцаа", "Гэр бүл, романс", [
        ("marry <@хүн>", "Гэрлэх санал (бөгж)"),
        ("couple", "Гэр бүлийн мэдээлэл"),
        ("date", "Болзоо"),
        ("divorce", "Салах"),
    ]),
    ("emote", "🎭", "Эможи", "Бусдад үзүүлэх", [
        ("hug, kiss, pat, cuddle", "+ <@хүн>"),
        ("slap, punch, bite, poke, kick", "+ <@хүн>"),
        ("highfive, dance, laugh, blush, cry", "+ <@хүн>"),
        ("flirt, wink, lick, seduce, spank", "🔞 зөвхөн NSFW суваг"),
    ]),
    ("life", "💖", "Амьдрал", "Хоол, үхэл, Revive", [
        ("eat <ID>", "3 хоног хоолгүй бол 2 цаг тутам хэтэвчний 2.5% хасагдана"),
        ("revive [@хүн]", "7 хоног хоолгүй бол үхнэ. Revive Active амилуулна"),
        ("inv use luck_potion / money_potion", "Аз, орлого +10% (1 цаг)"),
    ]),
    ("info", "ℹ️", "Мэдээлэл", "Бот, сервер", [
        ("info", "Ping, сервер, статистик"),
        ("phone / help", "Энэ утас"),
        ("register", "Бүртгүүлэх"),
    ]),
]
APP_BY_KEY = {a[0]: a for a in APPS}


def home_embed(prefix: str, name: str) -> discord.Embed:
    now = datetime.now(UB)
    days = ["Даваа", "Мягмар", "Лхагва", "Пүрэв", "Баасан", "Бямба", "Ням"]
    grid = []
    row = []
    for _, emoji, title, _, _ in APPS:
        row.append(f"{emoji} {title}")
        if len(row) == 3:
            grid.append("   ".join(row))
            row = []
    if row:
        grid.append("   ".join(row))
    screen = (
        f"📶 5G                 🔋 {80 + now.minute % 20}%\n"
        f"🕒 **{now:%H:%M}** · {days[now.weekday()]}\n\n"
        + "\n\n".join(grid)
    )
    embed = discord.Embed(title="📱 Утас", description=screen, color=0x111827)
    embed.set_footer(text=f"{name} · доорх цэснээс апп нээнэ · {prefix}phone")
    return embed


def app_embed(key: str, prefix: str) -> discord.Embed:
    _, emoji, title, desc, cmds = APP_BY_KEY[key]
    lines = [f"`{prefix}{c}` — {d}" for c, d in cmds]
    embed = discord.Embed(title=f"{emoji} {title}", description=f"*{desc}*\n\n" + "\n".join(lines), color=0x3B82F6)
    embed.set_footer(text="<> заавал, [] заавал биш · 🏠 Нүүр дарж буцна")
    return embed


class PhoneView(OwnerView):
    def __init__(self, owner_id: int, prefix: str, name: str):
        super().__init__(owner_id, timeout=180)
        self.prefix, self.name = prefix, name
        self.select = discord.ui.Select(
            placeholder="📲 Апп нээх...",
            options=[discord.SelectOption(label=t, value=k, emoji=e, description=d) for k, e, t, d, _ in APPS],
        )
        self.select.callback = self.on_select
        self.home_btn = nav_button("🏠 Нүүр", self.on_home, discord.ButtonStyle.primary)
        self.add_item(self.select)
        self.add_item(self.home_btn)

    async def on_select(self, interaction):
        await interaction.response.edit_message(embed=app_embed(self.select.values[0], self.prefix), view=self)

    async def on_home(self, interaction):
        await interaction.response.edit_message(embed=home_embed(self.prefix, self.name), view=self)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h", "commands", "phone", "utas", "tel"])
    async def help(self, ctx: commands.Context, app: str = None):
        """Утас (тусламжийн цэс): help [апп]"""
        view = PhoneView(ctx.author.id, ctx.clean_prefix, ctx.author.display_name)
        embed = home_embed(ctx.clean_prefix, ctx.author.display_name)
        if app:
            q = app.lower()
            for key, _, title, _, _ in APPS:
                if q in (key, title.lower()):
                    embed = app_embed(key, ctx.clean_prefix)
                    break
        view.message = await reply(ctx, embed=embed, view=view)

    @commands.command(name="info", aliases=["ping", "stats", "server"])
    async def info(self, ctx: commands.Context):
        """Бот ба серверийн мэдээлэл"""
        db = self.bot.db
        stats = await db.stats()
        top = await db.top("total", 1, 0)
        started = getattr(self.bot, "started_at", time.time())
        up = int(time.time() - started)
        d, rem = divmod(up, 86400)
        h, rem = divmod(rem, 3600)
        ping = round(self.bot.latency * 1000) if self.bot.latency == self.bot.latency else 0

        embed = discord.Embed(title="ℹ️ Мэдээлэл", color=0x3B82F6)
        embed.add_field(name="🏓 Ping", value=f"{ping} ms", inline=True)
        embed.add_field(name="⏱️ Ажилласан", value=f"{d}ө {h}ц {rem // 60}м", inline=True)
        embed.add_field(name="🌐 Сервер", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👥 Гишүүд", value=str(ctx.guild.member_count), inline=True)
        embed.add_field(name="🎮 Тоглогч", value=str(stats["players"]), inline=True)
        embed.add_field(name="💞 Гэрлэсэн хос", value=str(stats["married"]), inline=True)
        embed.add_field(name="💰 Нийт мөнгө", value=f"{stats['money']:,}₮", inline=True)
        embed.add_field(name="🏛️ Татварын сан", value=f"{stats['pool']:,}₮", inline=True)
        embed.add_field(name="⛓️ Шоронд", value=str(stats["jailed"]), inline=True)
        embed.add_field(name="💀 Үхсэн", value=str(stats["dead"]), inline=True)
        if top:
            t = top[0]
            embed.add_field(name="👑 Хамгийн баян", value=f"<@{t['user_id']}>", inline=True)
        embed.set_footer(text=f"{ctx.clean_prefix}help — утас")
        await reply(ctx, embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))
