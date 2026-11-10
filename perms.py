async def is_admin(bot, user) -> bool:
    """Ботын эзэн эсвэл `admin op`-оор томилогдсон хүн."""
    if await bot.is_owner(user):
        return True
    return await bot.db.is_admin(user.id)


def parse_duration(text: str) -> int | None:
    """'30s', '10m', '2h', '1d' → секунд. Буруу бол None."""
    t = text.strip().lower()
    if len(t) < 2 or not t[:-1].isdigit():
        return None
    n = int(t[:-1])
    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(t[-1])
    if mult is None or n <= 0:
        return None
    return n * mult
