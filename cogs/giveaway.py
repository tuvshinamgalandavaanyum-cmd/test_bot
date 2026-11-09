import logging
import random
import re
import time

import discord
from discord.ext import commands, tasks

from perms import admin_only
from usage import send_usage
from utils import fmt, parse_amount, reply

log = logging.getLogger(__name__)
DURATION_RE = re.compile(r"^(\d+)\s*(s|m|h|d|сек|мин|ц|цаг|өдөр)?$", re.I)
UNITS = {"s": 1, "сек": 1, "m": 60, "мин": 60, "h": 3600, "ц": 3600, "цаг": 3600, "d": 86400, "өдөр": 86400}


def parse_duration(text: str) -> int | None:
    m = DURATION_RE.match(text.strip())
    if not m:
        return None
    n = int(m.group(1))
    unit = (m.group(2) or "m").lower()
    secs = n * UNITS[unit]
    return secs if 30 <= secs <= 14 * 86400 else None


def giveaway_embed(prize: int, winners: int, ends_at: float, host_id: int, ended: bool = False, result: str = ""):
    embed = discord.Embed(
        title="🎉 GIVEAWAY" if not ended else "🎉 GIVEAWAY ДУУСЛАА",
        color=0xF59E0B if not ended else 0x6B7280,
    )
    embed.add_field(name="🏆 Шагнал", value=f"**{fmt(prize)}**" + (f" (×{winners} хүн тус бүр хуваана)" if winners > 1 else ""), inline=False)
    embed.add_field(name="⏰ Дуусах", value=f"<t:{int(ends_at)}:R>", inline=True)
    embed.add_field(name="🏛️ Эх үүсвэр", value="Татварын сан", inline=True)
    embed.add_field(name="👑 Зохион байгуулагч", value=f"<@{host_id}>", inline=True)
    if result:
        embed.add_field(name="🎊 Ялагчид", value=result, inline=False)
    return embed


class JoinView(discord.ui.View):
    """Persistent: ботыг дахин асаасан ч товч ажиллана."""

    def __init__(self, bot=None):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Оролцох", emoji="🎉", style=discord.ButtonStyle.success, custom_id="giveaway:join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = interaction.client.db
        g = await db.giveaway_by_message(interaction.message.id)
        if g is None:
            await interaction.response.send_message("❌ Энэ giveaway дууссан байна.", ephemeral=True)
            return
        if await db.get_profile(interaction.user.id) is None:
            await interaction.response.send_message(
                "❌ Эхлээд `qprofile` гэж бичиж character-аа үүсгэнэ үү.", ephemeral=True
            )
            return
        if await db.enter_giveaway(g["id"], interaction.user.id):
            n = len(await db.giveaway_entries(g["id"]))
            await interaction.response.send_message(f"✅ Оролцлоо! Одоогоор **{n}** хүн оролцож байна.", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ Та аль хэдийн оролцсон байна.", ephemeral=True)


class Giveaway(commands.Cog):
    """Татварын сангаас giveaway зохиох."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(JoinView(self.bot))
        self.loop.start()

    async def cog_unload(self):
        self.loop.cancel()

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.command(name="treasury", aliases=["tax", "sang"])
    async def treasury(self, ctx: commands.Context):
        """Цугласан татварын сангийн үлдэгдэл"""
        amount = await self.bot.db.treasury_get()
        embed = discord.Embed(
            title="🏛️ Татварын сан",
            description=f"Үлдэгдэл: **{fmt(amount)}**\nӨдөр бүрийн орлогоос (daily, work) **10%** татвар авдаг.",
            color=0x0EA5E9,
        )
        embed.set_footer(text="Сангаас owner giveaway зохион явуулна")
        await reply(ctx, embed=embed)

    @commands.command(name="giveaway", aliases=["gw"])
    @admin_only()
    async def giveaway(self, ctx: commands.Context, amount: str, duration: str, winners: str = "1"):
        """Owner/Admin: татварын сангаас giveaway: giveaway <дүн|all> <30m|2h|1d> [ялагчийн тоо]"""
        pool = await self.bot.db.treasury_get()
        amt = parse_amount(amount, pool)
        secs = parse_duration(duration)
        if amt is None or secs is None or not winners.isdigit() or not (1 <= int(winners) <= 20):
            await send_usage(ctx)
            return
        n = int(winners)
        if amt < n:
            await reply(ctx, "❌ Шагнал ялагчийн тооноос бага байна.")
            return
        ends = time.time() + secs
        gid = await self.bot.db.create_giveaway(ctx.guild.id, ctx.channel.id, amt, n, ends, ctx.author.id)
        if gid is None:
            await reply(ctx, f"❌ Татварын санд хангалттай мөнгө алга. Сан: **{fmt(pool)}**")
            return
        try:
            msg = await ctx.send(embed=giveaway_embed(amt, n, ends, ctx.author.id), view=JoinView(self.bot))
        except discord.HTTPException:
            await self.bot.db.finish_giveaway(gid)
            await self.bot.db.treasury_add(amt)
            await reply(ctx, "❌ Giveaway мессеж илгээж чадсангүй. Мөнгө санд буцлаа.")
            return
        await self.bot.db.set_giveaway_message(gid, msg.id)

    @tasks.loop(seconds=20)
    async def loop(self):
        try:
            for g in await self.bot.db.due_giveaways(time.time()):
                await self.finish(g)
        except Exception:
            log.exception("Giveaway шалгалт алдаатай")

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    async def finish(self, g):
        db = self.bot.db
        if not await db.finish_giveaway(g["id"]):
            return
        entries = await db.giveaway_entries(g["id"])
        winners = random.sample(entries, min(g["winners"], len(entries))) if entries else []
        if winners:
            share = g["prize"] // len(winners)
            for uid in winners:
                await db.add_balance(uid, share)
            left = g["prize"] - share * len(winners)
            if left:
                await db.treasury_add(left)
            result = "\n".join(f"<@{u}> — **{fmt(share)}**" for u in winners)
        else:
            await db.treasury_add(g["prize"])
            result = "Оролцогч байгаагүй тул мөнгө санд буцлаа."

        channel = self.bot.get_channel(g["channel_id"])
        if channel is None:
            return
        try:
            msg = await channel.fetch_message(g["message_id"])
            view = JoinView(self.bot)
            view.join.disabled = True
            await msg.edit(embed=giveaway_embed(g["prize"], g["winners"], g["ends_at"], g["host_id"], True, result), view=view)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
        try:
            mentions = " ".join(f"<@{u}>" for u in winners)
            await channel.send(
                f"🎊 **Giveaway дууслаа!** {mentions or ''}\n{result}",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
