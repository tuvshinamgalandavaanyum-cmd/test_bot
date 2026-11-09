import random
import time

import discord
from discord.ext import commands

from houses import comfort_pct
from items import ITEMS, get_pet
from jobs import JOBS
from utils import MAX_STRENGTH, fmt, fmt_duration, jailed, reply, tax_split

WORK_COOLDOWN = 60 * 60  # 1 цаг
WORKOUT_COOLDOWN = 2 * 60 * 60  # 2 цаг
CAT_BONUS = 0.10  # Муур: ажлын цалин +10%
STRENGTH_BONUS = 0.01  # хүч 1 тутамд ажлын цалин +1%


def pay_status(pay: int) -> str:
    if pay < 60_000:
        return "🪙 Бага цалин"
    if pay < 80_000:
        return "💼 Дундаж цалин"
    if pay < 100_000:
        return "✨ Сайн цалинтай ажил"
    return "🔥 Маш өндөр цалин"


async def placed_value(db, user_id: int) -> int:
    rows = await db.get_house_items(user_id)
    return sum(ITEMS[r["item_key"]].price * r["qty"] for r in rows if r["item_key"] in ITEMS)


class Work(commands.Cog):
    """Санамсаргүй ажил хийх, дасгал хийх."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.command(name="work", aliases=["w"])
    async def work(self, ctx: commands.Context):
        """Санамсаргүй ажил хийж цалин авах"""
        user = await self.bot.db.get_user(ctx.author.id)
        if await jailed(ctx, user):
            return
        now = time.time()

        left = user["last_work"] + WORK_COOLDOWN - now
        if left > 0:
            await reply(ctx, f"⏳ Та амарч байна. **{fmt_duration(left)}**-ийн дараа дахин ажиллана.")
            return

        job = random.choice(JOBS)
        base = int(job.salary * random.uniform(0.9, 1.1) / 100) * 100
        bonus_pct = user["strength"] * STRENGTH_BONUS
        comfort = comfort_pct(await placed_value(self.bot.db, ctx.author.id)) / 100
        pet = get_pet(user["pet"])
        cat = CAT_BONUS if pet and pet.key == "cat" else 0.0
        pay = int(base * (1 + bonus_pct + comfort + cat) / 100) * 100

        gross = pay
        pay, tax = tax_split(gross)
        ok = await self.bot.db.complete_work(ctx.author.id, pay, now, WORK_COOLDOWN)
        if not ok:
            await reply(ctx, "⏳ Та амарч байна. Дахин оролдоно уу.")
            return
        await self.bot.db.treasury_add(tax)

        embed = discord.Embed(title="💼 Цагийн ажил хийлээ", color=0x3B82F6)
        embed.description = f"{job.emoji} **{job.name}**\n*{job.desc}*"
        embed.add_field(name="⏱️ Ажилласан хугацаа", value="1 цаг", inline=True)
        embed.add_field(name="💵 Олсон мөнгө", value=f"**{pay:,} ₮**", inline=True)
        embed.add_field(name="🏛️ Татвар (10%)", value=f"-{tax:,} ₮", inline=True)
        embed.add_field(name="📈 Статус", value=pay_status(pay), inline=False)
        extras = []
        if bonus_pct:
            extras.append(f"💪 Хүч +{int(bonus_pct * 100)}%")
        if comfort:
            extras.append(f"🏠 Байшин +{int(comfort * 100)}%")
        if cat:
            extras.append("🐈 Муур +10%")
        if extras:
            embed.add_field(name="✨ Нэмэгдэл", value=" · ".join(extras), inline=False)
        embed.set_footer(text=f"⏰ Дараагийн ажил: 1 цагийн дараа • {ctx.clean_prefix}workout хийвэл илүү олно")
        await reply(ctx, embed=embed)

    @commands.command(name="jobs")
    async def jobs_list(self, ctx: commands.Context):
        """Хийж болох ажлууд ба цалингийн жагсаалт"""
        lines = [f"{j.emoji} **{j.name}** — ~{fmt(j.salary)}" for j in JOBS]
        half = len(lines) // 2
        embed = discord.Embed(
            title="💼 Ажлын жагсаалт",
            description=(
                f"`{ctx.clean_prefix}work` бүрт эдгээрээс санамсаргүй нэгийг хийнэ. "
                "Цалин ажлын газраас хамаарна."
            ),
            color=0x3B82F6,
        )
        embed.add_field(name="​", value="\n".join(lines[:half]), inline=True)
        embed.add_field(name="​", value="\n".join(lines[half:]), inline=True)
        await reply(ctx, embed=embed)

    @commands.command(name="workout", aliases=["gym"])
    async def workout(self, ctx: commands.Context):
        """Дасгал хийж хүч нэмэх (ажлын орлого, дээрэмд тусална)"""
        user = await self.bot.db.get_user(ctx.author.id)
        if await jailed(ctx, user):
            return
        now = time.time()

        if user["strength"] >= MAX_STRENGTH:
            await reply(ctx, f"💪 Таны хүч дээд түвшиндээ ({MAX_STRENGTH}) хүрсэн байна.")
            return
        left = user["last_workout"] + WORKOUT_COOLDOWN - now
        if left > 0:
            await reply(ctx, f"⏳ Булчин амарч байна. **{fmt_duration(left)}**-ийн дараа дахин дасгал хийнэ.")
            return

        ok = await self.bot.db.complete_workout(ctx.author.id, now, WORKOUT_COOLDOWN, MAX_STRENGTH)
        if not ok:
            await reply(ctx, "⏳ Булчин амарч байна. Дахин оролдоно уу.")
            return

        s = user["strength"] + 1
        embed = discord.Embed(title="🏋️ Дасгал хийлээ", color=0xF97316)
        embed.description = "💪 *Фитнесс төвд хүчтэй дасгал хийлээ*"
        embed.add_field(name="⏱️ Хугацаа", value="1 цаг", inline=True)
        embed.add_field(name="💪 Хүч", value=f"**{s}/{MAX_STRENGTH}**", inline=True)
        embed.add_field(
            name="📈 Статус",
            value=f"Ажлын орлого **+{int(s * STRENGTH_BONUS * 100)}%** · дээрэмд амжилт +{s}%",
            inline=False,
        )
        embed.set_footer(text="⏰ Дараагийн дасгал: 2 цагийн дараа • Дасгал хийх тусам ажлын орлого нэмэгдэнэ")
        await reply(ctx, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Work(bot))
