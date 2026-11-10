import random

import aiohttp
import discord
from discord.ext import commands

from usage import send_usage
from utils import reply

# (нэр, nekos.best төрөл, үйлдлийн текст, өөртөө хийвэл текст, өнгө, emoji)
EMOTES = [
    ("hug", "hug", "{a} {b}-г тэвэрлээ", "{a} өөрийгөө тэвэрлээ", 0xF472B6, "🤗"),
    ("kiss", "kiss", "{a} {b}-г үнсэв", "{a} агаарыг үнсэв", 0xEC4899, "😘"),
    ("slap", "slap", "{a} {b}-г алгадлаа", "{a} өөрийгөө алгадлаа", 0xEF4444, "👋"),
    ("pat", "pat", "{a} {b}-ийн толгойг илэв", "{a} өөрийнхөө толгойг илэв", 0xFBBF24, "🫳"),
    ("cuddle", "cuddle", "{a} {b}-тэй наалдан тэврэв", "{a} дэрийг тэврэв", 0xF472B6, "🥰"),
    ("poke", "poke", "{a} {b}-г хуруугаараа гэв", "{a} өөрийгөө гэв", 0x60A5FA, "👉"),
    ("bite", "bite", "{a} {b}-г зууллаа", "{a} өөрийгөө зууллаа", 0xEF4444, "😬"),
    ("punch", "punch", "{a} {b}-г цохилоо", "{a} агаарыг цохилоо", 0xDC2626, "👊"),
    ("highfive", "highfive", "{a} {b}-тэй алгаа ташив", "{a} өөртэйгөө алгаа ташив", 0x22C55E, "🙌"),
    ("cry", "cry", "{a} {b}-ийн өмнө уйллаа", "{a} уйллаа", 0x3B82F6, "😭"),
    ("dance", "dance", "{a} {b}-тэй бүжиглэв", "{a} бүжиглэв", 0xA855F7, "💃"),
    ("laugh", "laugh", "{a} {b}-ийг хараад инээв", "{a} инээв", 0xFBBF24, "😂"),
    ("blush", "blush", "{a} {b}-ийн өмнө улайв", "{a} улайв", 0xF472B6, "😊"),
    ("kick", "kick", "{a} {b}-г өшиглөв", "{a} өөрийгөө өшиглөв", 0xDC2626, "🦵"),
    ("tickle", "tickle", "{a} {b}-г гижигдэв", "{a} өөрийгөө гижигдэв", 0xFBBF24, "🤭"),
    ("feed", "feed", "{a} {b}-г хооллов", "{a} өөрийгөө хооллов", 0x22C55E, "🍙"),
    ("handhold", "handhold", "{a} {b}-ийн гараас барилаа", "{a} гараа атгав", 0xF472B6, "🤝"),
    ("wink", "wink", "{a} {b} руу нүд ирмэв", "{a} нүд ирмэв", 0xEC4899, "😉"),
    # 🔞 насанд хүрэгчдийн сэдэвтэй (ил биш), зөвхөн NSFW (age-restricted) суваг дээр
    ("flirt", "wink", "{a} {b}-тэй сээтэглэв 😏", "{a} толинд өөртэйгөө сээтэглэв", 0xEC4899, "😏", True),
    ("lick", None, "{a} {b}-г долоов 😛", "{a} уруулаа долоов", 0xEC4899, "😛", True),
    ("seduce", "smug", "{a} {b}-г уруу татав 😈", "{a} өөртөө итгэлтэй инээмсэглэв", 0xBE185D, "😈", True),
    ("spank", None, "{a} {b}-г зөөлхөн алгадав 🍑", "{a} өөрийгөө алгадав", 0xBE185D, "🍑", True),
]

API = "https://nekos.best/api/v2/{}"
FALLBACK = {}  # төрөл -> бэлэн GIF холбоос (хүсвэл энд нэмж болно)


async def fetch_gif(kind: str | None) -> str | None:
    if not kind:
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(API.format(kind)) as r:
                if r.status == 200:
                    data = await r.json()
                    return data["results"][0]["url"]
    except Exception:
        pass
    return FALLBACK.get(kind)


def make_emote(name, kind, text_other, text_self, color, emoji, nsfw=False):
    @commands.command(name=name, help=f"{emoji} {name}")
    async def emote(ctx: commands.Context, member: discord.Member = None):
        if member is None:
            await send_usage(ctx)
            return
        if nsfw and not getattr(ctx.channel, "is_nsfw", lambda: False)():
            await reply(ctx, "🔞 Энэ эможи зөвхөн NSFW (насанд хүрэгчдийн) суваг дээр ажиллана.")
            return
        a, b = ctx.author.mention, member.mention
        text = text_self if member.id == ctx.author.id else text_other
        embed = discord.Embed(description=f"{emoji} **{text.format(a=a, b=b)}**", color=color)
        gif = await fetch_gif(kind)
        if gif:
            embed.set_image(url=gif)
        await ctx.send(embed=embed)

    return emote


async def setup(bot):
    for e in EMOTES:
        bot.add_command(make_emote(*e))
