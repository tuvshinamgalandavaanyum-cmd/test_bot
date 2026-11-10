import logging
import random
import time

import discord
from discord.ext import commands, tasks

from perms import is_admin, parse_duration
from usage import send_usage
from utils import fmt, fmt_duration, parse_amount, reply

log = logging.getLogger(__name__)


class GiveawayView(discord.ui.View):
    def __init__(self, cog, gid: int):
        super().__init__(timeout=None)
        self.cog, self.gid = cog, gid
        btn = discord.ui.Button(
            label="🎉 Оролцох", style=discord.ButtonStyle.success, custom_id=f"gw:{gid}"
        )
        btn.callback = self.on_join
        self.add_item(btn)

    async def on_join(self, interaction):
        db = self.cog.bot.db
        row = await db.get_giveaway(self.gid)
        if row is None or row["status"] != "active":
            await interaction.response.send_message("⌛ Giveaway дууссан байна.", ephemeral=True)
            return
        user = await db.get_user(interaction.user.id)
        if not user["registered"]:
            await interaction.response.send_message("❌ Эхлээд бүртгүүлнэ үү (командаар бичнэ).", ephemeral=True)
            return
        if await db.enter_giveaway(self.gid, interaction.user.id):
            count = len(await db.giveaway_entries(self.gid))
            await interaction.response.send_message(f"✅ Оролцлоо! Нийт оролцогч: {count}", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ Та аль хэдийн оролцсон байна.", ephemeral=True)


def giveaway_embed(row, entries: int = 0, ended: bool = False, winners_text: str = "") -> discord.Embed:
    embed = discord.Embed(
        title="🎉 GIVEAWAY!",
        description=f"💰 Шагнал: **{fmt(row['prize'])}**\n🏆 Ялагч: **{row['winners']}**\n"
        f"👤 Зохион байгуулагч: <@{row['host_id']}>",
        color=0x6B7280 if ended else 0xF59E0B,
    )
    if ended:
        embed.add_field(name="🎊 Ялагчид", value=winners_text or "Оролцогч байгаагүй", inline=False)
    else:
        embed.add_field(name="⏰ Дуусах", value=f"<t:{int(row['ends_at'])}:R>", inline=True)
        embed.add_field(name="👥 Оролцогч", value=str(entries), inline=True)
    return embed


class Giveaway(commands.Cog):
    """Татварын сангаас Giveaway зохион байгуулах."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.loop.start()

    async def cog_unload(self):
        self.loop.cancel()

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    async def restore_views(self):
        for row in await self.bot.db.active_giveaways():
            if row["message_id"]:
                self.bot.add_view(GiveawayView(self, row["id"]), message_id=row["message_id"])

    @tasks.loop(seconds=20)
    async def loop(self):
        try:
            now = time.time()
            for row in await self.bot.db.active_giveaways():
                if row["ends_at"] <= now:
                    await self.finish(row["id"])
        except Exception:
            log.exception("Giveaway шалгахад алдаа")

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await self.restore_views()

    async def finish(self, gid: int):
        db = self.bot.db
        if not await db.close_giveaway(gid):
            return
        row = await db.get_giveaway(gid)
        entries = []
        for uid in await db.giveaway_entries(gid):
            if (await db.get_user(uid))["registered"]:
                entries.append(uid)
        winners = random.sample(entries, min(row["winners"], len(entries))) if entries else []
        if winners:
            share = row["prize"] // len(winners)
            for uid in winners:
                await db.add_balance(uid, share)
            text = "\n".join(f"<@{u}> — {fmt(share)}" for u in winners)
        else:
            await db.add_setting("pool", row["prize"])  # оролцогчгүй бол санд буцаана
            text = ""
        channel = self.bot.get_channel(row["channel_id"])
        if channel is None:
            return
        try:
            msg = await channel.fetch_message(row["message_id"])
            await msg.edit(embed=giveaway_embed(row, ended=True, winners_text=text), view=None)
        except Exception:
            pass
        try:
            if winners:
                await channel.send(
                    "🎊 Giveaway дууслаа! Ялагчид: " + " ".join(f"<@{u}>" for u in winners) + f"\n{text}",
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
            else:
                await channel.send("😢 Giveaway-д хэн ч оролцсонгүй. Шагнал санд буцлаа.")
        except Exception:
            pass

    @commands.command(name="giveaway", aliases=["gw"])
    async def giveaway(self, ctx: commands.Context, amount: str, duration: str, winners: str = "1"):
        """Giveaway: giveaway <дүн | pool> <хугацаа 10m/2h/1d> [ялагчийн тоо] (админ)"""
        if not await is_admin(self.bot, ctx.author):
            await reply(ctx, "🚫 Энэ командыг зөвхөн админ ашиглана.")
            return
        pool = await self.bot.db.get_setting("pool")
        prize = parse_amount(amount, pool)
        secs = parse_duration(duration)
        if prize is None or secs is None or not winners.isdigit() or not 1 <= int(winners) <= 20:
            await send_usage(ctx)
            return
        if secs < 10 or secs > 14 * 86400:
            await reply(ctx, "❌ Хугацаа 10 секундээс 14 хоногийн хооронд байх ёстой.")
            return
        if prize > pool or not await self.bot.db.take_pool(prize):
            await reply(ctx, f"❌ Татварын сан хүрэлцэхгүй. Сан: **{fmt(pool)}**")
            return
        n = int(winners)
        ends = time.time() + secs
        gid = await self.bot.db.create_giveaway(ctx.guild.id, ctx.channel.id, ctx.author.id, prize, n, ends)
        row = await self.bot.db.get_giveaway(gid)
        view = GiveawayView(self, gid)
        msg = await ctx.send(embed=giveaway_embed(row), view=view)
        await self.bot.db.set_giveaway_message(gid, msg.id)

    @commands.command(name="pool", aliases=["treasury", "tax"])
    async def pool(self, ctx: commands.Context):
        """Татварын сангийн үлдэгдэл"""
        pool = await self.bot.db.get_setting("pool")
        embed = discord.Embed(
            title="🏛️ Татварын сан",
            description=f"Цалин, өдрийн цалингаас 10% татвар авч, энд хуримтлуулна.\n\n💰 Үлдэгдэл: **{fmt(pool)}**",
            color=0x3B82F6,
        )
        embed.set_footer(text="Админ энэ сангаас giveaway зохион байгуулна")
        await reply(ctx, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
