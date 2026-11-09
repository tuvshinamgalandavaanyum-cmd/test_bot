from discord.ext import commands


async def _is_admin(ctx: commands.Context) -> bool:
    """Bot Owner эсвэл серверийн Administrator эрхтэй хүн."""
    if ctx.guild is None:
        return False
    if await ctx.bot.is_owner(ctx.author):
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    await ctx.reply("❌ Энэ команд зөвхөн **Owner / Admin**-д зориулагдсан.", mention_author=False)
    return False


def admin_only():
    return commands.check(_is_admin)
