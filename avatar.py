"""2D character зургийг Pillow-оор зурна (гадны зураг шаардахгүй)."""
import io

from PIL import Image, ImageDraw

from items import CLOTHES_STYLE

HAIR_COLORS = {
    "black": ("Хар", "#1f1b1b"),
    "brown": ("Бор", "#6b4226"),
    "blonde": ("Шар", "#e6c15a"),
    "red": ("Улаан", "#b83a1e"),
    "white": ("Цагаан", "#e5e7eb"),
    "blue": ("Цэнхэр", "#3b82f6"),
    "pink": ("Ягаан", "#f472b6"),
    "green": ("Ногоон", "#22c55e"),
    "purple": ("Нил ягаан", "#8b5cf6"),
}

W, H, SS = 300, 420, 2  # SS: өнгөлгөөний (supersampling) үржвэр
SKIN = "#f3cfa8"


def _age_scale(age: int) -> tuple[float, float]:
    """(өндрийн итгэлцүүр, толгойн итгэлцүүр)"""
    if age < 6:
        return 0.55, 1.45
    if age < 13:
        return 0.68, 1.3
    if age < 18:
        return 0.85, 1.1
    if age >= 70:
        return 0.93, 1.0
    return 1.0, 1.0


def _gradient(draw: ImageDraw.ImageDraw, top: tuple, bottom: tuple):
    for y in range(H * SS):
        t = y / (H * SS)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (W * SS, y)], fill=c)


def render_character(gender: str, age: int, hair: str, outfit: dict | None = None) -> io.BytesIO:
    outfit = outfit or {}
    hair_hex = HAIR_COLORS.get(hair, HAIR_COLORS["black"])[1]
    female = gender == "female"
    h, hs = _age_scale(age)

    img = Image.new("RGB", (W * SS, H * SS), "white")
    d = ImageDraw.Draw(img)
    if female:
        _gradient(d, (253, 226, 243), (251, 182, 206))
    else:
        _gradient(d, (219, 234, 254), (147, 197, 253))

    def s(v: float) -> int:
        return int(v * SS)

    cx, ground = W / 2, 385
    d.ellipse([s(cx - 70), s(ground - 8), s(cx + 70), s(ground + 12)], fill=(0, 0, 0, 40) if False else "#00000022")

    def slot_color(slot: str, default: str) -> str:
        key = outfit.get(slot)
        if key and key in CLOTHES_STYLE:
            return CLOTHES_STYLE[key][1]
        return default

    full_key = outfit.get("full")
    full_col = CLOTHES_STYLE[full_key][1] if full_key in CLOTHES_STYLE else None
    top_col = full_col or slot_color("top", "#9ca3af" if not female else "#fbcfe8")
    bottom_col = full_col or slot_color("bottom", "#374151")
    shoe_col = slot_color("shoes", "#1f2937")

    leg_h, torso_h = 100 * h, 105 * h
    head_r = 40 * h * hs
    shoe_h = 12 * h
    legs_top = ground - leg_h
    torso_top = legs_top - torso_h
    head_cy = torso_top - head_r + 6 * h
    torso_w = 74 if not female else 66
    skirt = full_key in ("dress", "deel") or (female and full_key is None and outfit.get("bottom") is None and False)

    # ---- дал/хөл ----
    if skirt:
        d.polygon(
            [(s(cx - torso_w / 2), s(torso_top + torso_h * 0.7)), (s(cx + torso_w / 2), s(torso_top + torso_h * 0.7)),
             (s(cx + torso_w / 2 + 22), s(ground - 18 * h)), (s(cx - torso_w / 2 - 22), s(ground - 18 * h))],
            fill=bottom_col,
        )
        for dx in (-16, 16):
            d.rectangle([s(cx + dx - 9), s(ground - 22 * h), s(cx + dx + 9), s(ground - shoe_h)], fill=SKIN)
    else:
        for dx in (-17, 17):
            d.rectangle([s(cx + dx - 14), s(legs_top), s(cx + dx + 14), s(ground - shoe_h)], fill=bottom_col)
    for dx in (-17, 17):
        d.rounded_rectangle([s(cx + dx - 18), s(ground - shoe_h), s(cx + dx + 18), s(ground)], radius=s(5), fill=shoe_col)

    # ---- гар ----
    arm_w = 16
    for side in (-1, 1):
        x0 = cx + side * (torso_w / 2 + 2)
        d.rounded_rectangle([s(x0 - arm_w / 2 + side * 4), s(torso_top + 6 * h), s(x0 + arm_w / 2 + side * 4),
                             s(torso_top + 92 * h)], radius=s(7), fill=top_col if outfit.get("top") or full_col else SKIN)
        d.ellipse([s(x0 - 9 + side * 4), s(torso_top + 86 * h), s(x0 + 9 + side * 4), s(torso_top + 104 * h)], fill=SKIN)

    # ---- их бие ----
    d.rounded_rectangle([s(cx - torso_w / 2), s(torso_top), s(cx + torso_w / 2), s(torso_top + torso_h)],
                        radius=s(14), fill=top_col)
    if full_key == "suit":
        d.polygon([(s(cx - 10), s(torso_top)), (s(cx + 10), s(torso_top)), (s(cx), s(torso_top + 45 * h))], fill="#f9fafb")
        d.polygon([(s(cx - 3), s(torso_top + 10 * h)), (s(cx + 3), s(torso_top + 10 * h)), (s(cx), s(torso_top + 40 * h))], fill="#dc2626")
    if full_key == "deel":
        d.line([(s(cx - torso_w / 2 + 6), s(torso_top + 8)), (s(cx + 14), s(torso_top + torso_h * 0.8))], fill="#fde047", width=s(4))
        d.rectangle([s(cx - torso_w / 2), s(torso_top + torso_h * 0.62), s(cx + torso_w / 2), s(torso_top + torso_h * 0.72)], fill="#dc2626")

    # ---- хүзүү, ороолт ----
    d.rectangle([s(cx - 9 * h), s(head_cy + head_r - 6), s(cx + 9 * h), s(torso_top + 6)], fill=SKIN)
    if outfit.get("neck"):
        d.rounded_rectangle([s(cx - 22 * h), s(torso_top - 6 * h), s(cx + 22 * h), s(torso_top + 12 * h)],
                            radius=s(6), fill=slot_color("neck", "#f97316"))

    # ---- үс (ар тал) ----
    if female:
        d.rounded_rectangle([s(cx - head_r - 6), s(head_cy - head_r * 0.6), s(cx + head_r + 6), s(head_cy + head_r + 55 * h)],
                            radius=s(24), fill=hair_hex)

    # ---- толгой ----
    d.ellipse([s(cx - head_r), s(head_cy - head_r), s(cx + head_r), s(head_cy + head_r)], fill=SKIN)

    # ---- үс (урд тал) ----
    d.pieslice([s(cx - head_r - 3), s(head_cy - head_r - 5), s(cx + head_r + 3), s(head_cy + head_r - 5)],
               start=180, end=360, fill=hair_hex)
    if female:
        d.rectangle([s(cx - head_r - 3), s(head_cy - 4), s(cx - head_r + 9), s(head_cy + head_r * 0.9)], fill=hair_hex)
        d.rectangle([s(cx + head_r - 9), s(head_cy - 4), s(cx + head_r + 3), s(head_cy + head_r * 0.9)], fill=hair_hex)
    else:
        d.rectangle([s(cx - head_r + 2), s(head_cy - head_r * 0.5), s(cx + head_r - 2), s(head_cy - head_r * 0.15)], fill=hair_hex)

    # ---- нүүр ----
    eye_y = head_cy + head_r * 0.05
    for dx in (-0.38, 0.38):
        ex = cx + dx * head_r
        d.ellipse([s(ex - 4), s(eye_y - 4), s(ex + 4), s(eye_y + 4)], fill="#111827")
    d.arc([s(cx - head_r * 0.3), s(head_cy + head_r * 0.2), s(cx + head_r * 0.3), s(head_cy + head_r * 0.6)],
          start=15, end=165, fill="#9f1239", width=s(3))
    if age >= 60:
        for dx in (-0.38, 0.38):
            ex = cx + dx * head_r
            d.line([(s(ex - 8), s(eye_y - 12)), (s(ex + 8), s(eye_y - 14))], fill="#e5e7eb", width=s(3))
    elif age < 13:
        for dx in (-0.62, 0.62):
            ex = cx + dx * head_r
            d.ellipse([s(ex - 5), s(eye_y + 7), s(ex + 5), s(eye_y + 14)], fill="#fda4af")

    face_key = outfit.get("face")
    if face_key:
        col = slot_color("face", "#111827")
        for dx in (-0.38, 0.38):
            ex = cx + dx * head_r
            if face_key == "sunglasses":
                d.rounded_rectangle([s(ex - 13), s(eye_y - 8), s(ex + 13), s(eye_y + 8)], radius=s(4), fill=col)
            else:
                d.ellipse([s(ex - 12), s(eye_y - 10), s(ex + 12), s(eye_y + 10)], outline=col, width=s(3))
        d.line([(s(cx - head_r * 0.38 + 12), s(eye_y)), (s(cx + head_r * 0.38 - 12), s(eye_y))], fill=col, width=s(3))

    # ---- малгай ----
    if outfit.get("hat"):
        col = slot_color("hat", "#92400e")
        top = head_cy - head_r
        d.ellipse([s(cx - head_r - 14), s(top + 2), s(cx + head_r + 14), s(top + 20)], fill=col)
        d.rounded_rectangle([s(cx - head_r + 6), s(top - 22), s(cx + head_r - 6), s(top + 12)], radius=s(10), fill=col)

    out = img.resize((W, H), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "PNG")
    buf.seek(0)
    return buf
