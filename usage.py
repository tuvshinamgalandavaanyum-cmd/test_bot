import discord

from utils import reply

# команд -> (emoji, тайлбар, хэрэглээ, жишээ)  ({p} = угтвар)
USAGE = {
    "bal": ("💰", "Хэтэвч, банк, хөрөнгө, хоол, хүчний мэдээлэл харах.", "{p}bal [@хэрэглэгч]", "{p}bal @Bat"),
    "give": ("💸", "Бусад хэрэглэгчид мөнгө шилжүүлэх (шимтгэл 200₮).", "{p}give <@хэрэглэгч> <дүн>", "{p}give @Bat 50k"),
    "daily": ("🎁", "24 цаг тутамд өдрийн цалингаа авах.", "{p}daily", "{p}daily"),
    "bank": ("🏦", "Банкны дансны мэдээллээ харах.", "{p}bank", "{p}bank"),
    "dep": ("📥", "Хэтэвчээсээ банкны данс руу мөнгө хийх (шимтгэл 200₮).", "{p}dep [дүн | all]", "{p}dep 100k"),
    "with": ("📤", "Банкны данснаас хэтэвч рүү мөнгө авах (шимтгэл 200₮).", "{p}with [дүн | all]", "{p}with 75k"),
    "lb": ("🏆", "Серверийн хамгийн баян хэрэглэгчдийн жагсаалт.", "{p}lb [bank | wallet | total]", "{p}lb total"),
    "setmoney": ("💵", "Bot Owner: хэрэглэгчийн хэтэвчийн мөнгийг тохируулах.", "{p}setmoney <@хэрэглэгч> <дүн>", "{p}setmoney @Bat 1m"),
    "addmoney": ("🛠️", "Bot Owner: хэрэглэгчид мөнгө нэмэх.", "{p}addmoney <@хэрэглэгч> <дүн>", "{p}addmoney @Bat 1m"),
    "work": ("💼", "Санамсаргүй ажил хийж цалин авах (1 цаг тутам).", "{p}work", "{p}work"),
    "jobs": ("📋", "Ажлын жагсаалт.", "{p}jobs", "{p}jobs"),
    "workout": ("🏋️", "Дасгал хийж хүч нэмэх. Хүч нэмэгдэх тусам ажлын орлого өснө (2 цаг тутам).", "{p}workout", "{p}workout"),
    "shop": ("🛍️", "Дэлгүүр. Ангилал, хуудсаар үзнэ.", "{p}shop [food | house | jewel | metal | tool]", "{p}shop jewel"),
    "buy": ("🛒", "Дэлгүүрээс бараа худалдаж авна.", "{p}buy <ID> [тоо]", "{p}buy bread 3"),
    "inv": ("🎒", "Цүнхээ харах, ашиглах.", "{p}inv [use <ID> [тоо]]", "{p}inv use shield"),
    "sell": ("💰", "Цүнхний барааг дэлгүүрт 70%-ийн үнээр зарна. `all` бол бүгдийг.", "{p}sell <ID | all> [тоо]", "{p}sell chair 2"),
    "gift": ("🎁", "Бараагаа өөр хүнд бэлэглэнэ.", "{p}gift <ID> <@хэрэглэгч> [тоо]", "{p}gift gold @Bat 2"),
    "eat": ("😋", "Хоол идэж цатгана (7 хоногт 1 удаа өлсөнө).", "{p}eat <ID> [тоо]", "{p}eat buuz 2"),
    "petshop": ("🐾", "Тэжээвэр амьтны дэлгүүр.", "{p}petshop", "{p}petshop"),
    "buypet": ("🐕", "Тэжээвэр амьтан худалдаж авна.", "{p}buypet <dog | cat | falcon>", "{p}buypet dog"),
    "house": ("🏠", "Байшин худалдаж авах, өрөөнд эд зүйл байрлуулах.", "{p}house [shop | buy <ID> | <өрөө> [use|unuse <ID> [тоо]]]", "{p}house bedroom use computer"),
    "safe": ("🔐", "Байшин доторх сейф. Мөнгө, эд зүйлээ хамгаална.", "{p}safe [buy | put <ID|money> <тоо> | take <ID|money> <тоо>]", "{p}safe put money 500k"),
    "steal": ("🏚️", "Байшинд нууцаар орж хулгай хийх.", "{p}steal [1-5]", "{p}steal 3"),
    "rob": ("🥷", "Өөр хүний халаасыг дээрэмдэх.", "{p}rob <@хэрэглэгч>", "{p}rob @Bat"),
    "hack": ("💻", "Өөр хүний банкны данс руу хакердах (байшиндаа компьютертой байх ёстой).", "{p}hack <@хэрэглэгч>", "{p}hack @Bat"),
    "block": ("🛡️", "Хамгаалалтын бамбай ашиглаж 2.5 цаг дээрэм, хакераас хамгаалагдана.", "{p}block", "{p}block"),
    "bail": ("⛓️", "Шорон дахь хугацаагаа барьцаа төлж эрт гарах.", "{p}bail", "{p}bail"),
    "cf": ("🪙", "Зоос шидэж азаа сориорой (зөвхөн банкны данснаас, дээд 250,000₮).", "{p}cf <дүн> [сүүл | тоо]", "{p}cf 50k сүүл"),
    "dice": ("🎲", "Шоо хаяж 1-6-г таа (зөвхөн банкнаас, дээд 250,000₮).", "{p}dice <дүн> <1-6>", "{p}dice 20k 4"),
    "slots": ("🎰", "Слот машин (зөвхөн банкнаас, дээд 250,000₮).", "{p}slots <дүн>", "{p}slots 10k"),
    "mf": ("💣", "Minefield: аюулгүй талбай нээгээд бөмбөгөөс зайлаарай.", "{p}mf <дүн>", "{p}mf 30k"),
    "duel": ("⚔️", "Эсрэг тоглогчтой 3 раунд чулуу-хайч-даавуу дуэль.", "{p}duel <@хэрэглэгч> <дүн>", "{p}duel @Bat 50k"),
    "draw": ("🔫", "Quick Draw: GO! гарахад хамгийн хурдан буудсан хүн ялна.", "{p}draw <@хэрэглэгч> <дүн>", "{p}draw @Bat 50k"),
    "help": ("📖", "Командын тусламж.", "{p}help", "{p}help"),
    "profile": ("👤", "Character профайл харах. Анх удаа бол асуултууд эхэлнэ.", "{p}profile [@хэрэглэгч]", "{p}profile @Bat"),
    "wear": ("👕", "Хувцас өмсөх (цүнхэнд байх ёстой). `off` бол бүгдийг тайлна.", "{p}wear <ID | off>", "{p}wear hoodie"),
    "marry": ("💍", "Гэрлэх санал тавина (Бөгж хэрэгтэй).", "{p}marry <@хэрэглэгч>", "{p}marry @Bat"),
    "divorce": ("💔", "Гэрлэлтээ цуцлах.", "{p}divorce", "{p}divorce"),
    "date": ("💞", "Хосоороо болзож хайрын оноо авах (6 цаг тутам).", "{p}date", "{p}date"),
    "box": ("🎁", "Хайрцгийн дэлгүүр. Box / Case / Chest.", "{p}box [buy <box|case|chest> [тоо]]", "{p}box buy case 2"),
    "open": ("🎁", "Хайрцаг, кейс, авдар нээх.", "{p}open <box|case|chest> [тоо]", "{p}open box 3"),
    "mine": ("⛏️", "Алт ухах (40% олдоно, 1.5 цаг тутам).", "{p}mine", "{p}mine"),
    "coach": ("🏋️", "Хувийн дасгалжуулагчид мөнгө төлж хүч нэмэх.", "{p}coach", "{p}coach"),
    "treasury": ("🏛️", "Татварын сангийн үлдэгдэл.", "{p}treasury", "{p}treasury"),
    "giveaway": ("🎉", "Owner/Admin: татварын сангаас giveaway.", "{p}giveaway <дүн|all> <30m|2h|1d> [ялагчийн тоо]", "{p}giveaway 500k 1h 2"),
    "phone": ("📱", "Утас: банк, эрүүл мэнд, татвар, сервер апп.", "{p}phone", "{p}phone"),
    "info": ("📡", "Серверийн мэдээлэл.", "{p}info", "{p}info"),
    "ping": ("🏓", "Ботын ping.", "{p}ping", "{p}ping"),
    "admin": ("🛠️", "Owner/Admin: слайдтай тайлбар. Дэлгэрэнгүй: `{p}admin`.", "{p}admin", "{p}admin"),
    "admin give": ("💰", "Admin: мөнгө өгөх.", "{p}admin give <@хүн> <дүн>", "{p}admin give @Bat 1m"),
    "admin take": ("💸", "Admin: мөнгө хасах.", "{p}admin take <@хүн> <дүн>", "{p}admin take @Bat 100k"),
    "admin set": ("💵", "Admin: хэтэвч тохируулах.", "{p}admin set <@хүн> <дүн>", "{p}admin set @Bat 0"),
    "admin jail": ("⛓️", "Admin: шоронд хийх.", "{p}admin jail <@хүн> [минут]", "{p}admin jail @Bat 30"),
    "admin treasury": ("🏛️", "Admin: татварын сан.", "{p}admin treasury <add|take> <дүн>", "{p}admin treasury add 1m"),
}

EMOTE_USAGE = ("🎭", "Бусдад эможи үзүүлэх.", "{p}{name} <@хэрэглэгч>", "{p}{name} @Bat")


def usage_embed(ctx, command) -> discord.Embed:
    p = ctx.clean_prefix
    name = command.qualified_name if command else "help"
    info = USAGE.get(name)
    if info is None:
        emoji, desc, usage, example = EMOTE_USAGE
    else:
        emoji, desc, usage, example = info
    fmt = lambda s: s.format(p=p, name=name)
    embed = discord.Embed(
        title=f"🔍 Командын тусламж: {p}{name}",
        description=f"{emoji} {desc}",
        color=0x3B82F6,
    )
    embed.add_field(name="Хэрэглээ (Usage)", value=f"`{fmt(usage)}`", inline=False)
    embed.add_field(name="Жишээ", value=f"`{fmt(example)}`", inline=False)
    embed.set_footer(text="<> доторх зүйл заавал, [] доторх зүйл заавал биш")
    return embed


async def send_usage(ctx, command=None):
    await reply(ctx, embed=usage_embed(ctx, command or ctx.command))
