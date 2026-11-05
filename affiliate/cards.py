"""投稿計画（planner）からカルーセル画像とスライド動画を作る。

- 画像: 1080x1350（Instagramカルーセル・TikTokフォトモード・X）を3枚（表紙・中身・まとめ）
- 動画: 3枚を1080x1920に並べ替えた15秒のスライド動画（YouTubeショート・TikTok）。音声なし（音楽は各アプリで付ける）
- 背景は図形のコラージュ調（生成AIは使わない → AIラベル不要）
- 他社の写真は使わない。OLD ORDERの商品写真は data/photos/<商品ID>.png|.jpg に置く（無ければ枠だけ描く）
"""
import random
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
PHOTO_DIR = Path(__file__).parent / "data" / "photos"
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
]

# アカウントごとの見た目（accounts.py の visual に合わせる）
STYLES = {
    "zukan":     {"bg": (246, 246, 244), "ink": (25, 25, 25), "accent": (40, 40, 40), "shape": (225, 225, 222), "pattern": "grid"},
    "kstreet":   {"bg": (236, 230, 222), "ink": (60, 52, 48), "accent": (150, 120, 110), "shape": (220, 208, 198), "pattern": "circles"},
    "black":     {"bg": (16, 16, 16), "ink": (240, 240, 240), "accent": (255, 255, 255), "shape": (38, 38, 38), "pattern": "rects"},
    "atsuzoko":  {"bg": (255, 240, 200), "ink": (40, 40, 40), "accent": (240, 110, 60), "shape": (255, 222, 160), "pattern": "circles"},
    "weekend":   {"bg": (232, 240, 236), "ink": (30, 50, 45), "accent": (40, 130, 110), "shape": (205, 225, 218), "pattern": "grid"},
    "furugi":    {"bg": (226, 214, 196), "ink": (60, 45, 35), "accent": (140, 90, 50), "shape": (210, 195, 172), "pattern": "rects"},
    "oshikatsu": {"bg": (250, 236, 244), "ink": (70, 50, 70), "accent": (220, 110, 160), "shape": (240, 215, 230), "pattern": "circles"},
    "campus":    {"bg": (238, 242, 250), "ink": (35, 45, 70), "accent": (70, 110, 200), "shape": (215, 225, 245), "pattern": "grid"},
    "ashimoto":  {"bg": (244, 238, 228), "ink": (30, 30, 30), "accent": (210, 70, 50), "shape": (228, 218, 200), "pattern": "rects"},
}


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise RuntimeError("日本語フォントが見つかりません（IPAゴシック等を入れてください）")


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> List[str]:
    """日本語は単語区切りがないので1文字ずつ詰めて折り返す。"""
    lines = []
    for para in text.split("\n"):
        line = ""
        for ch in para:
            if draw.textlength(line + ch, font=font) > width:
                lines.append(line)
                line = ch
            else:
                line += ch
        lines.append(line)
    return lines


def _background(style: dict, seed: str) -> Image.Image:
    rng = random.Random(seed)
    im = Image.new("RGB", (W, H), style["bg"])
    d = ImageDraw.Draw(im)
    if style["pattern"] == "grid":
        for x in range(0, W, 60):
            d.line([(x, 0), (x, H)], fill=style["shape"], width=1)
        for y in range(0, H, 60):
            d.line([(0, y), (W, y)], fill=style["shape"], width=1)
    for _ in range(7):
        x, y, s = rng.randint(-200, W), rng.randint(-200, H), rng.randint(160, 420)
        if style["pattern"] == "circles":
            d.ellipse([x, y, x + s, y + s], fill=style["shape"])
        elif style["pattern"] == "rects":
            d.rectangle([x, y, x + s, y + int(s * 0.6)], fill=style["shape"])
    return im


def _header(d: ImageDraw.ImageDraw, style: dict, account_name: str, page: int, total: int):
    d.text((60, 70), account_name, font=_font(38), fill=style["ink"], anchor="lm")
    d.text((W - 60, 70), f"{page}/{total}", font=_font(34), fill=style["ink"], anchor="rm")
    d.line([(60, 110), (W - 60, 110)], fill=style["ink"], width=2)


def _text_block(d, style, text: str, top: int, size: int, color=None, width: int = W - 160) -> int:
    font = _font(size)
    y = top
    for line in _wrap(d, text, font, width):
        d.text((W / 2, y), line, font=font, fill=color or style["ink"], anchor="ma")
        y += int(size * 1.45)
    return y


def _product_photo(im: Image.Image, style: dict, product: dict, box) -> None:
    x0, y0, x1, y1 = box
    for ext in ("png", "jpg", "jpeg"):
        path = PHOTO_DIR / f"{product.get('id')}.{ext}"
        if path.exists():
            photo = Image.open(path).convert("RGBA")
            photo.thumbnail((x1 - x0, y1 - y0))
            im.paste(photo, (x0 + (x1 - x0 - photo.width) // 2, y0 + (y1 - y0 - photo.height) // 2), photo)
            return
    d = ImageDraw.Draw(im)  # 写真が届くまでは置き場所だけ描く
    d.rounded_rectangle(box, radius=30, outline=style["accent"], width=4)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2), "OLD ORDER 商品写真\n（data/photos に置く）", font=_font(36),
           fill=style["accent"], anchor="mm", align="center")


def _slides_content(row: dict) -> dict:
    """投稿文（Instagram版）から 表紙・中身・まとめ の文字を取り出す。"""
    # 1行目の広告表示（#PR OLD ORDERスタッフです）は投稿文に残し、画像の表紙には使わない
    lines = [x for x in row["caption"].split("\n") if x.strip() and not x.startswith("#PR")]
    if row["oo"]:
        hook = lines[0]
        points = [x[1:] for x in lines if x.startswith("・")]
        product_line = next((x for x in lines if "OLD ORDER" in x and "¥" in x), "")
        return {"cover": hook, "body": points or [row["type"]], "end": product_line, "draft": False}
    if row.get("ready"):  # テーマ回の完成原稿: 1行目=タイトル、・=中身、最後の文=まとめ
        body = [x[1:] for x in lines if x.startswith("・")]
        rest = [x for x in lines[1:] if not x.startswith("・") and not x.startswith("#")]
        return {"cover": lines[0], "body": body, "end": rest[-1] if rest else "", "draft": False}
    return {"cover": row["type"], "body": [row["brief"]], "end": "保存してあとで見返してね", "draft": True}


def render_post(row: dict, product: dict, out_dir: Path, stem: str) -> List[Path]:
    style = STYLES[row["account"]]
    c = _slides_content(row)
    paths = []
    for page in (1, 2, 3):
        im = _background(style, f"{stem}-{page}")
        d = ImageDraw.Draw(im)
        _header(d, style, row["account_name"], page, 3)
        if page == 1:
            _text_block(d, style, c["cover"], 300, 76)
            if row["oo"]:
                _product_photo(im, style, product, (190, 700, 890, 1150))
            d.text((W / 2, H - 110), "→ スワイプ", font=_font(40), fill=style["accent"], anchor="mm")
        elif page == 2:
            y = 220
            for pt in c["body"][:5]:
                d.rounded_rectangle([90, y, W - 90, y + 8], radius=4, fill=style["accent"])
                y = _text_block(d, style, pt, y + 40, 50) + 40
        else:
            if row["oo"]:
                _product_photo(im, style, product, (190, 220, 890, 760))
                _text_block(d, style, c["end"], 830, 50)
                _text_block(d, style, "商品ページはプロフィールのリンクから", 1000, 42, style["accent"])
                coupon = next((x for x in row["caption"].split("\n") if "KAITO3" in x or "クーポン" in x), "")
                if coupon:
                    _text_block(d, style, coupon.split("（")[0], 1110, 34)
            else:
                _text_block(d, style, c["end"], 560, 56, style["accent"])
        if c["draft"]:
            d.text((W - 60, H - 50), "下書き（中身は【要確認】を埋めてから）", font=_font(26), fill=style["accent"], anchor="rm")
        path = out_dir / f"{stem}_{page}.png"
        im.save(path)
        paths.append(path)
    return paths


def make_video(slides: List[Path], out: Path, style: dict, seconds_each: int = 5) -> Optional[Path]:
    """1080x1350の画像を1080x1920の縦動画にする（上下は背景色）。ffmpegが無ければ作らない。"""
    if not shutil.which("ffmpeg"):
        return None
    tall = []
    for p in slides:
        canvas = Image.new("RGB", (1080, 1920), style["bg"])
        canvas.paste(Image.open(p), (0, (1920 - H) // 2))
        tp = p.with_name(p.stem + "_9x16.png")
        canvas.save(tp)
        tall.append(tp)
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for tp in tall:
        args += ["-loop", "1", "-t", str(seconds_each), "-i", str(tp)]
    n = len(tall)
    args += ["-filter_complex", "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0,format=yuv420p[v]",
             "-map", "[v]", "-r", "30", str(out)]
    subprocess.run(args, check=True)
    for tp in tall:
        tp.unlink()
    return out


def render_week(rows: List[dict], product: dict, out_dir: Path, video: bool = True, only_oo: bool = False) -> int:
    """1日1アカウント1ネタ（Instagram版の行）ごとに画像3枚＋動画1本。"""
    count = 0
    for row in rows:
        if row["platform"] != "Instagram" or (only_oo and not row["oo"]):
            continue
        d = out_dir / row["account"]
        d.mkdir(parents=True, exist_ok=True)
        stem = row["date"][:10]
        slides = render_post(row, product, d, stem)
        if video:
            make_video(slides, d / f"{stem}.mp4", STYLES[row["account"]])
        count += 1
    return count
