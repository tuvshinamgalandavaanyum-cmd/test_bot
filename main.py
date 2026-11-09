import logging
import os
import random

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
    "cogs.economy",
    "cogs.work",
    "cogs.shop",
    "cogs.house",
    "cogs.crime",
    "cogs.casino",
    "cogs.fun",
    "cogs.hunger",
    "cogs.profile",
    "cogs.social",
    "cogs.loot",
    "cogs.giveaway",
    "cogs.admin",
    "cogs.phone",
    "cogs.help",
)

# Бүртгэлгүй хүн ашиглаж болох командууд
OPEN_COMMANDS = {"profile", "help", "info", "ping", "admin"}
# Үхсэн хүн ашиглаж болох командууд
DEAD_COMMANDS = {"inv", "bal", "help", "profile", "phone", "info", "ping", "admin", "shop", "buy", "eat"}
# Эдгээр командаас 0.1% магадлалтай Revive Active олдоно
REVIVE_DROP_COMMANDS = {"cf", "dice", "slots", "mf", "duel", "draw", "work", "steal", "rob", "hack", "mine"}
REVIVE_DROP_CHANCE = 0.001


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
        self.before_invoke(self.before_invoke_hook)
        self.after_invoke(self.after_invoke_hook)
        self.add_check(self.global_check)

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

    async def global_check(self, ctx: commands.Context) -> bool:
        """1) Бүртгэл (character) үүсгээгүй хүнд бот ажиллахгүй. 2) Үхсэн хүнд ихэнх команд хаалттай."""
        if ctx.guild is None or ctx.command is None:
            return True
        name = (ctx.command.root_parent or ctx.command).name
        if name in OPEN_COMMANDS:
            return True
        if await self.db.get_profile(ctx.author.id) is None:
            from cogs.profile import send_register_prompt
            await send_register_prompt(self, ctx)
            return False
        if name not in DEAD_COMMANDS:
            user = await self.db.get_user(ctx.author.id)
            if user["dead"]:
                await ctx.reply(
                    f"💀 Та нас барсан байна. Амилахын тулд **Revive Active** хэрэгтэй "
                    f"(`{ctx.clean_prefix}inv use revive`). Найз бэлэглэж болно, эсвэл админ амилуулна.",
                    mention_author=False,
                )
                return False
        return True

    async def after_invoke_hook(self, ctx: commands.Context):
        if ctx.command is None or ctx.command_failed or ctx.guild is None:
            return
        name = (ctx.command.root_parent or ctx.command).name
        if name in REVIVE_DROP_COMMANDS and random.random() < REVIVE_DROP_CHANCE:
            await self.db.add_item(ctx.author.id, "revive", 1)
            try:
                await ctx.send(
                    f"💖 {ctx.author.mention} **ГАЙХАМШИГТАЙ!** Тоглож байгаад **Revive Active** (0.1%) олчихлоо! "
                    f"`{ctx.clean_prefix}inv`-ээс хараарай."
                )
            except discord.HTTPException:
                pass

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
