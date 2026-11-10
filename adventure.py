import random
import time

import discord
from discord.ext import commands

from actions import maybe_revive_drop, open_box, revive_player
from items import get_item
from usage import send_usage
from utils import fmt_duration, jailed, luck_bonus, parse_qty, reply

MINE_COOLDOWN = 30 * 60
MINE_CHANCE = 40  # алт олох магадлал (%)

MINE_FAIL = [
    "Чулуу, шороо л сугалж байна. Алт гэнэ, хөөрхий 🪨",
    "Нүх ухаж байтал хөрш чинь «Та юу хийж байна?» гэж асуулаа. Алт алга 🕳️",
    "Олсон нь хуучин шар айрагны лонх 🍺 (хэн нэгэн таныг түрүүлжээ)",
    "Алтны оронд өөрийн хуучин гутлаа ухлаа 👞",
    "Газар доороос «Хоосон шүү» гэсэн хоолой сонсогдлоо... 👻",
    "Алт олох гэж ухсаар байтал ухаж байсан хүрз тань хугарлаа 🔧",
    "Энэ удаа азгүй. Алт чинь амарч байгаа бололтой 😴",
    "Ганц хөндий хорхой л харагдлаа 🪱",
    "Алтны шинж тэмдэг байтал... хуучин цоожны түлхүүр л байлаа 🗝️",
]
MINE_OK = [
    "Гялалзсан юм харагдлаа! ✨",
    "Хүрз «тоон» гэж дуугарлаа... Алт! 🤩",
    "Энэ удаа аз таарлаа! 🍀",
]


class Adventure(commands.Cog):
    """Алт малтах, хайрцаг нээх, амилуулах."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.command(name="mine", aliases=["dig", "malta"])
    async def mine(self, ctx: commands.Context):
        """Алт малтах (амжилтын магадлал 40%)"""
        user = await self.bot.db.get_user(ctx.author.id)
        if await jailed(ctx, user):
            return
        now = time.time()
        if not await self.bot.db.start_cooldown(ctx.author.id, "last_mine", now, MINE_COOLDOWN):
            left = user["last_mine"] + MINE_COOLDOWN - now
            await reply(ctx, f"⏳ Ядарсан байна. **{fmt_duration(left)}**-ийн дараа дахин малтана.")
            return

        chance = MINE_CHANCE + luck_bonus(user)
        embed = discord.Embed(title="⛏️ Алт малтлаа", color=0xF59E0B)
        if random.randint(1, 100) <= chance:
            qty = random.choices([1, 2, 3], weights=[55, 33, 12])[0]
            await self.bot.db.add_item(ctx.author.id, "gold_ore", qty)
            ore = get_item("gold_ore")
            embed.color = 0x22C55E
            embed.description = f"{random.choice(MINE_OK)}\n{ore.emoji} **{ore.name} × {qty}** олдлоо!"
            embed.add_field(name="💰 Үнэ", value=f"1 ширхэг ≈ {ore.sell_price:,}₮ (зарах: `{ctx.clean_prefix}sell gold_ore`)", inline=False)
        else:
            embed.color = 0x6B7280
            embed.description = random.choice(MINE_FAIL)
        embed.set_footer(text=f"Магадлал: {chance}% · дараагийн малталт 30 минутын дараа")
        await reply(ctx, embed=embed)
        await maybe_revive_drop(self.bot, ctx)

    @commands.command(name="open", aliases=["unbox"])
    async def open(self, ctx: commands.Context, item_id: str, qty: str = "1"):
        """Хайрцаг, кейс, сан нээх: open <box | case | chest> [тоо]"""
        n = parse_qty(qty, 1, 20)
        if n is None:
            await reply(ctx, "❌ Тоо 1-ээс 20 хооронд байх ёстой.")
            return
        it = get_item(item_id.lower())
        if it is None or it.kind != "box":
            await send_usage(ctx)
            return
        await open_box(self.bot, ctx, it, n)

    @commands.command(name="revive")
    async def revive(self, ctx: commands.Context, member: discord.Member = None):
        """Revive Active ашиглан амилуулах: revive [@хүн]"""
        await revive_player(self.bot, ctx, member or ctx.author)


async def setup(bot: commands.Bot):
    await bot.add_cog(Adventure(bot))
