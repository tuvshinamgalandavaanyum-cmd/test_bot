# Mongol Economy Bot

Python + discord.py + SQLite. Угтвар: `q` эсвэл `!` (том жижиг үсэг хамаагүй).

## Суулгах
1. `.env` файлд `DISCORD_TOKEN=...` (токеноо хэнд ч бүү үзүүл), `PREFIX=q,!`
2. Discord Developer Portal → Bot → **Message Content Intent**, **Server Members Intent** асаана.
3. `pip install -r requirements.txt`
4. `py main.py` (Windows) эсвэл `python main.py`

Хуучин `bot.db` шинэ баганууд руугаа автоматаар шилждэг. Хуучин тоглогчид эхний командаар дахин бүртгүүлнэ.

## Гол боломжууд
- **Бүртгэл:** эхний командаар хүйс, нас, улс, арьсны өнгө сонгоно. Бүртгүүлэх хүртэл бот ажиллахгүй.
- **Профайл:** `qprofile` 2D дүр, `qwear`, `qundress` (брэнд хувцас).
- **Өлсөлт:** 3 хоног хоолгүй бол 2 цаг тутам хэтэвчний 2.5% хасагдана; 7 хоног хоолгүй бол үхнэ. `Revive Active` (хайрцгаас 2%, тоглоомоор 0.1%) амилуулна.
- **Татвар:** `work`, `daily`-ийн 10% татварын санд орно. Админ `qgiveaway` хийнэ.
- **Дэлгүүр:** food, digital, home, house (байшин+машин), clothes, jewel, metal, box, tool.
- **Хайрцаг:** `qopen box|case|chest`, `qmine` (алт 40%), luck/money potion.
- **Романс:** `qmarry`, `qdate`, `qcouple`, `qdivorce`.
- **Утас:** `qhelp` / `qphone` / `qutas`.
- **Админ:** `qadmin` (слайд цэс). Ботын эзэн `qadmin op @хүн`-ээр админ томилно.
- **Казино:** cf, dice, slots, mf, duel, draw (банкнаас).
- **Мэдээлэл:** `qinfo`.
