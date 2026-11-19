"""アカウントのアイコン（英字ロゴ）を作る。python -m affiliate.icons → out/icons/final/<ID>.png

丸く切り抜かれても欠けないよう、文字は中央の幅560px・高さ480pxに収める。色は cards.STYLES。
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .accounts import ACCOUNTS
from .cards import STYLES, _font

LOGO_FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
WORDS = {"black": ["BLACK", "SNKR", "CLUB"], "kstreet": ["K-STREET", "LAB"], "zukan": ["ATSUZOKO", "ZUKAN"],
         "atsuzoko": ["ATSUZOKO", "CLUB"], "weekend": ["WEEKEND", "WHERE?"], "furugi": ["FURUGI", "WALK"],
         "oshikatsu": ["OSHI", "DAY", "FIT"], "campus": ["CAMPUS", "7DAYS"], "ashimoto": ["ASHIMOTO", "ZUKAN"]}
S = 1080


def make(account_id: str, out_dir: Path) -> Path:
    style, words = STYLES[account_id], WORDS[account_id]
    im = Image.new("RGB", (S, S), style["bg"])
    d = ImageDraw.Draw(im)
    size = 260
    while True:
        f = ImageFont.truetype(LOGO_FONT, size)
        if max(d.textlength(w, font=f) for w in words) <= 560 and len(words) * size * 0.95 <= 480:
            break
        size -= 5
    step = int(size * 0.95)
    y = (S - step * len(words)) // 2 - 40
    for w in words:
        d.text((S / 2, y), w, font=f, fill=style["ink"], anchor="mt")
        y += step
    d.line([(400, y + 25), (680, y + 25)], fill=style["accent"], width=6)
    sub = style["accent"] if account_id != "black" else (160, 160, 160)
    d.text((S / 2, y + 50), ACCOUNTS[account_id]["name"], font=_font(34), fill=sub, anchor="mt")
    path = out_dir / f"{account_id}.png"
    im.save(path)
    return path


if __name__ == "__main__":
    out = Path("out/icons/final")
    out.mkdir(parents=True, exist_ok=True)
    for aid in ACCOUNTS:
        print(make(aid, out))
