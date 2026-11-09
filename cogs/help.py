import discord
from discord.ext import commands

from ui import OwnerView, nav_button
from utils import reply

# (нэр, emoji, [(команд, тайлбар)])
PAGES = [
    ("Үндсэн", "💰", [
        ("bal [@хүн]", "Хэтэвч, банк, хөрөнгө харах"),
        ("daily", "Өдрийн цалин авах"),
        ("dep / with <дүн|all>", "Банкинд хийх / авах (шимтгэл 200₮)"),
        ("give <@хүн> <дүн>", "Мөнгө шилжүүлэх"),
        ("lb [bank|wallet|total]", "Тэргүүлэгчид"),
    ]),
    ("Ажил", "💼", [
        ("work", "Ажил хийж цалин авах (1 цаг)"),
        ("jobs", "Ажлын жагсаалт"),
        ("workout", "Дасгал хийж хүч нэмэх (ажлын орлого өснө)"),
    ]),
    ("Дэлгүүр", "🛍️", [
        ("shop [ангилал]", "Дэлгүүр: food, digital, home, house, clothes"),
        ("buy <ID> [тоо]", "Бараа авах"),
        ("inv [use <ID> [тоо]]", "Цүнх харах / ашиглах"),
        ("sell <ID|all> [тоо]", "Зарах (70%)"),
        ("gift <ID> <@хүн> [тоо]", "Бэлэглэх"),
        ("eat <ID> [тоо]", "Хоол идэх"),
        ("petshop / buypet <ID>", "Тэжээвэр амьтан"),
    ]),
    ("Байшин", "🏠", [
        ("house", "Байшингаа харах"),
        ("house shop", "Байшингийн жагсаалт"),
        ("house buy <ID>", "Байшин авах"),
        ("house <өрөө>", "Өрөөний эд зүйлс"),
        ("house <өрөө> use|unuse <ID>", "Эд зүйл байрлуулах / авах"),
        ("safe [buy|put|take]", "Сейф: мөнгө, эд зүйл хадгалах"),
    ]),
    ("Гэмт хэрэг", "🥷", [
        ("steal [1-5]", "Байшин руу хулгай хийх"),
        ("rob <@хүн>", "Дээрэмдэх"),
        ("hack <@хүн>", "Банк руу хакердах (компьютер хэрэгтэй)"),
        ("block", "Бамбай: 2.5 цаг хамгаалалт"),
        ("bail", "Барьцаа төлж шоронгоос гарах"),
    ]),
    ("Казино", "🎰", [
        ("cf <дүн> [сүүл|тоо]", "Зоос шидэх"),
        ("dice <дүн> <1-6>", "Шоо"),
        ("slots <дүн>", "Слот (s)"),
        ("mf <дүн>", "Minefield"),
        ("duel <@хүн> <дүн>", "Чулуу-хайч-даавуу дуэль"),
        ("draw <@хүн> <дүн>", "Quick Draw"),
        ("", "Бүгд банкнаас, 1,000₮ – 250,000₮"),
    ]),
    ("Character", "👤", [
        ("profile [@хүн]", "2D character профайл"),
        ("wear <ID|off>", "Хувцас өмсөх"),
        ("marry <@хүн>", "Гэрлэх санал (Бөгж хэрэгтэй)"),
        ("divorce", "Гэрлэлт цуцлах"),
        ("date", "Хосоороо болзох (6 цаг)"),
    ]),
    ("Хайрцаг & Уурхай", "🎁", [
        ("box / box buy <box|case|chest>", "Хайрцгийн дэлгүүр"),
        ("open <box|case|chest> [тоо]", "Хайрцаг нээх"),
        ("mine", "Алтны уурхай (40%)"),
        ("coach", "Хувийн дасгалжуулагч (хүч +3, 200,000₮)"),
        ("inv use revive", "Revive Active: үхсэн хүнийг амилуулах"),
    ]),
    ("Татвар & Giveaway", "🏛️", [
        ("treasury", "Татварын сан (орлогын 10%)"),
        ("giveaway <дүн> <хугацаа> [тоо]", "Owner/Admin: сангаас giveaway"),
        ("phone / utas", "Утасны апп-ууд"),
        ("info, ping", "Серверийн мэдээлэл"),
        ("admin", "Admin слайд (Owner/Admin)"),
    ]),
    ("Эможи", "🎭", [
        ("slap, hug, kiss, pat, cuddle", "+ <@хүн>"),
        ("poke, bite, punch, highfive", "+ <@хүн>"),
        ("cry, dance, laugh, blush, wink", "+ <@хүн>"),
        ("peck, handhold, feed, tickle, smug", "+ <@хүн>"),
        ("kick, baka, pout, wave, stare, nom, yeet", "+ <@хүн>"),
        ("flirt, tease, seduce, lovebite, sparkle", "🔞 Зөвхөн NSFW суваг"),
    ]),
]


def page_embed(i: int, p: str) -> discord.Embed:
    name, emoji, cmds = PAGES[i]
    lines = [f"`{p}{c}` — {d}" if c else f"*{d}*" for c, d in cmds]
    embed = discord.Embed(title=f"{emoji} {name}", description="\n".join(lines), color=0x3B82F6)
    embed.set_footer(text=f"Хуудас {i + 1}/{len(PAGES)} · <> заавал, [] заавал биш · {p} эсвэл ! угтвар")
    return embed


class HelpView(OwnerView):
    def __init__(self, owner_id: int, prefix: str, page: int = 0):
        super().__init__(owner_id, timeout=120)
        self.prefix, self.page = prefix, page
        self.select = discord.ui.Select(
            placeholder="Ангилал сонгох",
            options=[
                discord.SelectOption(label=n, value=str(i), emoji=e) for i, (n, e, _) in enumerate(PAGES)
            ],
        )
        self.select.callback = self.on_select
        self.prev = nav_button("◀", self.on_prev)
        self.nxt = nav_button("▶", self.on_next)
        self.add_item(self.select)
        self.add_item(self.prev)
        self.add_item(self.nxt)
        self._sync()

    def _sync(self):
        self.prev.disabled = self.page <= 0
        self.nxt.disabled = self.page >= len(PAGES) - 1

    async def _show(self, interaction):
        self._sync()
        await interaction.response.edit_message(embed=page_embed(self.page, self.prefix), view=self)

    async def on_select(self, interaction):
        self.page = int(self.select.values[0])
        await self._show(interaction)

    async def on_prev(self, interaction):
        self.page = max(0, self.page - 1)
        await self._show(interaction)

    async def on_next(self, interaction):
        self.page = min(len(PAGES) - 1, self.page + 1)
        await self._show(interaction)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h", "commands"])
    async def help(self, ctx: commands.Context):
        """Тусламжийн цэс"""
        view = HelpView(ctx.author.id, ctx.clean_prefix)
        view.message = await reply(ctx, embed=page_embed(0, ctx.clean_prefix), view=view)


async def setup(bot):
    await bot.add_cog(Help(bot))
