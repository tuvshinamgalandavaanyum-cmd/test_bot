import time

import discord

HUNGER_DAYS = 3
HUNGER_SECONDS = HUNGER_DAYS * 24 * 3600  # 3 хоног хоолгүй бол өлсөнө
DEAD_DAYS = 7
DEAD_SECONDS = DEAD_DAYS * 24 * 3600  # 7 хоног хоолгүй бол үхнэ (Revive Active хэрэгтэй)
TAX_RATE = 0.10  # өдрийн орлогоос 10% татвар
MAX_STRENGTH = 30
STARVE_RATE = 0.025  # өлссөн үед өдөрт хэтэвчний 2.5% хасагдана
STARVE_GAP = 2 * 3600  # өлссөн үед 2 цаг тутам торгуулна
BANK_FEE = 200  # банк, шилжүүлгийн шимтгэл
JAIL_SECONDS = 12 * 3600
PROTECT_SECONDS = int(2.5 * 3600)
MIN_BET = 1_000
MAX_BET = 250_000


def tax_split(gross: int) -> tuple[int, int]:
    """Орлогыг (цэвэр, татвар) болгон хуваана."""
    tax = int(gross * TAX_RATE)
    return gross - tax, tax


def fmt(amount: int) -> str:
    """Мөнгөн дүнг 50,000₮ хэлбэрээр харуулна."""
    return f"{int(amount):,}₮"


def fmt_duration(seconds: float) -> str:
    """Секундийг '1 цаг 5 мин' гэх мэт хэлбэрт оруулна."""
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} өдөр")
    if hours:
        parts.append(f"{hours} цаг")
    if minutes:
        parts.append(f"{minutes} мин")
    if not parts:
        parts.append(f"{secs} сек")
    return " ".join(parts)


def fmt_short(seconds: float) -> str:
    """Секундийг '11ц 59м' хэлбэрт оруулна."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    if h:
        return f"{h}ц {m}м"
    if m:
        return f"{m}м"
    return f"{rem}сек"


def hunger_left(last_fed: float, now: float) -> float:
    """Өлсөх хүртэл үлдсэн секунд. 0 буюу сөрөг бол өлссөн."""
    return HUNGER_SECONDS - (now - last_fed)


def is_hungry(last_fed: float, now: float) -> bool:
    return hunger_left(last_fed, now) <= 0


def shop_day(now: float | None = None) -> int:
    """Дэлгүүрийн нөөц Улаанбаатарын шөнө дундад шинэчлэгдэнэ (UTC+8)."""
    now = time.time() if now is None else now
    return int((now + 8 * 3600) // 86400)


def parse_amount(text: str | None, maximum: int) -> int | None:
    """'5000', '50k', '1.5m', 'all' зэргийг тоо болгоно. Буруу бол None."""
    if text is None:
        return maximum
    s = text.strip().lower().replace(",", "").replace("_", "").replace("₮", "")
    if s in ("all", "max", "бүгд", "bugd"):
        return maximum
    mult = 1
    if s.endswith("k"):
        mult, s = 1_000, s[:-1]
    elif s.endswith("m"):
        mult, s = 1_000_000, s[:-1]
    try:
        value = int(float(s) * mult)
    except ValueError:
        return None
    return value if value > 0 else None


def parse_qty(text: str | None, default: int = 1, maximum: int = 1000) -> int | None:
    """Бүхэл тоо. Буруу эсвэл 1-ээс бага бол None."""
    if text is None:
        return default
    if not text.strip().isdigit():
        return None
    n = int(text.strip())
    return n if 1 <= n <= maximum else None


async def reply(ctx, *args, **kwargs):
    """Мессежид хариулна (тухайн хүнийг ping хийхгүй)."""
    kwargs.setdefault("mention_author", False)
    return await ctx.reply(*args, **kwargs)


def hint_use(p: str) -> str:
    return f"💡 Ашиглах: {p}inv use <ID> [тоо] | Бэлэглэх: {p}gift <ID> @user"


def hint_shop(p: str) -> str:
    return f"Бараа авах: {p}buy <ID> | Цүнхээ харах: {p}inv"


async def jailed(ctx, user) -> bool:
    """Шоронд байвал мэдэгдээд True буцаана."""
    left = user["jail_until"] - time.time()
    if left <= 0:
        return False
    p = ctx.clean_prefix
    embed = discord.Embed(
        title="⛓️ Та шоронд байна",
        description=(
            f"Үлдсэн хугацаа: **{fmt_short(left)}**\n"
            f"Батлан даалтад гарах: `{p}bail`"
        ),
        color=0x6B7280,
    )
    await reply(ctx, embed=embed)
    return True
