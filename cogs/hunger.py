import logging
import time

import discord
from discord.ext import commands, tasks

from utils import DEAD_SECONDS, HUNGER_DAYS, HUNGER_SECONDS, STARVE_GAP, STARVE_RATE, fmt

log = logging.getLogger(__name__)


class Hunger(commands.Cog):
    """3 хоног хоолгүй бол 2 цаг тутам хэтэвчний 2.5%-ийг хасна. 7 хоног хоолгүй бол үхнэ."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.check.start()

    async def cog_unload(self):
        self.check.cancel()

    async def _notify(self, row, text: str):
        uid = row["user_id"]
        channel = self.bot.get_channel(row["last_channel"]) if row["last_channel"] else None
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
            now = time.time()
            p = getattr(self.bot, "main_prefix", "!")
            db = self.bot.db

            # 1) 7 хоног хоолгүй -> үхнэ
            for row in await db.dying_users(now, DEAD_SECONDS):
                await db.set_dead(row["user_id"], True)
                await self._notify(
                    row,
                    f"💀 <@{row['user_id']}> **Та хоолгүйгээс болж нас барлаа!**\n"
                    f"Амилахын тулд **Revive Active** хэрэгтэй (найз бэлэглэх эсвэл админ амилуулна).",
                )

            # 2) 3 хоног хоолгүй -> 2 цаг тутам 2.5% торгууль
            for row in await db.starving_users(now, HUNGER_SECONDS, STARVE_GAP):
                uid = row["user_id"]
                taken = await db.apply_starvation(uid, now, STARVE_RATE)
                await self._notify(
                    row,
                    f"🍞 <@{uid}> **Та {HUNGER_DAYS} хоногоос дээш хоолгүй байна!** "
                    f"Хэтэвчнээс чинь 2.5% (**{fmt(taken)}**) хасагдлаа. (2 цаг тутам давтагдана)\n"
                    f"`{p}shop food` дээрээс хоол аваад `{p}eat <ID>` гэж хооллоорой. "
                    f"7 хоног хүртэл хооллохгүй бол үхнэ!",
                )
        except Exception:
            log.exception("Өлсөлтийн шалгалт алдаатай")

    @check.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Hunger(bot))
