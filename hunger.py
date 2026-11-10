import logging
import time

import discord
from discord.ext import commands, tasks

from utils import (
    DEATH_SECONDS,
    HUNGER_SECONDS,
    STARVE_GAP,
    STARVE_NOTICE_GAP,
    STARVE_RATE,
    fmt,
)

log = logging.getLogger(__name__)


class Hunger(commands.Cog):
    """3 хоног хоолгүй бол 2 цаг тутам хэтэвчний 2.5% хасагдана. 7 хоног хоолгүй бол үхнэ."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.check.start()

    async def cog_unload(self):
        self.check.cancel()

    async def _say(self, uid: int, channel_id: int, text: str):
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if channel is not None:
            try:
                await channel.send(text, allowed_mentions=discord.AllowedMentions(users=True))
                return
            except (discord.Forbidden, discord.HTTPException):
                pass
        try:
            user = self.bot.get_user(uid) or await self.bot.fetch_user(uid)
            await user.send(text)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

    @tasks.loop(minutes=10)
    async def check(self):
        try:
            db = self.bot.db
            now = time.time()
            p = getattr(self.bot, "main_prefix", "!")

            # 1) 7 хоног хоолгүй → үхнэ
            for row in await db.dying_users(now, DEATH_SECONDS):
                uid = row["user_id"]
                await db.set_dead(uid, True, now)
                await self._say(
                    uid,
                    row["last_channel"],
                    f"💀 <@{uid}> **7 хоног хоол идээгүй тул үхлээ!**\n"
                    f"Амилуулахад `Revive Active` хэрэгтэй: `{p}inv use revive` (эсвэл админаас хүс).",
                )

            # 2) 3-7 хоног хоолгүй → 2 цаг тутам 2.5% хасна
            for row in await db.starving_users(now, HUNGER_SECONDS, DEATH_SECONDS, STARVE_GAP):
                uid = row["user_id"]
                taken = await db.apply_starvation(uid, now, STARVE_RATE)
                if now - row["hunger_notified"] >= STARVE_NOTICE_GAP:
                    await db.mark_notified(uid, now)
                    await self._say(
                        uid,
                        row["last_channel"],
                        f"🍞 <@{uid}> **Та өлсөж байна!** 2 цаг тутам хэтэвчний 2.5% хасагдана "
                        f"(одоо **{fmt(taken)}**).\n"
                        f"`{p}shop food` дээрээс хоол аваад `{p}eat <ID>` гэж хооллоорой. "
                        f"7 хоног хоолгүй бол үхнэ! 💀",
                    )
        except Exception:
            log.exception("Өлсөлтийн шалгалт алдаатай")

    @check.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Hunger(bot))
