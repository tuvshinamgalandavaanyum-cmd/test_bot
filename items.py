import random
import re
from dataclasses import dataclass, replace

SELL_RATE = 0.7  # дэлгүүрт буцааж зарахад үнийн 70%

KIND_EMOJI = {"house": "🏠", "food": "🍽️", "jewel": "💎", "metal": "⛏️", "tool": "🛡️",
              "clothes": "👕", "car": "🚗", "love": "💞", "box": "🎁"}


@dataclass(frozen=True)
class Item:
    key: str  # ID: qbuy <ID>
    name: str  # монгол нэр
    en: str
    price: int
    kind: str  # house | food | jewel | metal | tool
    emoji: str = "📦"
    desc: str = ""
    stock: int | None = None  # өдөрт зарагдах дээд хэмжээ (None = хязгааргүй)
    placeable: bool = False  # байшинд байрлуулж болох эсэх
    stars: int = 0  # хоол: 1-5 од
    feeds_days: float = 0.0  # хоол: хэдэн хоногийн хоол
    strength: int = 0  # хоол: нэмэх хүч
    buyable: bool = True  # qbuy-аар авч болох эсэх

    @property
    def sell_price(self) -> int:
        return int(self.price * SELL_RATE)


def _slug(en: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", en.lower()).strip("_")


# ---------- гэр ахуйн бараа (хулгайгаар олдох, дэлгүүрт зарагдах) ----------
_HOUSE_RAW = [
    ("Хутга", "Knife", 8_000),
    ("Халбага", "Spoon", 1_500),
    ("Сэрээ", "Fork", 1_500),
    ("Таваг", "Plate", 3_000),
    ("Аяга", "Cup", 2_500),
    ("Төгнө", "Kettle", 25_000),
    ("Сандал", "Chair", 40_000),
    ("Ширээ", "Table", 90_000),
    ("Орон", "Bed", 250_000),
    ("Дэр", "Pillow", 12_000),
    ("Хөнжил", "Blanket", 45_000),
    ("Шүүгээ", "Cabinet", 180_000),
    ("Толь", "Mirror", 20_000),
    ("Хөшиг", "Curtain", 30_000),
    ("Хивс", "Carpet", 150_000),
    ("Цаг", "Wall clock", 18_000),
    ("Зураг", "Picture frame", 15_000),
    ("Ваар", "Vase", 35_000),
    ("Ламп", "Lamp", 28_000),
    ("Телевиз", "TV", 450_000),
    ("Компьютер", "Computer", 600_000),
    ("Утас", "Phone", 400_000),
    ("Хөргөгч", "Fridge", 500_000),
    ("Бичил долгионы зуух", "Microwave", 120_000),
    ("Плитк", "Stove", 90_000),
    ("Угаагуур", "Sink", 70_000),
    ("Саван", "Soap", 2_000),
    ("Султаа", "Towel", 8_000),
    ("Шүдний сойз", "Toothbrush", 2_500),
    ("Шүдний оо", "Toothpaste", 4_000),
    ("Сам", "Comb", 3_000),
    ("Үсний сэн", "Hairdryer", 55_000),
    ("Шанага", "Ladle", 6_000),
    ("Тогоо", "Pot", 60_000),
    ("Хайруулын таваг", "Frying pan", 35_000),
    ("Хогийн сав", "Trash can", 12_000),
    ("Түлхүүр", "Keys", 5_000),
    ("Түрийвч", "Wallet", 30_000),
    ("Ном", "Book", 15_000),
    ("Дэвтэр", "Notebook", 3_000),
    ("Үзэг", "Pen", 1_000),
    ("Харандаа", "Pencil", 800),
    ("Цүнх", "Bag", 60_000),
    ("Хувцас", "Clothes", 80_000),
    ("Гутал", "Shoes", 100_000),
    ("Оймс", "Socks", 5_000),
    ("Цэнэглэгч", "Charger", 20_000),
    ("Чихэвч", "Headphones", 90_000),
    ("Спикер", "Speaker", 110_000),
    ("Хайч", "Scissors", 6_000),
    ("Скоч", "Tape", 2_500),
    ("Эм", "Medicine", 15_000),
    ("Термос", "Thermos", 40_000),
    ("Усны сав", "Water bottle", 12_000),
    ("Сүрчиг", "Perfume", 120_000),
    ("Цаг (бугуйн)", "Wristwatch", 200_000),
    ("Нүдний шил", "Glasses", 75_000),
    ("Маск", "Mask", 1_500),
    ("Дэнлүү", "Flashlight", 18_000),
    ("Батерей", "Battery", 3_500),
    ("Шүүр", "Broom", 8_000),
    ("Шапк", "Cap", 22_000),
    ("Ханцуйвч", "Gloves", 25_000),
    ("Бүс", "Belt", 30_000),
    ("Тоглоом", "Toy", 25_000),
    ("Шатар", "Chess", 35_000),
    ("Хөзөр", "Playing cards", 5_000),
    ("Сэтгүүл", "Magazine", 4_000),
    ("Газар зүйн зураг", "Map", 12_000),
    ("Дуран", "Binoculars", 150_000),
    ("Оёдлын иж бүрдэл", "Sewing kit", 14_000),
    ("Индүү", "Clothes iron", 45_000),
    ("Тоос сорогч", "Vacuum cleaner", 220_000),
    ("Орон орны бүтээлэг", "Bedspread", 65_000),
    ("Салфетка", "Napkin", 1_000),
    ("Сав таваг угаагч", "Dish soap", 3_500),
    ("Порлон", "Sponge", 1_200),
    ("Хайрцаг", "Box", 4_000),
    ("Тэвш", "Tray", 15_000),
    ("Бортого", "Jar", 6_000),
    ("Лоонх", "Bottle", 3_000),
    ("Шилэн аяга", "Glass", 4_000),
    ("Бэлэгний хайрцаг", "Gift box", 10_000),
    ("Лаа", "Candle", 4_500),
    ("Шүдэнз", "Matches", 800),
    ("Асагуур", "Lighter", 5_000),
    ("Алх", "Hammer", 28_000),
    ("Дээс", "Rope", 8_000),
    ("Тэгш өнцөгт", "Ruler", 2_000),
    ("Тооны машин", "Calculator", 25_000),
    ("Ургамал", "Plant", 20_000),
    ("Цэцгийн ваар", "Flower pot", 18_000),
    ("Будаг", "Paint", 35_000),
    ("Сонин", "Newspaper", 1_500),
    ("Зургийн цомог", "Photo album", 22_000),
    ("Мөнгөний сав", "Piggy bank", 14_000),
    ("Шүхэр", "Umbrella", 30_000),
    ("Цоож", "Lock", 16_000),
    ("Тэмдэглэлийн дэвтэр", "Diary", 9_000),
    ("Зүү", "Needle", 1_000),
]

_PLACEABLE = {
    "Chair", "Table", "Bed", "Pillow", "Blanket", "Cabinet", "Mirror", "Curtain",
    "Carpet", "Wall clock", "Picture frame", "Vase", "Lamp", "TV", "Computer",
    "Fridge", "Microwave", "Stove", "Sink", "Kettle", "Vacuum cleaner", "Speaker",
    "Plant", "Flower pot", "Chess", "Bedspread", "Trash can", "Photo album",
    "Piggy bank", "Clothes iron", "Candle", "Hairdryer",
}

_EMOJI = {
    "chair": "🪑", "table": "🍽️", "bed": "🛏️", "pillow": "🛌", "blanket": "🧣",
    "cabinet": "🗄️", "mirror": "🪞", "curtain": "🪟", "carpet": "🟫", "wall_clock": "🕰️",
    "picture_frame": "🖼️", "vase": "🏺", "lamp": "💡", "tv": "📺", "computer": "💻",
    "phone": "📱", "fridge": "🧊", "microwave": "📡", "stove": "🔥", "sink": "🚰",
    "kettle": "🫖", "knife": "🔪", "book": "📖", "keys": "🔑", "wallet": "👛",
    "bag": "👜", "shoes": "👟", "headphones": "🎧", "speaker": "🔊", "glasses": "👓",
    "umbrella": "☂️", "plant": "🪴", "candle": "🕯️", "lighter": "🪔", "hammer": "🔨",
    "lock": "🔒", "toy": "🧸", "chess": "♟️", "playing_cards": "🃏", "binoculars": "🔭",
    "perfume": "🧴", "wristwatch": "⌚", "medicine": "💊", "soap": "🧼", "toothbrush": "🪥",
    "scissors": "✂️", "calculator": "🧮", "battery": "🔋", "flashlight": "🔦",
    "rope": "🪢", "piggy_bank": "🐷", "mask": "😷", "map": "🗺️", "vacuum_cleaner": "🧹",
    "broom": "🧹", "needle": "🪡", "paint": "🎨", "gift_box": "🎁",
}

HOUSE_ITEMS: list[Item] = []
for _mn, _en, _price in _HOUSE_RAW:
    _k = _slug(_en)
    HOUSE_ITEMS.append(
        Item(
            _k, _mn, _en, _price, "house",
            emoji=_EMOJI.get(_k, "🏠"),
            desc="Гэр ахуйн бараа" + (" · байшинд байрлуулна" if _en in _PLACEABLE else ""),
            stock=5 if _price >= 400_000 else None,
            placeable=_en in _PLACEABLE,
        )
    )

# ---------- үнэт эдлэл ----------
JEWELS: list[Item] = [
    Item("ring", "Бөгж", "Ring", 150_000, "jewel", "💍", "Алтан бөгж · Статус", stock=5),
    Item("watch", "Цаг", "Luxury watch", 200_000, "jewel", "🕐", "Үнэт цаг · Статус", stock=5),
    Item("necklace", "Зүүлт", "Necklace", 250_000, "jewel", "📿", "Алтан зүүлт · Статус", stock=5),
    Item("crystal", "Болор", "Crystal", 300_000, "jewel", "🔮", "Ховор болор · Ид шид", stock=5),
    Item("gem", "Эрдэнийн чулуу", "Gem", 500_000, "jewel", "💎", "Нандин эрдэнийн чулуу · Статус", stock=5),
    Item("gold_coin", "Алтан зоос", "Gold coin", 1_000_000, "jewel", "🪙", "Цэвэр алтан зоос · Хөрөнгө", stock=5),
]

# ---------- металл (үнэ нь металлаас хамаарна) ----------
METALS: list[Item] = [
    Item("iron", "Төмөр", "Iron", 5_000, "metal", "🔩", "Энгийн төмөр", stock=30),
    Item("copper", "Зэс", "Copper", 8_000, "metal", "🟠", "Улбар шар зэс", stock=30),
    Item("bronze", "Хүрэл", "Bronze", 12_000, "metal", "🥉", "Хүрэл", stock=25),
    Item("silver", "Мөнгө (silver)", "Silver", 60_000, "metal", "🥈", "Цэвэр мөнгөн металл", stock=15),
    Item("gold", "Алт", "Gold", 250_000, "metal", "🥇", "Цэвэр алт", stock=10),
    Item("platinum", "Цагаан алт", "Platinum", 400_000, "metal", "⬜", "Платина", stock=8),
    Item("diamond", "Алмаз", "Diamond", 800_000, "metal", "💠", "Алмаз", stock=5),
    Item("uranium", "Уран", "Uranium", 1_500_000, "metal", "☢️", "Туйлын ховор уран", stock=3),
]

# ---------- хоол: 1-5 од, од өндөр байх тусам үнэ, цатгах хугацаа нэмэгдэнэ ----------
# (ID, нэр, англи, үнэ, од, цатгах хоног, хүч, emoji)
_FOODS_RAW = [
    ("candy", "Чихэр", "Candy", 1_000, 1, 1, 0, "🍬"),
    ("cookie", "Жигнэмэг", "Cookie", 2_000, 1, 1, 0, "🍪"),
    ("chips", "Чипс", "Chips", 2_500, 1, 1, 0, "🍟"),
    ("milk_tea", "Сүүтэй цай", "Milk tea", 3_000, 1, 1, 0, "🍵"),
    ("bread", "Талх", "Bread", 4_000, 2, 2, 0, "🍞"),
    ("noodles", "Түргэн гоймон", "Instant noodles", 5_000, 2, 2, 0, "🍜"),
    ("bansh", "Банш", "Bansh", 7_000, 2, 3, 0, "🥟"),
    ("buuz", "Бууз", "Buuz", 10_000, 3, 4, 0, "🥟"),
    ("khuushuur", "Хуушуур", "Khuushuur", 12_000, 3, 4, 0, "🥮"),
    ("tsuivan", "Цуйван", "Tsuivan", 16_000, 3, 5, 0, "🍝"),
    ("soup", "Хонины шөл", "Mutton soup", 28_000, 4, 6, 1, "🍲"),
    ("khorkhog", "Хорхог", "Khorkhog", 45_000, 4, 7, 1, "🍖"),
    ("steak", "Стейк", "Steak", 65_000, 5, 7, 2, "🥩"),
    ("boodog", "Боодог", "Boodog", 90_000, 5, 7, 2, "🍖"),
    ("feast", "Баярын хоол", "Feast", 130_000, 5, 7, 3, "🍱"),
]

FOODS: list[Item] = [
    Item(k, mn, en, price, "food", emoji, "", None, False, stars, float(days), strength)
    for (k, mn, en, price, stars, days, strength, emoji) in _FOODS_RAW
]

# ---------- хэрэгсэл ----------
TOOLS: list[Item] = [
    Item("shield", "Хамгаалалтын бамбай", "Shield", 120_000, "tool", "🛡️",
         "2.5 цаг дээрэм, хакердалтаас хамгаална · qblock"),
]

# ---------- хэрэгслийн нэмэлт: Revive Active ба хайрцгууд (дэлгүүрт зарагдахгүй) ----------
TOOLS.append(
    Item("revive", "Revive Active", "Revive Active", 5_000_000, "tool", "💖",
         "Үхсэн хүнийг амилуулна · qinv use revive", buyable=False)
)
BOXES: list[Item] = [
    Item("mbox", "Box", "Box", 50_000, "box", "📦", "Энгийн хайрцаг · qopen box", buyable=False),
    Item("mcase", "Case", "Case", 150_000, "box", "💼", "Big Cash кейс · qopen case", buyable=False),
    Item("mchest", "Chest", "Chest", 400_000, "box", "🧰", "Эд зүйлсийн авдар · qopen chest", buyable=False),
]
BOX_ALIASES = {"box": "mbox", "case": "mcase", "chest": "mchest",
               "mbox": "mbox", "mcase": "mcase", "mchest": "mchest"}

# ---------- хайр сэтгэл, хосын эд зүйлс ----------
LOVE_ITEMS: list[Item] = [
    Item("rose", "Сарнай", "Rose", 15_000, "love", "🌹", "Хайртай хүндээ бэлэглэ · qgift rose @хүн"),
    Item("chocolate", "Шоколад", "Chocolate", 20_000, "love", "🍫", "Амттай бэлэг · qgift chocolate @хүн"),
    Item("love_letter", "Хайрын захидал", "Love letter", 5_000, "love", "💌", "Сэтгэлээ илэр"),
    Item("teddy", "Хонгор баавгай", "Teddy bear", 60_000, "love", "🧸", "Хайртай хүндээ бэлэглэ"),
    Item("couple_cups", "Хосын аяга", "Couple cups", 40_000, "love", "☕", "Хосын хоёр аяга"),
    Item("bouquet", "Баглаа цэцэг", "Bouquet", 90_000, "love", "💐", "Гоё баглаа цэцэг"),
]

# ---------- дижитал ----------
_DIGITAL_EN = {"TV", "Computer", "Phone", "Charger", "Headphones", "Speaker", "Calculator"}
_DIGITAL_NEW: list[Item] = [
    Item("laptop", "Зөөврийн компьютер", "Laptop", 900_000, "house", "💻", "Дижитал · зөөврийн компьютер", stock=5),
    Item("tablet", "Таблет", "Tablet", 500_000, "house", "📲", "Дижитал · таблет", stock=5),
    Item("console", "Тоглоомын консол", "Game console", 700_000, "house", "🎮", "Дижитал · тоглоомын консол", stock=5),
    Item("camera", "Камер", "Camera", 350_000, "house", "📷", "Дижитал · зургийн аппарат", stock=5),
    Item("smartwatch", "Ухаалаг цаг", "Smart watch", 250_000, "house", "⌚", "Дижитал · ухаалаг цаг", stock=5),
    Item("drone", "Дрон", "Drone", 1_200_000, "house", "🚁", "Дижитал · дрон", stock=3),
]

# ---------- хувцас: key -> (байрлал, өнгө) ----------
CLOTHES_STYLE: dict[str, tuple[str, str]] = {
    "tshirt": ("top", "#ef4444"), "hoodie": ("top", "#6366f1"), "jacket": ("top", "#374151"),
    "suit": ("full", "#111827"), "deel": ("full", "#0ea5e9"), "dress": ("full", "#ec4899"),
    "jeans": ("bottom", "#1d4ed8"), "shorts": ("bottom", "#f59e0b"),
    "sneakers": ("shoes", "#f3f4f6"), "boots": ("shoes", "#78350f"), "mongol_boots": ("shoes", "#b91c1c"),
    "hat": ("hat", "#92400e"), "sunglasses": ("face", "#111827"), "scarf": ("neck", "#f97316"),
    # дэлгүүрт байсан хуучин хувцаснууд
    "clothes": ("top", "#10b981"), "shoes": ("shoes", "#4b5563"), "cap": ("hat", "#2563eb"),
    "glasses": ("face", "#1f2937"),
}
_CLOTHES_NEW: list[Item] = [
    Item("tshirt", "Футболк", "T-shirt", 60_000, "clothes", "👕", "Дээр өмсөх · qwear tshirt"),
    Item("hoodie", "Ходи", "Hoodie", 150_000, "clothes", "🧥", "Дээр өмсөх · qwear hoodie"),
    Item("jacket", "Куртик", "Jacket", 280_000, "clothes", "🧥", "Дээр өмсөх · qwear jacket"),
    Item("suit", "Костюм", "Suit", 700_000, "clothes", "🤵", "Бүтэн хувцас · qwear suit"),
    Item("deel", "Монгол дээл", "Deel", 900_000, "clothes", "🥋", "Үндэсний бүтэн хувцас · qwear deel"),
    Item("dress", "Даашинз", "Dress", 450_000, "clothes", "👗", "Бүтэн хувцас · qwear dress"),
    Item("jeans", "Жинсэн өмд", "Jeans", 120_000, "clothes", "👖", "Доор өмсөх · qwear jeans"),
    Item("shorts", "Богино өмд", "Shorts", 50_000, "clothes", "🩳", "Доор өмсөх · qwear shorts"),
    Item("sneakers", "Пүүз", "Sneakers", 180_000, "clothes", "👟", "Гутал · qwear sneakers"),
    Item("boots", "Гутал (өвлийн)", "Boots", 220_000, "clothes", "🥾", "Гутал · qwear boots"),
    Item("mongol_boots", "Монгол гутал", "Mongol boots", 350_000, "clothes", "👢", "Үндэсний гутал · qwear mongol_boots"),
    Item("hat", "Малгай", "Hat", 70_000, "clothes", "🎩", "Толгойн хувцас · qwear hat"),
    Item("sunglasses", "Нарны шил", "Sunglasses", 90_000, "clothes", "🕶️", "Нүүрний аксессуар · qwear sunglasses"),
    Item("scarf", "Ороолт", "Scarf", 40_000, "clothes", "🧣", "Хүзүүний аксессуар · qwear scarf"),
]
_WEAR_EN = {"Clothes", "Shoes", "Socks", "Cap", "Gloves", "Belt", "Glasses", "Mask", "Wristwatch", "Bag"}

_OLD_HOUSE = HOUSE_ITEMS
DIGITAL: list[Item] = [i for i in _OLD_HOUSE if i.en in _DIGITAL_EN] + _DIGITAL_NEW
_WEAR_OLD: list[Item] = [i for i in _OLD_HOUSE if i.en in _WEAR_EN]
HOME: list[Item] = [i for i in _OLD_HOUSE if i.en not in _DIGITAL_EN and i.en not in _WEAR_EN] + LOVE_ITEMS
CLOTHES: list[Item] = _CLOTHES_NEW + _WEAR_OLD + JEWELS

# ---------- машин ----------
CARS: list[Item] = [
    Item("bicycle", "Дугуй", "Bicycle", 300_000, "car", "🚲", "Хамгийн хямд унаа"),
    Item("moped", "Мопед", "Moped", 2_500_000, "car", "🛵", "Хотоор давхих"),
    Item("old_prius", "Хуучин Приус", "Old Prius", 12_000_000, "car", "🚗", "Улаанбаатарын хамгийн алдартай машин", stock=5),
    Item("land_cruiser", "Ландкрузер", "Land Cruiser", 60_000_000, "car", "🚙", "Баялгийн тэмдэг", stock=3),
    Item("sports_car", "Спорт машин", "Sports car", 150_000_000, "car", "🏎️", "Хамгийн хурдан, хамгийн үнэтэй", stock=2),
]

ALL_ITEMS: list[Item] = (
    HOUSE_ITEMS + _DIGITAL_NEW + _CLOTHES_NEW + LOVE_ITEMS + CARS
    + JEWELS + METALS + FOODS + TOOLS + BOXES
)
ITEMS: dict[str, Item] = {it.key: it for it in ALL_ITEMS}
assert len(ITEMS) == len(ALL_ITEMS), "Барааны ID давхардсан байна"

# металл дэлгүүрт зарагдахгүй: уурхайгаас (qmine) эсвэл хулгайгаар олдоно
METALS = [replace(m, buyable=False) for m in METALS]
ALL_ITEMS = [replace(i, buyable=False) if i.kind == "metal" else i for i in ALL_ITEMS]
ITEMS = {it.key: it for it in ALL_ITEMS}

# Дэлгүүрийн 5 ангилал: (түлхүүр, emoji, нэр, бараанууд)
CATEGORIES = [
    ("food", "🍞", "Хүнс", FOODS),
    ("digital", "📱", "Дижитал", DIGITAL),
    ("home", "🪑", "Гэр ахуй", HOME),
    ("house", "🏠", "Байшин, машин", CARS + [t for t in TOOLS if t.buyable]),
    ("clothes", "👕", "Хувцас", CLOTHES),
]
CATEGORY_BY_KEY = {c[0]: c for c in CATEGORIES}


def get_item(key: str) -> Item | None:
    return ITEMS.get(key)


def find_items(query: str, pool=None) -> list[Item]:
    """ID, монгол нэр, англи нэрээр бараа хайна (том жижиг үсэг ялгахгүй)."""
    pool = list(pool) if pool is not None else ALL_ITEMS
    q = query.strip().casefold()
    if not q:
        return []
    exact = [i for i in pool if q in (i.key.casefold(), i.name.casefold(), i.en.casefold())]
    if exact:
        return exact[:1]
    starts = [
        i for i in pool
        if i.name.casefold().startswith(q) or i.en.casefold().startswith(q)
        or i.key.casefold().startswith(q)
    ]
    if starts:
        return starts
    return [i for i in pool if q in i.name.casefold() or q in i.en.casefold()]


def stars(n: int) -> str:
    return "⭐" * n


_HOUSE_W = [1 / (it.price ** 0.5) for it in HOUSE_ITEMS]
_RARE = JEWELS + METALS
_RARE_W = [1 / it.price for it in _RARE]


def random_loot(n: int, rare_chance: float = 0.0) -> list[Item]:
    """Хямд бараа олон, үнэтэй бараа ховор олдоно. rare_chance: металл/үнэт эдлэл олох магадлал."""
    out = []
    for _ in range(n):
        if rare_chance and random.random() < rare_chance:
            out.append(random.choices(_RARE, weights=_RARE_W)[0])
        else:
            out.append(random.choices(HOUSE_ITEMS, weights=_HOUSE_W)[0])
    return out


# ---------- тэжээвэр амьтан ----------
@dataclass(frozen=True)
class Pet:
    key: str
    name: str
    emoji: str
    price: int
    perk: str


PETS: list[Pet] = [
    Pet("dog", "Нохой", "🐕", 300_000, "Хулгай, дээрэмд амжилт +10%"),
    Pet("cat", "Муур", "🐈", 200_000, "Ажлын цалин +10%"),
    Pet("falcon", "Шонхор", "🦅", 500_000, "Хулгайгаар олох мөнгө +25%"),
]
PETS_BY_KEY: dict[str, Pet] = {p.key: p for p in PETS}


def get_pet(key: str | None) -> Pet | None:
    return PETS_BY_KEY.get(key) if key else None
