import logging
import os
import time

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import Database

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mongolbot")

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIXES = [p.strip() for p in os.getenv("PREFIX", "q,!").split(",") if p.strip()] or ["!"]

EXTENSIONS = (
    "cogs.profile",
    "cogs.economy",
    "cogs.work",
    "cogs.shop",
    "cogs.house",
    "cogs.adventure",
    "cogs.romance",
    "cogs.crime",
    "cogs.casino",
    "cogs.fun",
    "cogs.hunger",
    "cogs.giveaway",
    "cogs.admin",
    "cogs.help",
)

# үхсэн дүр зөвхөн эдгээр командыг ашиглана
DEAD_OK = {"inv", "bal", "profile", "help", "info", "revive", "pool", "register"}


def get_prefix(bot, message: discord.Message):
    """Том жижиг үсэг ялгахгүй угтвар (Qwork, qwork, !work бүгд ажиллана)."""
    content = message.content.lower()
    for p in PREFIXES:
        if content.startswith(p.lower()):
            return message.content[: len(p)]
    return commands.when_mentioned(bot, message)


class MongolBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Developer Portal дээр заавал идэвхжүүлнэ
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            case_insensitive=True,
            strip_after_prefix=True,
            help_command=None,
        )
        self.db = Database()
        self.main_prefix = PREFIXES[0]
        self.started_at = time.time()
        self.before_invoke(self.before_invoke_hook)
        self.add_check(self.global_gate)

    async def global_gate(self, ctx: commands.Context) -> bool:
        """Бүртгүүлээгүй бол бот ажиллахгүй. Үхсэн бол цөөн команд л ажиллана."""
        if ctx.guild is None or ctx.command is None or ctx.command.name == "register":
            return True
        user = await self.db.get_user(ctx.author.id)
        if not user["registered"]:
            cog = self.get_cog("Profile")
            if cog is not None:
                await cog.send_onboarding(ctx)
            return False
        if user["dead"] and ctx.command.name not in DEAD_OK:
            p = ctx.clean_prefix
            await ctx.reply(
                f"💀 Та үхсэн байна! `{p}inv use revive` ({'Revive Active'} хэрэгтэй) эсвэл админаас амилуулахыг хүс.",
                mention_author=False,
            )
            return False
        return True

    async def setup_hook(self):
        await self.db.connect()
        for ext in EXTENSIONS:
            await self.load_extension(ext)

    async def before_invoke_hook(self, ctx: commands.Context):
        if ctx.guild is not None:
            try:
                await self.db.set_last_channel(ctx.author.id, ctx.channel.id)
            except Exception:
                log.exception("last_channel хадгалахад алдаа")

    async def on_ready(self):
        print(f"Бот нэвтэрлээ: {self.user} (ID: {self.user.id})")
        print(f"Угтвар: {', '.join(PREFIXES)}")

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
            return
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            from usage import send_usage
            await send_usage(ctx)
        else:
            log.error("Командын алдаа", exc_info=error)

    async def close(self):
        await self.db.close()
        await super().close()


def main():
    if not TOKEN:
        raise SystemExit(".env файлд DISCORD_TOKEN оруулна уу.")
    MongolBot().run(TOKEN)


if __name__ == "__main__":
    main()
