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
    ("wink", "wink", "{a} {b}-д нүд ирмэв", "{a} нүд ирмэв", 0xFBBF24, "😉"),
    ("peck", "peck", "{a} {b}-ийг хацар дээр нь үнсэв", "{a} агаарт үнсэв", 0xEC4899, "😚"),
    ("handhold", "handhold", "{a} {b}-ийн гараас атгалаа", "{a} гараа атгав", 0xF472B6, "🤝"),
    ("feed", "feed", "{a} {b}-д хоол асууж идүүллээ", "{a} өөрийгөө хооллов", 0xF59E0B, "🍙"),
    ("tickle", "tickle", "{a} {b}-г кили кили хийв", "{a} өөрийгөө кили кили хийв", 0xFBBF24, "🤭"),
    ("smug", "smug", "{a} {b}-ийн өмнө бардам инээмсэглэв", "{a} бардам инээмсэглэв", 0xA855F7, "😏"),
    ("kick", "kick", "{a} {b}-г өшиглөв", "{a} агаарыг өшиглөв", 0xDC2626, "🦵"),
    ("baka", "baka", "{a} {b}-г тэнэг гэж хэллээ", "{a} өөрийгөө тэнэг гэв", 0xEF4444, "💢"),
    ("pout", "pout", "{a} {b}-д уурлаж аман тагнай хийв", "{a} уурлав", 0xF472B6, "😤"),
    ("wave", "wave", "{a} {b}-д гараа даллав", "{a} гараа даллав", 0x22C55E, "👋"),
    ("stare", "stare", "{a} {b}-г ширтэв", "{a} хоосон ширтэв", 0x6B7280, "👀"),
    ("nom", "nom", "{a} {b}-г хазаж амсав", "{a} амттай юм идэв", 0xF59E0B, "😋"),
    ("yeet", "yeet", "{a} {b}-г шидэв", "{a} өөрийгөө шидэв", 0xEF4444, "🚀"),
]

API = "https://nekos.best/api/v2/{}"
FALLBACK = {}  # төрөл -> бэлэн GIF холбоос (хүсвэл энд нэмж болно)


async def fetch_gif(kind: str) -> str | None:
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


def make_emote(name, kind, text_other, text_self, color, emoji):
    @commands.command(name=name, help=f"{emoji} {name}")
    async def emote(ctx: commands.Context, member: discord.Member = None):
        if member is None:
            await send_usage(ctx)
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
