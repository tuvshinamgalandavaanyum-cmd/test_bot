import asyncio
import time

import aiosqlite

DB_PATH = "bot.db"
START_BALANCE = 10_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    balance         INTEGER NOT NULL DEFAULT 10000,
    bank            INTEGER NOT NULL DEFAULT 0,
    job_id          INTEGER,
    work_count      INTEGER NOT NULL DEFAULT 0,
    last_work       REAL    NOT NULL DEFAULT 0,
    last_fed        REAL    NOT NULL DEFAULT 0,
    created_at      REAL    NOT NULL DEFAULT 0,
    last_daily      REAL    NOT NULL DEFAULT 0,
    daily_streak    INTEGER NOT NULL DEFAULT 0,
    last_burglary   REAL    NOT NULL DEFAULT 0,
    last_workout    REAL    NOT NULL DEFAULT 0,
    strength        INTEGER NOT NULL DEFAULT 0,
    pet             TEXT,
    hunger_notified REAL    NOT NULL DEFAULT 0,
    house           TEXT,
    safe_level      INTEGER NOT NULL DEFAULT 0,
    safe_money      INTEGER NOT NULL DEFAULT 0,
    jail_until      REAL    NOT NULL DEFAULT 0,
    jail_bail       INTEGER NOT NULL DEFAULT 0,
    protect_until   REAL    NOT NULL DEFAULT 0,
    last_rob        REAL    NOT NULL DEFAULT 0,
    last_hack       REAL    NOT NULL DEFAULT 0,
    last_channel    INTEGER NOT NULL DEFAULT 0,
    last_starve     REAL    NOT NULL DEFAULT 0,
    registered      INTEGER NOT NULL DEFAULT 0,
    gender          TEXT,
    age             INTEGER NOT NULL DEFAULT 0,
    country         TEXT,
    skin            TEXT,
    dead            INTEGER NOT NULL DEFAULT 0,
    spouse          INTEGER NOT NULL DEFAULT 0,
    love            INTEGER NOT NULL DEFAULT 0,
    last_date       REAL    NOT NULL DEFAULT 0,
    luck_until      REAL    NOT NULL DEFAULT 0,
    boost_until     REAL    NOT NULL DEFAULT 0,
    last_mine       REAL    NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS inventory (
    user_id  INTEGER NOT NULL,
    item_key TEXT    NOT NULL,
    qty      INTEGER NOT NULL,
    PRIMARY KEY (user_id, item_key)
);
CREATE TABLE IF NOT EXISTS house_items (
    user_id  INTEGER NOT NULL,
    room     TEXT    NOT NULL,
    item_key TEXT    NOT NULL,
    qty      INTEGER NOT NULL,
    PRIMARY KEY (user_id, room, item_key)
);
CREATE TABLE IF NOT EXISTS safe_items (
    user_id  INTEGER NOT NULL,
    item_key TEXT    NOT NULL,
    qty      INTEGER NOT NULL,
    PRIMARY KEY (user_id, item_key)
);
CREATE TABLE IF NOT EXISTS equipped (
    user_id  INTEGER NOT NULL,
    slot     TEXT    NOT NULL,
    item_key TEXT    NOT NULL,
    PRIMARY KEY (user_id, slot)
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS giveaways (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL DEFAULT 0,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL DEFAULT 0,
    host_id    INTEGER NOT NULL,
    prize      INTEGER NOT NULL,
    winners    INTEGER NOT NULL DEFAULT 1,
    ends_at    REAL    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS giveaway_entries (
    giveaway_id INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    PRIMARY KEY (giveaway_id, user_id)
);
CREATE TABLE IF NOT EXISTS shop_stock (
    item_key TEXT PRIMARY KEY,
    day      INTEGER NOT NULL,
    sold     INTEGER NOT NULL
);
"""

# Өмнөх хувилбарын bot.db байвал дутуу баганыг нэмнэ
MIGRATIONS = {
    "bank": "INTEGER NOT NULL DEFAULT 0",
    "last_daily": "REAL NOT NULL DEFAULT 0",
    "daily_streak": "INTEGER NOT NULL DEFAULT 0",
    "last_burglary": "REAL NOT NULL DEFAULT 0",
    "last_workout": "REAL NOT NULL DEFAULT 0",
    "strength": "INTEGER NOT NULL DEFAULT 0",
    "pet": "TEXT",
    "hunger_notified": "REAL NOT NULL DEFAULT 0",
    "house": "TEXT",
    "safe_level": "INTEGER NOT NULL DEFAULT 0",
    "safe_money": "INTEGER NOT NULL DEFAULT 0",
    "jail_until": "REAL NOT NULL DEFAULT 0",
    "jail_bail": "INTEGER NOT NULL DEFAULT 0",
    "protect_until": "REAL NOT NULL DEFAULT 0",
    "last_rob": "REAL NOT NULL DEFAULT 0",
    "last_hack": "REAL NOT NULL DEFAULT 0",
    "last_channel": "INTEGER NOT NULL DEFAULT 0",
    "last_starve": "REAL NOT NULL DEFAULT 0",
    "registered": "INTEGER NOT NULL DEFAULT 0",
    "gender": "TEXT",
    "age": "INTEGER NOT NULL DEFAULT 0",
    "country": "TEXT",
    "skin": "TEXT",
    "dead": "INTEGER NOT NULL DEFAULT 0",
    "spouse": "INTEGER NOT NULL DEFAULT 0",
    "love": "INTEGER NOT NULL DEFAULT 0",
    "last_date": "REAL NOT NULL DEFAULT 0",
    "luck_until": "REAL NOT NULL DEFAULT 0",
    "boost_until": "REAL NOT NULL DEFAULT 0",
    "last_mine": "REAL NOT NULL DEFAULT 0",
}

COOLDOWN_COLUMNS = {"last_burglary", "last_rob", "last_hack", "last_mine", "last_date"}
TOP_EXPR = {
    "bank": "bank",
    "wallet": "balance",
    "total": "balance + bank + safe_money",
}


class Database:
    """SQLite өгөгдлийн сан. Бичих үйлдэл бүрийг lock-оор хамгаална."""

    def __init__(self, path: str = DB_PATH):
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        self.lock = asyncio.Lock()

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.executescript(SCHEMA)
        cur = await self.conn.execute("PRAGMA table_info(users)")
        existing = {r["name"] for r in await cur.fetchall()}
        for col, decl in MIGRATIONS.items():
            if col not in existing:
                await self.conn.execute(f"ALTER TABLE users ADD COLUMN {col} {decl}")
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def _ensure(self, user_id: int):
        """Lock авсан үед хэрэглэгч байхгүй бол үүсгэнэ."""
        now = time.time()
        await self.conn.execute(
            "INSERT OR IGNORE INTO users (user_id, balance, last_fed, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, START_BALANCE, now, now),
        )

    # ---------- хэрэглэгч ----------
    async def get_user(self, user_id: int) -> aiosqlite.Row:
        """Хэрэглэгч байхгүй бол шинээр үүсгээд буцаана."""
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.commit()
            cur = await self.conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            return await cur.fetchone()

    async def set_last_channel(self, user_id: int, channel_id: int):
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.execute(
                "UPDATE users SET last_channel = ? WHERE user_id = ?",
                (channel_id, user_id),
            )
            await self.conn.commit()

    async def count_users(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) AS n FROM users")
        return (await cur.fetchone())["n"]

    async def top(self, metric: str, limit: int, offset: int = 0):
        expr = TOP_EXPR[metric]
        cur = await self.conn.execute(
            f"SELECT user_id, {expr} AS value FROM users "
            f"ORDER BY value DESC, user_id LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cur.fetchall()

    # ---------- хэтэвч ----------
    async def add_balance(self, user_id: int, amount: int):
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, user_id),
            )
            await self.conn.commit()

    async def set_balance(self, user_id: int, amount: int):
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.execute(
                "UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id)
            )
            await self.conn.commit()

    async def spend(self, user_id: int, amount: int) -> bool:
        """Хэтэвчинд хүрэлцэж байвал хасаад True, үгүй бол False."""
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance - ? "
                "WHERE user_id = ? AND balance >= ?",
                (amount, user_id, amount),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def fine(self, user_id: int, amount: int) -> int:
        """Торгууль: хэтэвчинд байгаа хэмжээгээр хасаж, бодитоор хассан дүнг буцаана."""
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                "SELECT balance FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cur.fetchone()
            taken = max(0, min(row["balance"], amount))
            await self.conn.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (taken, user_id),
            )
            await self.conn.commit()
            return taken

    async def pay_to(self, from_id: int, to_id: int, amount: int) -> int:
        """from-ийн хэтэвчнээс to-ийн хэтэвч рүү хэдэн ₮ чадахаараа шилжүүлж, бодит дүнг буцаана."""
        async with self.lock:
            await self._ensure(from_id)
            await self._ensure(to_id)
            cur = await self.conn.execute(
                "SELECT balance FROM users WHERE user_id = ?", (from_id,)
            )
            row = await cur.fetchone()
            taken = max(0, min(row["balance"], amount))
            await self.conn.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (taken, from_id),
            )
            await self.conn.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (taken, to_id),
            )
            await self.conn.commit()
            return taken

    async def transfer(self, from_id: int, to_id: int, amount: int, fee: int = 0) -> bool:
        """Илгээгчийн хэтэвчнээс amount + fee хасаж, хүлээн авагчид amount өгнө."""
        async with self.lock:
            await self._ensure(from_id)
            await self._ensure(to_id)
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance - ? "
                "WHERE user_id = ? AND balance >= ?",
                (amount + fee, from_id, amount + fee),
            )
            if cur.rowcount != 1:
                await self.conn.rollback()
                return False
            await self.conn.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, to_id),
            )
            await self.conn.commit()
            return True

    # ---------- банк ----------
    async def deposit(self, user_id: int, amount: int, fee: int = 0) -> bool:
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance - ?, bank = bank + ? "
                "WHERE user_id = ? AND balance >= ?",
                (amount + fee, amount, user_id, amount + fee),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def withdraw(self, user_id: int, amount: int, fee: int = 0) -> bool:
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                "UPDATE users SET bank = bank - ?, balance = balance + ? "
                "WHERE user_id = ? AND bank >= ?",
                (amount + fee, amount, user_id, amount + fee),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def bank_spend(self, user_id: int, amount: int) -> bool:
        """Казинод: банкнаас бооцоо хасна."""
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                "UPDATE users SET bank = bank - ? WHERE user_id = ? AND bank >= ?",
                (amount, user_id, amount),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def bank_add(self, user_id: int, amount: int):
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.execute(
                "UPDATE users SET bank = bank + ? WHERE user_id = ?", (amount, user_id)
            )
            await self.conn.commit()

    async def bank_spend_two(self, a: int, b: int, amount: int) -> bool:
        """Хоёр тоглогчийн банкнаас зэрэг бооцоо хасна. Нэг нь хүрэхгүй бол юу ч хасахгүй."""
        async with self.lock:
            await self._ensure(a)
            await self._ensure(b)
            for uid in (a, b):
                cur = await self.conn.execute(
                    "UPDATE users SET bank = bank - ? WHERE user_id = ? AND bank >= ?",
                    (amount, uid, amount),
                )
                if cur.rowcount != 1:
                    await self.conn.rollback()
                    return False
            await self.conn.commit()
            return True

    # ---------- өдрийн шагнал ----------
    async def claim_daily(
        self, user_id: int, now: float, reward: int, streak: int, prev_last: float
    ) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance + ?, last_daily = ?, "
                "daily_streak = ? WHERE user_id = ? AND last_daily = ?",
                (reward, now, streak, user_id, prev_last),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    # ---------- ажил, дасгал ----------
    async def complete_work(
        self, user_id: int, pay: int, now: float, cooldown: float
    ) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance + ?, work_count = work_count + 1, "
                "last_work = ? WHERE user_id = ? AND ? - last_work >= ?",
                (pay, now, user_id, now, cooldown),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def complete_workout(
        self, user_id: int, now: float, cooldown: float, max_strength: int
    ) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE users SET strength = strength + 1, last_workout = ? "
                "WHERE user_id = ? AND strength < ? AND ? - last_workout >= ?",
                (now, user_id, max_strength, now, cooldown),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def add_strength(self, user_id: int, amount: int, max_strength: int):
        async with self.lock:
            await self.conn.execute(
                "UPDATE users SET strength = MIN(?, strength + ?) WHERE user_id = ?",
                (max_strength, amount, user_id),
            )
            await self.conn.commit()

    # ---------- хүлээлтийн хугацаа (хулгай, дээрэм, хакер) ----------
    async def start_cooldown(
        self, user_id: int, column: str, now: float, cooldown: float
    ) -> bool:
        """Хүлээх хугацаа дууссан бол эхлүүлж цагийг тэмдэглэнэ."""
        assert column in COOLDOWN_COLUMNS
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                f"UPDATE users SET {column} = ? WHERE user_id = ? AND ? - {column} >= ?",
                (now, user_id, now, cooldown),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def set_cooldown(self, user_id: int, column: str, ts: float):
        assert column in COOLDOWN_COLUMNS
        async with self.lock:
            await self.conn.execute(
                f"UPDATE users SET {column} = ? WHERE user_id = ?", (ts, user_id)
            )
            await self.conn.commit()

    # ---------- шорон, хамгаалалт ----------
    async def jail(self, user_id: int, until: float, bail: int):
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.execute(
                "UPDATE users SET jail_until = ?, jail_bail = ? WHERE user_id = ?",
                (until, bail, user_id),
            )
            await self.conn.commit()

    async def pay_bail(self, user_id: int, now: float) -> str:
        """'ok' | 'free' (шоронд байхгүй) | 'poor' (мөнгө хүрэхгүй)"""
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                "SELECT balance, jail_until, jail_bail FROM users WHERE user_id = ?",
                (user_id,),
            )
            row = await cur.fetchone()
            if row["jail_until"] <= now:
                return "free"
            if row["balance"] < row["jail_bail"]:
                return "poor"
            await self.conn.execute(
                "UPDATE users SET balance = balance - ?, jail_until = 0, jail_bail = 0 "
                "WHERE user_id = ?",
                (row["jail_bail"], user_id),
            )
            await self.conn.commit()
            return "ok"

    async def set_protect(self, user_id: int, until: float):
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.execute(
                "UPDATE users SET protect_until = ? WHERE user_id = ?", (until, user_id)
            )
            await self.conn.commit()

    # ---------- дээрэм, хакер ----------
    async def steal_wallet(self, thief: int, victim: int, amount: int) -> bool:
        async with self.lock:
            await self._ensure(thief)
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
                (amount, victim, amount),
            )
            if cur.rowcount != 1:
                await self.conn.rollback()
                return False
            await self.conn.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, thief)
            )
            await self.conn.commit()
            return True

    async def steal_bank(self, thief: int, victim: int, amount: int) -> bool:
        async with self.lock:
            await self._ensure(thief)
            cur = await self.conn.execute(
                "UPDATE users SET bank = bank - ? WHERE user_id = ? AND bank >= ?",
                (amount, victim, amount),
            )
            if cur.rowcount != 1:
                await self.conn.rollback()
                return False
            await self.conn.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, thief)
            )
            await self.conn.commit()
            return True

    # ---------- цүнх ----------
    async def get_inventory(self, user_id: int):
        cur = await self.conn.execute(
            "SELECT item_key, qty FROM inventory WHERE user_id = ? AND qty > 0 "
            "ORDER BY item_key",
            (user_id,),
        )
        return await cur.fetchall()

    async def item_qty(self, user_id: int, item_key: str) -> int:
        cur = await self.conn.execute(
            "SELECT qty FROM inventory WHERE user_id = ? AND item_key = ?",
            (user_id, item_key),
        )
        row = await cur.fetchone()
        return row["qty"] if row else 0

    async def add_item(self, user_id: int, item_key: str, qty: int = 1):
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.execute(
                "INSERT INTO inventory (user_id, item_key, qty) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, item_key) DO UPDATE SET qty = qty + excluded.qty",
                (user_id, item_key, qty),
            )
            await self.conn.commit()

    async def remove_item(self, user_id: int, item_key: str, qty: int = 1) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE inventory SET qty = qty - ? "
                "WHERE user_id = ? AND item_key = ? AND qty >= ?",
                (qty, user_id, item_key, qty),
            )
            ok = cur.rowcount == 1
            if ok:
                await self.conn.execute(
                    "DELETE FROM inventory WHERE user_id = ? AND item_key = ? AND qty <= 0",
                    (user_id, item_key),
                )
            await self.conn.commit()
            return ok

    # ---------- дэлгүүрийн нөөц ----------
    async def shop_sold(self, day: int) -> dict[str, int]:
        cur = await self.conn.execute(
            "SELECT item_key, sold FROM shop_stock WHERE day = ?", (day,)
        )
        return {r["item_key"]: r["sold"] for r in await cur.fetchall()}

    async def buy_stock(self, item_key: str, day: int, qty: int, max_stock: int) -> bool:
        """Нөөц хүрэлцэж байвал өнөөдрийн зарагдсан тоог нэмнэ."""
        async with self.lock:
            cur = await self.conn.execute(
                "SELECT day, sold FROM shop_stock WHERE item_key = ?", (item_key,)
            )
            row = await cur.fetchone()
            sold = row["sold"] if row and row["day"] == day else 0
            if sold + qty > max_stock:
                return False
            await self.conn.execute(
                "INSERT INTO shop_stock (item_key, day, sold) VALUES (?, ?, ?) "
                "ON CONFLICT(item_key) DO UPDATE SET day = excluded.day, sold = excluded.sold",
                (item_key, day, sold + qty),
            )
            await self.conn.commit()
            return True

    async def release_stock(self, item_key: str, day: int, qty: int):
        async with self.lock:
            await self.conn.execute(
                "UPDATE shop_stock SET sold = MAX(0, sold - ?) WHERE item_key = ? AND day = ?",
                (qty, item_key, day),
            )
            await self.conn.commit()

    # ---------- амьтан ----------
    async def set_pet(self, user_id: int, pet_key: str | None):
        async with self.lock:
            await self.conn.execute(
                "UPDATE users SET pet = ? WHERE user_id = ?", (pet_key, user_id)
            )
            await self.conn.commit()

    # ---------- байшин ----------
    async def set_house(self, user_id: int, house_key: str | None):
        async with self.lock:
            await self.conn.execute(
                "UPDATE users SET house = ? WHERE user_id = ?", (house_key, user_id)
            )
            await self.conn.commit()

    async def buy_house(self, user_id: int, house_key: str, cost: int) -> bool:
        """Мөнгө хүрэлцэж байвал хасаад байшинг онооно."""
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance - ?, house = ? "
                "WHERE user_id = ? AND balance >= ?",
                (cost, house_key, user_id, cost),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def get_house_items(self, user_id: int, room: str | None = None):
        if room is None:
            cur = await self.conn.execute(
                "SELECT room, item_key, qty FROM house_items "
                "WHERE user_id = ? AND qty > 0 ORDER BY room, item_key",
                (user_id,),
            )
        else:
            cur = await self.conn.execute(
                "SELECT room, item_key, qty FROM house_items "
                "WHERE user_id = ? AND room = ? AND qty > 0 ORDER BY item_key",
                (user_id, room),
            )
        return await cur.fetchall()

    async def place_item(
        self, user_id: int, room: str, item_key: str, qty: int, slots: int
    ) -> str:
        """Цүнхнээс өрөөнд шилжүүлнэ. 'ok' | 'no_item' | 'full'"""
        async with self.lock:
            cur = await self.conn.execute(
                "SELECT qty FROM inventory WHERE user_id = ? AND item_key = ?",
                (user_id, item_key),
            )
            row = await cur.fetchone()
            if not row or row["qty"] < qty:
                return "no_item"
            cur = await self.conn.execute(
                "SELECT COALESCE(SUM(qty), 0) AS n FROM house_items "
                "WHERE user_id = ? AND room = ?",
                (user_id, room),
            )
            used = (await cur.fetchone())["n"]
            if used + qty > slots:
                return "full"
            await self.conn.execute(
                "UPDATE inventory SET qty = qty - ? WHERE user_id = ? AND item_key = ?",
                (qty, user_id, item_key),
            )
            await self.conn.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_key = ? AND qty <= 0",
                (user_id, item_key),
            )
            await self.conn.execute(
                "INSERT INTO house_items (user_id, room, item_key, qty) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id, room, item_key) DO UPDATE SET qty = qty + excluded.qty",
                (user_id, room, item_key, qty),
            )
            await self.conn.commit()
            return "ok"

    async def unplace_item(self, user_id: int, room: str, item_key: str, qty: int) -> bool:
        """Өрөөнөөс цүнх рүү буцаана."""
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE house_items SET qty = qty - ? "
                "WHERE user_id = ? AND room = ? AND item_key = ? AND qty >= ?",
                (qty, user_id, room, item_key, qty),
            )
            if cur.rowcount != 1:
                await self.conn.rollback()
                return False
            await self.conn.execute(
                "DELETE FROM house_items WHERE user_id = ? AND room = ? "
                "AND item_key = ? AND qty <= 0",
                (user_id, room, item_key),
            )
            await self.conn.execute(
                "INSERT INTO inventory (user_id, item_key, qty) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, item_key) DO UPDATE SET qty = qty + excluded.qty",
                (user_id, item_key, qty),
            )
            await self.conn.commit()
            return True

    # ---------- сейф ----------
    async def buy_safe_level(self, user_id: int, new_level: int, cost: int) -> bool:
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance - ?, safe_level = ? "
                "WHERE user_id = ? AND balance >= ? AND safe_level = ?",
                (cost, new_level, user_id, cost, new_level - 1),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def safe_put_money(self, user_id: int, amount: int, cap: int) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance - ?, safe_money = safe_money + ? "
                "WHERE user_id = ? AND balance >= ? AND safe_money + ? <= ?",
                (amount, amount, user_id, amount, amount, cap),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def safe_take_money(self, user_id: int, amount: int) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE users SET balance = balance + ?, safe_money = safe_money - ? "
                "WHERE user_id = ? AND safe_money >= ?",
                (amount, amount, user_id, amount),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def get_safe_items(self, user_id: int):
        cur = await self.conn.execute(
            "SELECT item_key, qty FROM safe_items WHERE user_id = ? AND qty > 0 "
            "ORDER BY item_key",
            (user_id,),
        )
        return await cur.fetchall()

    async def safe_put_item(
        self, user_id: int, item_key: str, qty: int, slots: int
    ) -> str:
        """Цүнхнээс сейф рүү. 'ok' | 'no_item' | 'full'"""
        async with self.lock:
            cur = await self.conn.execute(
                "SELECT qty FROM inventory WHERE user_id = ? AND item_key = ?",
                (user_id, item_key),
            )
            row = await cur.fetchone()
            if not row or row["qty"] < qty:
                return "no_item"
            cur = await self.conn.execute(
                "SELECT COALESCE(SUM(qty), 0) AS n FROM safe_items WHERE user_id = ?",
                (user_id,),
            )
            if (await cur.fetchone())["n"] + qty > slots:
                return "full"
            await self.conn.execute(
                "UPDATE inventory SET qty = qty - ? WHERE user_id = ? AND item_key = ?",
                (qty, user_id, item_key),
            )
            await self.conn.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_key = ? AND qty <= 0",
                (user_id, item_key),
            )
            await self.conn.execute(
                "INSERT INTO safe_items (user_id, item_key, qty) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, item_key) DO UPDATE SET qty = qty + excluded.qty",
                (user_id, item_key, qty),
            )
            await self.conn.commit()
            return "ok"

    async def safe_take_item(self, user_id: int, item_key: str, qty: int) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE safe_items SET qty = qty - ? "
                "WHERE user_id = ? AND item_key = ? AND qty >= ?",
                (qty, user_id, item_key, qty),
            )
            if cur.rowcount != 1:
                await self.conn.rollback()
                return False
            await self.conn.execute(
                "DELETE FROM safe_items WHERE user_id = ? AND item_key = ? AND qty <= 0",
                (user_id, item_key),
            )
            await self.conn.execute(
                "INSERT INTO inventory (user_id, item_key, qty) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, item_key) DO UPDATE SET qty = qty + excluded.qty",
                (user_id, item_key, qty),
            )
            await self.conn.commit()
            return True

    # ---------- өлсөлт ----------
    async def set_last_fed(self, user_id: int, ts: float):
        async with self.lock:
            await self.conn.execute(
                "UPDATE users SET last_fed = ? WHERE user_id = ?", (ts, user_id)
            )
            await self.conn.commit()

    async def starving_users(self, now: float, hunger_seconds: float, death_seconds: float, gap: float):
        """Өлссөн (3-7 хоног хоолгүй), амьд, сүүлийн 'gap' секундэд торгуульд ороогүй хэрэглэгчид."""
        cur = await self.conn.execute(
            "SELECT user_id, last_channel, hunger_notified FROM users "
            "WHERE registered = 1 AND dead = 0 AND ? - last_fed >= ? AND ? - last_fed < ? "
            "AND ? - last_starve >= ?",
            (now, hunger_seconds, now, death_seconds, now, gap),
        )
        return await cur.fetchall()

    async def dying_users(self, now: float, death_seconds: float):
        cur = await self.conn.execute(
            "SELECT user_id, last_channel FROM users "
            "WHERE registered = 1 AND dead = 0 AND ? - last_fed >= ?",
            (now, death_seconds),
        )
        return await cur.fetchall()

    async def mark_notified(self, user_id: int, now: float):
        async with self.lock:
            await self.conn.execute(
                "UPDATE users SET hunger_notified = ? WHERE user_id = ?", (now, user_id)
            )
            await self.conn.commit()

    async def apply_starvation(self, user_id: int, now: float, rate: float) -> int:
        """Хэтэвчний rate хувийг хасаж, хассан дүнг буцаана."""
        async with self.lock:
            cur = await self.conn.execute(
                "SELECT balance FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cur.fetchone()
            taken = int(row["balance"] * rate) if row else 0
            await self.conn.execute(
                "UPDATE users SET balance = balance - ?, last_starve = ? WHERE user_id = ?",
                (taken, now, user_id),
            )
            await self.conn.commit()
            return taken

    # ---------- бүртгэл, дүр ----------
    async def register(self, user_id: int, gender: str, age: int, country: str, skin: str):
        now = time.time()
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.execute(
                "UPDATE users SET registered = 1, gender = ?, age = ?, country = ?, skin = ?, "
                "last_fed = ?, last_starve = ? WHERE user_id = ?",
                (gender, age, country, skin, now, now, user_id),
            )
            await self.conn.commit()

    async def set_dead(self, user_id: int, dead: bool, now: float):
        async with self.lock:
            await self._ensure(user_id)
            if dead:
                await self.conn.execute("UPDATE users SET dead = 1 WHERE user_id = ?", (user_id,))
            else:
                await self.conn.execute(
                    "UPDATE users SET dead = 0, last_fed = ?, last_starve = ? WHERE user_id = ?",
                    (now, now, user_id),
                )
            await self.conn.commit()

    async def get_equipped(self, user_id: int) -> dict[str, str]:
        cur = await self.conn.execute(
            "SELECT slot, item_key FROM equipped WHERE user_id = ?", (user_id,)
        )
        return {r["slot"]: r["item_key"] for r in await cur.fetchall()}

    async def equip(self, user_id: int, slot: str, item_key: str):
        async with self.lock:
            await self.conn.execute(
                "INSERT INTO equipped (user_id, slot, item_key) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, slot) DO UPDATE SET item_key = excluded.item_key",
                (user_id, slot, item_key),
            )
            await self.conn.commit()

    async def unequip(self, user_id: int, slot: str) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "DELETE FROM equipped WHERE user_id = ? AND slot = ?", (user_id, slot)
            )
            await self.conn.commit()
            return cur.rowcount == 1

    # ---------- potion ----------
    async def set_potion(self, user_id: int, column: str, until: float):
        assert column in ("luck_until", "boost_until")
        async with self.lock:
            await self._ensure(user_id)
            await self.conn.execute(
                f"UPDATE users SET {column} = ? WHERE user_id = ?", (until, user_id)
            )
            await self.conn.commit()

    # ---------- татвар / сан ----------
    async def get_setting(self, key: str) -> int:
        cur = await self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else 0

    async def add_setting(self, key: str, delta: int):
        async with self.lock:
            await self.conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = value + excluded.value",
                (key, delta),
            )
            await self.conn.commit()

    async def take_pool(self, amount: int) -> bool:
        """Татварын сангаас мөнгө хасна (хүрэлцэхгүй бол False)."""
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE settings SET value = value - ? WHERE key = 'pool' AND value >= ?",
                (amount, amount),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    # ---------- админ ----------
    async def is_admin(self, user_id: int) -> bool:
        cur = await self.conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return await cur.fetchone() is not None

    async def add_admin(self, user_id: int):
        async with self.lock:
            await self.conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
            await self.conn.commit()

    async def remove_admin(self, user_id: int) -> bool:
        async with self.lock:
            cur = await self.conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await self.conn.commit()
            return cur.rowcount == 1

    async def list_admins(self) -> list[int]:
        cur = await self.conn.execute("SELECT user_id FROM admins")
        return [r["user_id"] for r in await cur.fetchall()]

    async def confiscate(self, user_id: int, amount: int) -> int:
        """Хэтэвчнээс, дутвал банкнаас мөнгө хураана. Хураасан дүнг буцаана (сан руу орно)."""
        async with self.lock:
            await self._ensure(user_id)
            cur = await self.conn.execute(
                "SELECT balance, bank FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cur.fetchone()
            from_wallet = min(row["balance"], amount)
            from_bank = min(row["bank"], amount - from_wallet)
            total = from_wallet + from_bank
            await self.conn.execute(
                "UPDATE users SET balance = balance - ?, bank = bank - ? WHERE user_id = ?",
                (from_wallet, from_bank, user_id),
            )
            if total:
                await self.conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('pool', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = value + excluded.value",
                    (total,),
                )
            await self.conn.commit()
            return total

    async def set_jail_raw(self, user_id: int, until: float, bail: int = 0):
        await self.jail(user_id, until, bail)

    async def reset_user(self, user_id: int):
        async with self.lock:
            for table in ("inventory", "house_items", "safe_items", "equipped"):
                await self.conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
            await self.conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await self.conn.commit()

    # ---------- романс ----------
    async def marry(self, a: int, b: int) -> bool:
        async with self.lock:
            await self._ensure(a)
            await self._ensure(b)
            cur = await self.conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE user_id IN (?, ?) AND spouse = 0", (a, b)
            )
            if (await cur.fetchone())["c"] != 2:
                return False
            await self.conn.execute("UPDATE users SET spouse = ?, love = 0 WHERE user_id = ?", (b, a))
            await self.conn.execute("UPDATE users SET spouse = ?, love = 0 WHERE user_id = ?", (a, b))
            await self.conn.commit()
            return True

    async def divorce(self, user_id: int) -> int:
        """Салсан хүний ID-г буцаана (0 бол гэрлээгүй)."""
        async with self.lock:
            cur = await self.conn.execute("SELECT spouse FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            other = row["spouse"] if row else 0
            if other:
                await self.conn.execute(
                    "UPDATE users SET spouse = 0, love = 0 WHERE user_id IN (?, ?)", (user_id, other)
                )
                await self.conn.commit()
            return other

    async def add_love(self, a: int, b: int, amount: int):
        async with self.lock:
            await self.conn.execute(
                "UPDATE users SET love = love + ? WHERE user_id IN (?, ?)", (amount, a, b)
            )
            await self.conn.commit()

    # ---------- giveaway ----------
    async def create_giveaway(self, guild_id, channel_id, host_id, prize, winners, ends_at) -> int:
        async with self.lock:
            cur = await self.conn.execute(
                "INSERT INTO giveaways (guild_id, channel_id, host_id, prize, winners, ends_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, channel_id, host_id, prize, winners, ends_at),
            )
            await self.conn.commit()
            return cur.lastrowid

    async def set_giveaway_message(self, gid: int, message_id: int):
        async with self.lock:
            await self.conn.execute("UPDATE giveaways SET message_id = ? WHERE id = ?", (message_id, gid))
            await self.conn.commit()

    async def get_giveaway(self, gid: int):
        cur = await self.conn.execute("SELECT * FROM giveaways WHERE id = ?", (gid,))
        return await cur.fetchone()

    async def active_giveaways(self):
        cur = await self.conn.execute("SELECT * FROM giveaways WHERE status = 'active'")
        return await cur.fetchall()

    async def enter_giveaway(self, gid: int, user_id: int) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
                (gid, user_id),
            )
            await self.conn.commit()
            return cur.rowcount == 1

    async def giveaway_entries(self, gid: int) -> list[int]:
        cur = await self.conn.execute(
            "SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?", (gid,)
        )
        return [r["user_id"] for r in await cur.fetchall()]

    async def close_giveaway(self, gid: int) -> bool:
        async with self.lock:
            cur = await self.conn.execute(
                "UPDATE giveaways SET status = 'ended' WHERE id = ? AND status = 'active'", (gid,)
            )
            await self.conn.commit()
            return cur.rowcount == 1

    # ---------- статистик ----------
    async def stats(self) -> dict:
        cur = await self.conn.execute(
            "SELECT COUNT(*) AS players, "
            "COALESCE(SUM(balance + bank + safe_money), 0) AS money, "
            "COALESCE(SUM(CASE WHEN dead = 1 THEN 1 ELSE 0 END), 0) AS dead, "
            "COALESCE(SUM(CASE WHEN spouse > 0 THEN 1 ELSE 0 END), 0) AS married, "
            "COALESCE(SUM(CASE WHEN jail_until > ? THEN 1 ELSE 0 END), 0) AS jailed "
            "FROM users WHERE registered = 1",
            (time.time(),),
        )
        row = await cur.fetchone()
        out = dict(row)
        out["married"] //= 2
        out["pool"] = await self.get_setting("pool")
        return out
