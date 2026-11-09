# Mongol Economy Bot (Jungle City)

Python + discord.py + SQLite. Угтвар: `q` эсвэл `!` (том жижиг үсэг хамаагүй: `qwork`, `!work`, `! work`).

## Суулгах
1. `.env` файлд `DISCORD_TOKEN=...` (токеноо хэнд ч бүү үзүүл). `PREFIX=q,!`
2. Discord Developer Portal → Bot → **Message Content Intent** асаана.
3. `pip install -r requirements.txt`
4. `py main.py` (Windows) эсвэл `python main.py`

Хуучин `bot.db` байвал шинэ багана, хүснэгтүүд автоматаар нэмэгдэнэ.

## Командууд
`qhelp` гэж бичвэл ◀ ▶ товч, ангилал сонгох цэстэй тусламж гарна.
Үндсэн: bal, daily, dep, with, give, lb · Ажил: work, jobs, workout
Дэлгүүр: shop, buy, inv, sell, gift, eat, petshop, buypet
Байшин: house, safe · Гэмт хэрэг: steal, rob, hack, block, bail
Казино (банкнаас): cf, dice, slots, mf, duel, draw · Эможи: slap, hug, kiss, pat ...

## Шинэ боломжууд (v2)
- **Бүртгэл**: character үүсгээгүй хүн `q<команд>` бичихэд бот ажиллахгүй, оронд нь **Хариулах** товч гарна. Асуулт: хүйс → нас (1-100) + улс → үсний өнгө. `qprofile` дээр 2D character зурагтай.
- **Хувцас**: `qshop clothes` → `qbuy <ID>` → `qwear <ID>` (character дээр харагдана). **Гэрлэлт**: `qmarry @хүн` (Бөгж хэрэгтэй), `qdivorce`, `qdate`.
- **Дэлгүүр 5 ангилал**: food, digital, home, house (машин), clothes.
- **Татвар 10%**: `daily`, `work`-оос. Сан: `qtreasury`. **Giveaway**: `qgiveaway <дүн|all> <30m|2h|1d> [ялагч]` (Owner/Admin, сангаас).
- **Өлсөлт**: 3 хоног хоолгүй бол 2 цаг тутам хэтэвчний 2.5% хасна; 7 хоног хоолгүй бол **үхнэ** → `Revive Active` (`qinv use revive`) эсвэл `qadmin revive`. Тоглоомоос 0.1% олдоно.
- **Хайрцаг**: `qbox`, `qbox buy box|case|chest`, `qopen box|case|chest`. Box: 2% Revive Active, 10% азын хор, 10% мөнгөний хор. Case: Big Cash (RTP ~96%).
- **Уурхай**: `qmine` (40% алт, 1.5 цаг). **Дасгалжуулагч**: `qcoach` (200,000₮ → хүч +3).
- **Утас**: `qphone` / `qutas` (банк, эрүүл мэнд, татвар, сервер). `qinfo`, `qping`.
- **Admin**: `qadmin` (слайд тайлбар) — give/take/set/item/remove/revive/kill/feed/jail/free/strength/cooldown/reset/treasury.
- **+18 сэдэвтэй эможи**: `qflirt qtease qseduce qlovebite qsparkle` — зөвхөн NSFW сувагт, шууд бус (explicit биш).

Тохируулга: `utils.py` (TAX_RATE, HUNGER_DAYS, DEAD_DAYS), `cogs/loot.py` (MINE_*, BOX_*, CASE_TIERS), `cogs/phone.py` (REQUIRE_PHONE).
`pip install -r requirements.txt` дахин ажиллуулна (Pillow нэмэгдсэн).
