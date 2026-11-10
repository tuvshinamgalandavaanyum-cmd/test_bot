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
    "work": ("💼", "Санамсаргүй ажил хийж цалин авах (1 цаг тутам).", "{p}work", "{p}work"),
    "jobs": ("📋", "Ажлын жагсаалт.", "{p}jobs", "{p}jobs"),
    "workout": ("🏋️", "Дасгал хийж хүч нэмэх. Хүч нэмэгдэх тусам ажлын орлого өснө (2 цаг тутам).", "{p}workout", "{p}workout"),
    "shop": ("🛍️", "Дэлгүүр. Ангилал, хуудсаар үзнэ.", "{p}shop [food | digital | home | house | clothes | jewel | metal | box | tool]", "{p}shop jewel"),
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
    "register": ("📝", "Дүрээ бүртгүүлэх (хүйс, нас, улс, арьсны өнгө).", "{p}register", "{p}register"),
    "profile": ("👤", "2D дүр, мэдээллээ харах.", "{p}profile [@хэрэглэгч]", "{p}profile @Bat"),
    "wear": ("👕", "Цүнхний хувцсыг өмсөх.", "{p}wear <ID>", "{p}wear nike_air"),
    "undress": ("👕", "Хувцас тайлах.", "{p}undress <hat | top | bottom | shoes | acc | ID>", "{p}undress hat"),
    "mine": ("⛏️", "Алт малтах (40% магадлал, 30 минут тутам).", "{p}mine", "{p}mine"),
    "open": ("🎁", "Хайрцаг, кейс, сан нээх.", "{p}open <box | case | chest> [тоо]", "{p}open case 2"),
    "revive": ("💖", "Revive Active ашиглан үхсэн хүнийг амилуулах.", "{p}revive [@хэрэглэгч]", "{p}revive @Bat"),
    "marry": ("💍", "Гэр бүл болох санал тавих (бөгж хэрэгтэй).", "{p}marry <@хэрэглэгч>", "{p}marry @Bat"),
    "divorce": ("💔", "Салах (100,000₮).", "{p}divorce", "{p}divorce"),
    "couple": ("💞", "Гэр бүлийн мэдээлэл.", "{p}couple", "{p}couple"),
    "date": ("🌹", "Ханьтайгаа болзох (30,000₮).", "{p}date", "{p}date"),
    "giveaway": ("🎉", "Админ: татварын сангаас giveaway.", "{p}giveaway <дүн | pool> <10m | 2h | 1d> [ялагчийн тоо]", "{p}giveaway 500k 1h 2"),
    "pool": ("🏛️", "Татварын сангийн үлдэгдэл.", "{p}pool", "{p}pool"),
    "admin": ("🛠️", "Админы цэс ба командууд.", "{p}admin [give | take | set | item | revive | ...]", "{p}admin give @Bat 1m"),
    "info": ("ℹ️", "Бот, сервер, статистик.", "{p}info", "{p}info"),
    "addmoney": ("🛠️", "Bot Owner: хэрэглэгчид мөнгө нэмэх.", "{p}addmoney <@хэрэглэгч> <дүн>", "{p}addmoney @Bat 1m"),
    "help": ("📖", "Командын тусламж.", "{p}help [апп]", "{p}help casino"),
}

EMOTE_USAGE = ("🎭", "Бусдад эможи үзүүлэх.", "{p}{name} <@хэрэглэгч>", "{p}{name} @Bat")


def usage_embed(ctx, command) -> discord.Embed:
    p = ctx.clean_prefix
    name = command.name if command else "help"
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
