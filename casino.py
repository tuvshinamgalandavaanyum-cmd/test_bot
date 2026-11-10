import asyncio
import random
from math import comb

import discord
from discord.ext import commands

from ui import OwnerView, nav_button
from usage import send_usage
from utils import MAX_BET, MIN_BET, fmt, jailed, parse_amount, reply

GREEN, RED, GREY, GOLD = 0x22C55E, 0xEF4444, 0x6B7280, 0xF59E0B
DUEL_FEE = 0.05  # дуэль, quick draw: хожсон хүн нийт банкийн 95%-ийг авна

# ---------- слот ----------
# (emoji, жин, 3 ижил бол үржвэр, 2 ижил бол үржвэр)
SLOT_SYMBOLS = [
    ("🍒", 30, 5, 0.8),
    ("🍋", 25, 8, 0.8),
    ("🍇", 20, 12, 1.0),
    ("🔔", 12, 25, 2.0),
    ("💎", 8, 60, 3.0),
    ("7️⃣", 5, 150, 5.0),
]
SLOT_TOTAL = sum(s[1] for s in SLOT_SYMBOLS)


def slot_multiplier(reels: list[str]) -> float:
    for emoji, _, triple, pair in SLOT_SYMBOLS:
        count = reels.count(emoji)
        if count == 3:
            return triple
        if count == 2:
            return pair
    return 0.0


def slot_rtp() -> float:
    """Онолын буцаалт (RTP) - шалгахад ашиглана."""
    total = 0.0
    for a, wa, *_ in SLOT_SYMBOLS:
        for b, wb, *_ in SLOT_SYMBOLS:
            for c, wc, *_ in SLOT_SYMBOLS:
                p = (wa / SLOT_TOTAL) * (wb / SLOT_TOTAL) * (wc / SLOT_TOTAL)
                total += p * slot_multiplier([a, b, c])
    return total


# ---------- minefield ----------
MINE_TILES = 20
MINE_COUNT = 4
MINE_MAX_PICKS = 10
MINE_EDGE = 0.96


def mine_multiplier(picks: int) -> float:
    if picks <= 0:
        return 1.0
    return MINE_EDGE * comb(MINE_TILES, picks) / comb(MINE_TILES - MINE_COUNT, picks)


def result_embed(title: str, desc: str, bet: int, payout: int, bank: int) -> discord.Embed:
    net = payout - bet
    color = GREEN if net > 0 else (GREY if net == 0 else RED)
    embed = discord.Embed(title=title, description=desc, color=color)
    embed.add_field(name="💸 Бооцоо", value=fmt(bet), inline=True)
    if net > 0:
        embed.add_field(name="🎉 Хожил", value=f"```diff\n+{net:,} ₮\n```", inline=True)
    elif net == 0:
        embed.add_field(name="➖ Үр дүн", value="Тэнцлээ", inline=True)
    else:
        embed.add_field(name="💀 Алдагдал", value=f"```diff\n-{-net:,} ₮\n```", inline=True)
    embed.add_field(name="🏛️ Банк", value=fmt(bank), inline=True)
    return embed


# ================= minefield view =================
class MineView(OwnerView):
    def __init__(self, cog, ctx, bet: int):
        super().__init__(ctx.author.id, timeout=120)
        self.cog, self.ctx, self.bet = cog, ctx, bet
        self.mines = set(random.sample(range(MINE_TILES), MINE_COUNT))
        self.revealed: set[int] = set()
        self.done = False
        self.tiles = []
        for i in range(MINE_TILES):
            b = discord.ui.Button(label="❓", style=discord.ButtonStyle.secondary, row=i // 5)
            b.callback = self._tile_cb(i)
            self.tiles.append(b)
            self.add_item(b)
        self.cash_btn = discord.ui.Button(
            label="💰 Мөнгө авах", style=discord.ButtonStyle.success, row=4, disabled=True
        )
        self.cash_btn.callback = self.on_cash
        self.add_item(self.cash_btn)

    def _tile_cb(self, i: int):
        async def cb(interaction):
            await self.pick(interaction, i)

        return cb

    def current_payout(self) -> int:
        return int(self.bet * mine_multiplier(len(self.revealed)))

    def embed(self, note: str = "") -> discord.Embed:
        k = len(self.revealed)
        embed = discord.Embed(
            title="💣 Minefield",
            description=(
                f"{MINE_TILES} талбайн {MINE_COUNT}-т нь бөмбөг байна. Аюулгүй талбай нээгээд хэзээ ч мөнгөө аваарай!\n{note}"
            ),
            color=GOLD,
        )
        embed.add_field(name="💸 Бооцоо", value=fmt(self.bet), inline=True)
        embed.add_field(name="💎 Нээсэн", value=f"{k}/{MINE_MAX_PICKS}", inline=True)
        embed.add_field(
            name="📈 Одоогийн хожил",
            value=f"×{mine_multiplier(k):.2f} = {fmt(self.current_payout())}" if k else "—",
            inline=True,
        )
        return embed

    def _reveal_mines(self):
        for i, b in enumerate(self.tiles):
            if i in self.mines:
                b.label = "💣"
                b.style = discord.ButtonStyle.danger
            b.disabled = True
        self.cash_btn.disabled = True

    async def pick(self, interaction, i: int):
        if self.done:
            await interaction.response.defer()
            return
        if i in self.mines:
            self.done = True
            self._reveal_mines()
            self.stop()
            bank = (await self.cog.bot.db.get_user(self.ctx.author.id))["bank"]
            embed = result_embed("💥 Бөмбөгт тулав!", "Таны бооцоо алдагдлаа.", self.bet, 0, bank)
            await interaction.response.edit_message(embed=embed, view=self)
            return
        self.revealed.add(i)
        tile = self.tiles[i]
        tile.label = "💎"
        tile.style = discord.ButtonStyle.success
        tile.disabled = True
        self.cash_btn.disabled = False
        if len(self.revealed) >= MINE_MAX_PICKS:
            await self.cash_out(interaction, auto=True)
            return
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def cash_out(self, interaction, auto: bool = False):
        if self.done:
            await interaction.response.defer()
            return
        self.done = True
        payout = self.current_payout()
        await self.cog.bot.db.bank_add(self.ctx.author.id, payout)
        self._reveal_mines()
        self.stop()
        bank = (await self.cog.bot.db.get_user(self.ctx.author.id))["bank"]
        desc = "Дээд хэмжээнд хүрч автоматаар авлаа!" if auto else "Та мөнгөө аваад гарлаа."
        embed = result_embed("💰 Минфилд дууслаа", desc, self.bet, payout, bank)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_cash(self, interaction):
        await self.cash_out(interaction)

    async def on_timeout(self):
        if self.done:
            return
        self.done = True
        payout = self.current_payout() if self.revealed else self.bet
        await self.cog.bot.db.bank_add(self.ctx.author.id, payout)
        self._reveal_mines()
        if self.message is not None:
            try:
                bank = (await self.cog.bot.db.get_user(self.ctx.author.id))["bank"]
                note = "Хугацаа дууслаа, хожлыг автоматаар авлаа." if self.revealed else "Хугацаа дууслаа, бооцоо буцаагдлаа."
                await self.message.edit(
                    embed=result_embed("⌛ Хугацаа дууслаа", note, self.bet, payout, bank), view=self
                )
            except Exception:
                pass


# ================= дуэль / quick draw =================
class ChallengeView(discord.ui.View):
    """Уриалга: зөвшөөрвөл хоёр тоглогчийн банкнаас бооцоо хасаад тоглоом эхэлнэ."""

    def __init__(self, cog, ctx, challenger, target, bet: int, starter):
        super().__init__(timeout=60)
        self.cog, self.ctx = cog, ctx
        self.challenger, self.target, self.bet = challenger, target, bet
        self.starter = starter
        self.resolved = False
        self.message = None
        self.add_item(nav_button("✅ Зөвшөөрөх", self.on_accept, discord.ButtonStyle.success))
        self.add_item(nav_button("❌ Татгалзах", self.on_decline, discord.ButtonStyle.danger))

    async def interaction_check(self, interaction) -> bool:
        if interaction.user.id not in (self.challenger.id, self.target.id):
            await interaction.response.send_message("❌ Энэ уриалга танд хамаагүй.", ephemeral=True)
            return False
        return True

    async def on_accept(self, interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("⏳ Зөвхөн уригдсан хүн зөвшөөрнө.", ephemeral=True)
            return
        if self.resolved:
            await interaction.response.defer()
            return
        self.resolved = True
        self.stop()
        ok = await self.cog.bot.db.bank_spend_two(self.challenger.id, self.target.id, self.bet)
        if not ok:
            embed = discord.Embed(
                title="❌ Тоглоом цуцлагдлаа",
                description=f"Хэн нэгний банкны дансанд {fmt(self.bet)} хүрэлцэхгүй байна.",
                color=RED,
            )
            for c in self.children:
                c.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            return
        await self.starter(interaction)

    async def on_decline(self, interaction):
        if self.resolved:
            await interaction.response.defer()
            return
        self.resolved = True
        self.stop()
        for c in self.children:
            c.disabled = True
        who = "татгалзлаа" if interaction.user.id == self.target.id else "цуцаллаа"
        embed = discord.Embed(
            title="❌ Тоглоом цуцлагдлаа",
            description=f"{interaction.user.mention} уриалгыг {who}.",
            color=GREY,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.resolved:
            return
        self.resolved = True
        for c in self.children:
            c.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(
                    embed=discord.Embed(title="⌛ Уриалга хугацаа хэтэрлээ", color=GREY), view=self
                )
            except Exception:
                pass


RPS = {"rock": ("✊", "Чулуу"), "paper": ("✋", "Даавуу"), "scissors": ("✌️", "Хайч")}
RPS_BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}


class DuelView(discord.ui.View):
    """3 раунд (2 хожсон нь ялна) чулуу-хайч-даавуу."""

    WIN_ROUNDS = 2
    MAX_ROUNDS = 10

    def __init__(self, cog, a, b, bet: int):
        super().__init__(timeout=90)
        self.cog, self.a, self.b, self.bet = cog, a, b, bet
        self.score = {a.id: 0, b.id: 0}
        self.choices: dict[int, str] = {}
        self.rounds_played = 0
        self.finished = False
        self.message = None
        self.log: list[str] = []
        for key, (emoji, name) in RPS.items():
            btn = discord.ui.Button(label=name, emoji=emoji, style=discord.ButtonStyle.primary)
            btn.callback = self._cb(key)
            self.add_item(btn)

    @property
    def payout(self) -> int:
        return int(self.bet * 2 * (1 - DUEL_FEE))

    def _cb(self, key: str):
        async def cb(interaction):
            await self.choose(interaction, key)

        return cb

    async def interaction_check(self, interaction) -> bool:
        if interaction.user.id not in (self.a.id, self.b.id):
            await interaction.response.send_message("❌ Та энэ дуэлийн тоглогч биш.", ephemeral=True)
            return False
        return True

    def embed(self, footer: str = "") -> discord.Embed:
        embed = discord.Embed(
            title="⚔️ Дуэль: чулуу-хайч-даавуу",
            description=f"{self.a.mention} 🆚 {self.b.mention}\n🏆 Хожигч авах: **{fmt(self.payout)}**",
            color=GOLD,
        )
        embed.add_field(name=self.a.display_name, value=f"**{self.score[self.a.id]}**", inline=True)
        embed.add_field(name=self.b.display_name, value=f"**{self.score[self.b.id]}**", inline=True)
        if self.log:
            embed.add_field(name="Раундууд", value="\n".join(self.log[-6:]), inline=False)
        embed.set_footer(
            text=footer or f"Раунд {self.rounds_played + 1} · 2 раунд хожсон нь ялна · тэнцвэл дахин"
        )
        return embed

    async def choose(self, interaction, key: str):
        if self.finished:
            await interaction.response.defer()
            return
        uid = interaction.user.id
        if uid in self.choices:
            await interaction.response.send_message("Та аль хэдийн сонгосон. Хүлээнэ үү.", ephemeral=True)
            return
        self.choices[uid] = key
        if len(self.choices) < 2:
            emoji, name = RPS[key]
            await interaction.response.send_message(
                f"Та {emoji} **{name}** сонголоо. Эсрэг тоглогчийг хүлээж байна...", ephemeral=True
            )
            return

        ca, cb = self.choices[self.a.id], self.choices[self.b.id]
        self.choices = {}
        self.rounds_played += 1
        ea, eb = RPS[ca][0], RPS[cb][0]
        if ca == cb:
            self.log.append(f"{ea} 🆚 {eb} — тэнцлээ")
        elif RPS_BEATS[ca] == cb:
            self.score[self.a.id] += 1
            self.log.append(f"{ea} 🆚 {eb} — {self.a.display_name} хожлоо")
        else:
            self.score[self.b.id] += 1
            self.log.append(f"{ea} 🆚 {eb} — {self.b.display_name} хожлоо")

        sa, sb = self.score[self.a.id], self.score[self.b.id]
        if max(sa, sb) >= self.WIN_ROUNDS or self.rounds_played >= self.MAX_ROUNDS:
            await self.finish(interaction)
        else:
            await interaction.response.edit_message(embed=self.embed(), view=self)

    async def finish(self, interaction):
        self.finished = True
        sa, sb = self.score[self.a.id], self.score[self.b.id]
        db = self.cog.bot.db
        if sa == sb:
            await db.bank_add(self.a.id, self.bet)
            await db.bank_add(self.b.id, self.bet)
            footer = "Тэнцлээ. Бооцоо хоёр талд буцаагдлаа."
        else:
            winner = self.a if sa > sb else self.b
            await db.bank_add(winner.id, self.payout)
            footer = f"🏆 {winner.display_name} ялж {fmt(self.payout)} авлаа!"
        for c in self.children:
            c.disabled = True
        self.stop()
        await interaction.response.edit_message(embed=self.embed(footer), view=self)

    async def on_timeout(self):
        if self.finished:
            return
        self.finished = True
        db = self.cog.bot.db
        await db.bank_add(self.a.id, self.bet)
        await db.bank_add(self.b.id, self.bet)
        for c in self.children:
            c.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(embed=self.embed("⌛ Хугацаа дууслаа. Бооцоо буцаагдлаа."), view=self)
            except Exception:
                pass


class DrawView(discord.ui.View):
    """GO! гарсны дараа хамгийн түрүүнд дарсан хүн ялна."""

    def __init__(self, cog, a, b, bet: int):
        super().__init__(timeout=30)
        self.cog, self.a, self.b, self.bet = cog, a, b, bet
        self.ready = False
        self.finished = False
        self.message = None
        self.task = None
        self.btn = discord.ui.Button(label="🔫 Бэлдээрэй...", style=discord.ButtonStyle.secondary, disabled=True)
        self.btn.callback = self.on_shoot
        self.add_item(self.btn)

    @property
    def payout(self) -> int:
        return int(self.bet * 2 * (1 - DUEL_FEE))

    async def interaction_check(self, interaction) -> bool:
        if interaction.user.id not in (self.a.id, self.b.id):
            await interaction.response.send_message("❌ Та энэ тоглоомын тоглогч биш.", ephemeral=True)
            return False
        return True

    def start_embed(self) -> discord.Embed:
        return discord.Embed(
            title="🔫 Quick Draw",
            description=(
                f"{self.a.mention} 🆚 {self.b.mention}\n🏆 Хожигч авах: **{fmt(self.payout)}**\n\n"
                "**Бэлдээрэй...** GO! гарахыг хүлээгээд хамгийн түрүүнд буудна уу!"
            ),
            color=GOLD,
        )

    def start(self):
        self.task = asyncio.create_task(self._go())

    async def _go(self):
        await asyncio.sleep(random.uniform(2, 6))
        if self.finished:
            return
        self.ready = True
        self.btn.disabled = False
        self.btn.label = "🔫 БУУД!"
        self.btn.style = discord.ButtonStyle.danger
        embed = discord.Embed(title="🔫 GO!!!", description="**ОДОО БУУД!**", color=RED)
        if self.message is not None:
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass

    async def on_shoot(self, interaction):
        if self.finished or not self.ready:
            await interaction.response.defer()
            return
        self.finished = True
        if self.task is not None:
            self.task.cancel()
        winner = interaction.user
        await self.cog.bot.db.bank_add(winner.id, self.payout)
        self.btn.disabled = True
        self.btn.label = "Дууслаа"
        self.stop()
        embed = discord.Embed(
            title="🏆 Quick Draw дууслаа",
            description=f"{winner.mention} хамгийн хурдан буудлаа!\nХожил: **{fmt(self.payout)}**",
            color=GREEN,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.finished:
            return
        self.finished = True
        if self.task is not None:
            self.task.cancel()
        db = self.cog.bot.db
        await db.bank_add(self.a.id, self.bet)
        await db.bank_add(self.b.id, self.bet)
        self.btn.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(
                    embed=discord.Embed(
                        title="⌛ Хэн ч буудсангүй", description="Бооцоо хоёр талд буцаагдлаа.", color=GREY
                    ),
                    view=self,
                )
            except Exception:
                pass


class Casino(commands.Cog):
    """Азын тоглоомууд. Зөвхөн банкны данснаас тоглоно."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    async def _take_bet(self, ctx, amount: str | None, spend: bool = True):
        """Бооцоог шалгаж банкнаас хасна. Амжилтгүй бол None."""
        user = await self.bot.db.get_user(ctx.author.id)
        if await jailed(ctx, user):
            return None
        bet = parse_amount(amount, min(user["bank"], MAX_BET))
        if bet is None:
            await send_usage(ctx)
            return None
        if bet < MIN_BET:
            await reply(ctx, f"❌ Хамгийн бага бооцоо {fmt(MIN_BET)}.")
            return None
        if bet > MAX_BET:
            await reply(ctx, f"❌ Дээд бооцоо {fmt(MAX_BET)}.")
            return None
        if user["bank"] < bet:
            await reply(
                ctx,
                f"❌ Банкны дансанд мөнгө хүрэлцэхгүй байна. Казино зөвхөн банкнаас тоглоно: `{ctx.clean_prefix}dep`",
            )
            return None
        if spend and not await self.bot.db.bank_spend(ctx.author.id, bet):
            await reply(ctx, "❌ Банкны дансанд мөнгө хүрэлцэхгүй байна.")
            return None
        return bet

    async def _bank(self, uid: int) -> int:
        return (await self.bot.db.get_user(uid))["bank"]

    # ---------- coinflip ----------
    @commands.command(name="cf", aliases=["coinflip"])
    async def coinflip(self, ctx: commands.Context, amount: str, side: str = None):
        """Зоос шидэх: cf <дүн> [сүүл | тоо]"""
        sides = {
            "сүүл": "сүүл", "suul": "сүүл", "tail": "сүүл", "tails": "сүүл", "t": "сүүл",
            "тоо": "тоо", "too": "тоо", "head": "тоо", "heads": "тоо", "h": "тоо",
        }
        pick = None
        if side is not None:
            pick = sides.get(side.lower())
            if pick is None:
                await send_usage(ctx)
                return
        bet = await self._take_bet(ctx, amount)
        if bet is None:
            return
        pick = pick or random.choice(["сүүл", "тоо"])
        win = random.random() < 0.49
        other = "тоо" if pick == "сүүл" else "сүүл"
        landed = pick if win else other
        payout = bet * 2 if win else 0
        if payout:
            await self.bot.db.bank_add(ctx.author.id, payout)
        desc = f"🪙 Зоос шидлээ...\nТаны сонголт: **{pick}** · Унасан тал: **{landed}**"
        embed = result_embed("🪙 Coinflip", desc, bet, payout, await self._bank(ctx.author.id))
        await reply(ctx, embed=embed)

    # ---------- dice ----------
    @commands.command(name="dice")
    async def dice(self, ctx: commands.Context, amount: str, guess: str):
        """Шоо хаях: dice <дүн> <1-6>"""
        if not guess.isdigit() or not 1 <= int(guess) <= 6:
            await send_usage(ctx)
            return
        bet = await self._take_bet(ctx, amount)
        if bet is None:
            return
        roll = random.randint(1, 6)
        payout = int(bet * 5.7) if roll == int(guess) else 0
        if payout:
            await self.bot.db.bank_add(ctx.author.id, payout)
        desc = f"🎲 Шоо хаялаа... **{roll}** буулаа!\nТаны таамаг: **{guess}**"
        embed = result_embed("🎲 Dice", desc, bet, payout, await self._bank(ctx.author.id))
        await reply(ctx, embed=embed)

    # ---------- slots ----------
    @commands.command(name="slots", aliases=["s"])
    async def slots(self, ctx: commands.Context, amount: str):
        """Слот машин: slots <дүн>"""
        bet = await self._take_bet(ctx, amount)
        if bet is None:
            return
        reels = random.choices(
            [s[0] for s in SLOT_SYMBOLS], weights=[s[1] for s in SLOT_SYMBOLS], k=3
        )
        mult = slot_multiplier(reels)
        payout = int(bet * mult)
        if payout:
            await self.bot.db.bank_add(ctx.author.id, payout)
        desc = f"🎰 **│ {reels[0]} │ {reels[1]} │ {reels[2]} │**"
        if mult:
            desc += f"\nҮржвэр: ×{mult:g}"
        embed = result_embed("🎰 Slots", desc, bet, payout, await self._bank(ctx.author.id))
        await reply(ctx, embed=embed)

    # ---------- minefield ----------
    @commands.command(name="mf", aliases=["minefield"])
    async def minefield(self, ctx: commands.Context, amount: str):
        """Minefield: mf <дүн>"""
        bet = await self._take_bet(ctx, amount)
        if bet is None:
            return
        view = MineView(self, ctx, bet)
        view.message = await reply(ctx, embed=view.embed(), view=view)

    # ---------- уриалгат тоглоом ----------
    async def _challenge(self, ctx, member: discord.Member, amount: str, title: str, make_starter):
        if member.id == ctx.author.id or member.bot:
            await reply(ctx, "❌ Энэ хүнийг уриалах боломжгүй.")
            return
        bet = await self._take_bet(ctx, amount, spend=False)
        if bet is None:
            return
        opp = await self.bot.db.get_user(member.id)
        if opp["bank"] < bet:
            await reply(ctx, f"❌ {member.mention}-ийн банкны дансанд {fmt(bet)} алга.")
            return
        embed = discord.Embed(
            title=title,
            description=(
                f"{member.mention}, {ctx.author.mention} таныг уриалж байна!\n"
                f"💸 Бооцоо: **{fmt(bet)}** (хоёр талын банкнаас)"
            ),
            color=GOLD,
        )
        view = ChallengeView(self, ctx, ctx.author, member, bet, None)
        view.starter = make_starter(view)
        view.message = await reply(ctx, embed=embed, view=view)

    @commands.command(name="duel", aliases=["d"])
    async def duel(self, ctx: commands.Context, member: discord.Member, amount: str):
        """Дуэль: duel @хүн <дүн>"""

        def make_starter(challenge: ChallengeView):
            async def starter(interaction):
                game = DuelView(self, challenge.challenger, challenge.target, challenge.bet)
                await interaction.response.edit_message(embed=game.embed(), view=game)
                game.message = interaction.message

            return starter

        await self._challenge(ctx, member, amount, "⚔️ Дуэлийн уриалга", make_starter)

    @commands.command(name="draw", aliases=["quickdraw"])
    async def quickdraw(self, ctx: commands.Context, member: discord.Member, amount: str):
        """Quick Draw: draw @хүн <дүн>"""

        def make_starter(challenge: ChallengeView):
            async def starter(interaction):
                game = DrawView(self, challenge.challenger, challenge.target, challenge.bet)
                await interaction.response.edit_message(embed=game.start_embed(), view=game)
                game.message = interaction.message
                game.start()

            return starter

        await self._challenge(ctx, member, amount, "🔫 Quick Draw уриалга", make_starter)


async def setup(bot: commands.Bot):
    await bot.add_cog(Casino(bot))
