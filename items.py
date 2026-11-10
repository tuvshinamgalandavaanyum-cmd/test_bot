import random
import re
from dataclasses import dataclass

SELL_RATE = 0.7  # дэлгүүрт буцааж зарахад үнийн 70%

KIND_EMOJI = {"house": "🏠", "food": "🍽️", "jewel": "💎", "metal": "⛏️", "tool": "🛡️",
              "digital": "📱", "clothes": "👕", "car": "🚗", "realty": "🏘️", "box": "🎁"}


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
    slot: str = ""  # хувцас: hat | top | bottom | shoes | acc
    color: str = ""  # хувцас: зурагт ашиглах өнгө (hex)
    bonus: float = 0.0  # машин: ажлын цалингийн нэмэгдэл (0.05 = 5%)

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
    ("Картон хайрцаг", "Cardboard box", 4_000),
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

_DIGITAL_MOVED = {"TV", "Computer", "Phone", "Headphones", "Speaker", "Charger", "Battery", "Calculator"}

HOUSE_ITEMS: list[Item] = []
DIGITAL: list[Item] = []
for _mn, _en, _price in _HOUSE_RAW:
    _k = _slug(_en)
    if _en in _DIGITAL_MOVED:
        DIGITAL.append(
            Item(
                _k, _mn, _en, _price, "digital",
                emoji=_EMOJI.get(_k, "📱"),
                desc="Дижитал бараа" + (" · байшинд байрлуулна" if _en in _PLACEABLE else ""),
                stock=5 if _price >= 400_000 else None,
                placeable=_en in _PLACEABLE,
            )
        )
        continue
    HOUSE_ITEMS.append(
        Item(
            _k, _mn, _en, _price, "house",
            emoji=_EMOJI.get(_k, "🏠"),
            desc="Гэр ахуйн бараа" + (" · байшинд байрлуулна" if _en in _PLACEABLE else ""),
            stock=5 if _price >= 400_000 else None,
            placeable=_en in _PLACEABLE,
        )
    )

DIGITAL += [
    Item("laptop", "Зөөврийн компьютер", "Laptop", 900_000, "digital", "💻", "Дижитал бараа · байшинд байрлуулна", 5, True),
    Item("tablet", "Таблет", "Tablet", 500_000, "digital", "📲", "Дижитал бараа", 5),
    Item("smartwatch", "Ухаалаг цаг", "Smartwatch", 350_000, "digital", "⌚", "Дижитал бараа"),
    Item("camera", "Камер", "Camera", 700_000, "digital", "📷", "Дижитал бараа", 5),
    Item("console", "Тоглоомын консол", "Game console", 800_000, "digital", "🎮", "Дижитал бараа · байшинд байрлуулна", 5, True),
    Item("drone", "Дрон", "Drone", 1_200_000, "digital", "🛸", "Дижитал бараа", 3),
    Item("router", "Роутер", "Router", 60_000, "digital", "📶", "Дижитал бараа"),
]
DIGITAL.sort(key=lambda i: i.price)

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


# ---------- брэнд хувцас (үнээр эрэмбэлсэн) ----------
# (ID, нэр, англи, үнэ, slot, өнгө, emoji)
_CLOTHES_RAW = [
    ("zara_tee", "Zara футболк", "Zara T-shirt", 35_000, "top", "#e5e7eb", "👕"),
    ("hm_hoodie", "H&M цамц", "H&M Hoodie", 60_000, "top", "#6b7280", "🧥"),
    ("levis_jeans", "Levi's жийнс", "Levi's Jeans", 90_000, "bottom", "#2563eb", "👖"),
    ("nike_cap", "Nike малгай", "Nike Cap", 80_000, "hat", "#111827", "🧢"),
    ("adidas_pants", "Adidas өмд", "Adidas Pants", 120_000, "bottom", "#111827", "👖"),
    ("puma_tee", "Puma футболк", "Puma T-shirt", 130_000, "top", "#dc2626", "👕"),
    ("converse", "Converse гутал", "Converse", 150_000, "shoes", "#f9fafb", "👟"),
    ("nike_air", "Nike Air гутал", "Nike Air", 280_000, "shoes", "#ef4444", "👟"),
    ("deel", "Монгол дээл", "Mongol Deel", 300_000, "top", "#1d4ed8", "🥋"),
    ("mongol_hat", "Монгол малгай", "Mongol Hat", 250_000, "hat", "#b91c1c", "🎩"),
    ("mongol_boots", "Монгол гутал", "Mongol Boots", 350_000, "shoes", "#7c2d12", "🥾"),
    ("adidas_jacket", "Adidas хүрэм", "Adidas Jacket", 400_000, "top", "#0f172a", "🧥"),
    ("north_face", "North Face пуховик", "North Face Jacket", 650_000, "top", "#f59e0b", "🧥"),
    ("supreme_hoodie", "Supreme цамц", "Supreme Hoodie", 900_000, "top", "#b91c1c", "🧥"),
    ("ray_ban", "Ray-Ban шил", "Ray-Ban", 700_000, "acc", "#111827", "🕶️"),
    ("gucci_belt", "Gucci бүс", "Gucci Belt", 1_100_000, "acc", "#16a34a", "🪢"),
    ("lv_bag", "Louis Vuitton цүнх", "Louis Vuitton Bag", 2_500_000, "acc", "#92400e", "👜"),
    ("balenciaga", "Balenciaga гутал", "Balenciaga Sneakers", 1_600_000, "shoes", "#e5e7eb", "👟"),
    ("gucci_suit", "Gucci костюм", "Gucci Suit", 3_500_000, "top", "#1f2937", "🤵"),
    ("dior_dress", "Dior даашинз", "Dior Dress", 4_500_000, "top", "#be185d", "👗"),
    ("armani_pants", "Armani өмд", "Armani Pants", 1_900_000, "bottom", "#1f2937", "👖"),
    ("hermes_hat", "Hermès малгай", "Hermes Hat", 2_000_000, "hat", "#ea580c", "🎩"),
    ("prada_shoes", "Prada гутал", "Prada Shoes", 2_800_000, "shoes", "#0f172a", "👞"),
]
CLOTHES: list[Item] = [
    Item(k, mn, en, price, "clothes", emoji, f"Брэнд хувцас · {sl}", 5 if price >= 1_500_000 else None,
         slot=sl, color=col)
    for (k, mn, en, price, sl, col, emoji) in _CLOTHES_RAW
]
CLOTHES.sort(key=lambda i: i.price)
SLOT_NAMES = {"hat": "Толгойн хувцас", "top": "Дээд хувцас", "bottom": "Доод хувцас",
              "shoes": "Гутал", "acc": "Гоёл чимэглэл"}

# ---------- машин ----------
CARS: list[Item] = [
    Item("prius", "Toyota Prius", "Toyota Prius", 1_200_000, "car", "🚗", "Ажлын цалин +2%", stock=5, bonus=0.02),
    Item("landcruiser", "Land Cruiser", "Land Cruiser", 3_500_000, "car", "🚙", "Ажлын цалин +4%", stock=4, bonus=0.04),
    Item("lexus", "Lexus LX", "Lexus LX", 6_000_000, "car", "🚙", "Ажлын цалин +5%", stock=3, bonus=0.05),
    Item("bmw", "BMW M5", "BMW M5", 9_000_000, "car", "🏎️", "Ажлын цалин +6%", stock=3, bonus=0.06),
    Item("g63", "Mercedes G63", "Mercedes G63", 14_000_000, "car", "🚙", "Ажлын цалин +8%", stock=2, bonus=0.08),
    Item("lambo", "Lamborghini", "Lamborghini", 25_000_000, "car", "🏎️", "Ажлын цалин +10%", stock=1, bonus=0.10),
]

# ---------- байшин (дэлгүүрт харагдах мөр; авахад qhouse buy-тай ижил) ----------
from houses import HOUSES as _HOUSES  # noqa: E402

REALTY: list[Item] = [
    Item(h.key, h.name, h.name, h.price, "realty", h.emoji,
         f"{h.rooms} өрөө · өрөө бүрт {h.slots} эд зүйл")
    for h in _HOUSES
]

# ---------- хайрцаг ----------
BOXES: list[Item] = [
    Item("box", "Хайрцаг (Box)", "Box", 50_000, "box", "📦", "Санамсаргүй бараа · 2% Revive Active"),
    Item("case", "Big Cash Case", "Case", 100_000, "box", "💼", "Мөнгө хожих кейс · хоосон ч гарч болно"),
    Item("chest", "Сан (Chest)", "Chest", 250_000, "box", "🧰", "Металл, үнэт эдлэл гарна"),
]

# ---------- хэрэгсэл ----------
TOOLS: list[Item] = [
    Item("shield", "Хамгаалалтын бамбай", "Shield", 120_000, "tool", "🛡️",
         "2.5 цаг дээрэм, хакердалтаас хамгаална · qblock"),
    Item("luck_potion", "Азын сав (Luck Poison)", "Luck potion", 80_000, "tool", "🍀",
         "1 цаг азын магадлал +10%"),
    Item("money_potion", "Мөнгөний сав (Money Poison)", "Money potion", 100_000, "tool", "💰",
         "1 цаг ажил, өдрийн цалин +10%"),
]
# дэлгүүрт зарагдахгүй, зөвхөн тоглоомоор / админаас олдоно
SPECIAL: list[Item] = [
    Item("revive", "Revive Active", "Revive Active", 2_000_000, "tool", "💖",
         "Үхсэн дүрийг амилуулна · qinv use revive"),
    Item("gold_ore", "Алтан хүдэр", "Gold ore", 40_000, "metal", "🪨", "Малтаж олсон алтан хүдэр"),
]

ALL_ITEMS: list[Item] = (
    HOUSE_ITEMS + DIGITAL + JEWELS + METALS + FOODS + CLOTHES + CARS + REALTY + BOXES + TOOLS + SPECIAL
)
ITEMS: dict[str, Item] = {it.key: it for it in ALL_ITEMS}
assert len(ITEMS) == len(ALL_ITEMS), "Барааны ID давхардсан байна"

# Дэлгүүрийн ангилал: (түлхүүр, emoji, нэр, бараанууд)
CATEGORIES = [
    ("food", "🍞", "Хүнс", FOODS),
    ("digital", "📱", "Дижитал", DIGITAL),
    ("home", "🏠", "Гэр ахуй", HOUSE_ITEMS),
    ("house", "🏘️", "Байшин, машин", sorted(REALTY + CARS, key=lambda i: i.price)),
    ("clothes", "👕", "Брэнд хувцас", CLOTHES),
    ("jewel", "💎", "Үнэт эдлэл", JEWELS),
    ("metal", "⛏️", "Металл", METALS),
    ("box", "🎁", "Хайрцаг, кейс", BOXES),
    ("tool", "🛡️", "Хэрэгсэл", TOOLS),
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


LOOT_POOL = HOUSE_ITEMS + DIGITAL
_HOUSE_W = [1 / (it.price ** 0.5) for it in LOOT_POOL]
_RARE = JEWELS + METALS
_RARE_W = [1 / it.price for it in _RARE]


def random_loot(n: int, rare_chance: float = 0.0) -> list[Item]:
    """Хямд бараа олон, үнэтэй бараа ховор олдоно. rare_chance: металл/үнэт эдлэл олох магадлал."""
    out = []
    for _ in range(n):
        if rare_chance and random.random() < rare_chance:
            out.append(random.choices(_RARE, weights=_RARE_W)[0])
        else:
            out.append(random.choices(LOOT_POOL, weights=_HOUSE_W)[0])
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
