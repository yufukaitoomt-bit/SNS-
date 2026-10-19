"""商品データ → 1週間分の台本・投稿文を生成する。"""
import csv
import io
import random
import re
from datetime import date, timedelta
from typing import List, Optional

from .library import ANGLES, BANNED_PHRASES, CTA, DEFAULT_PLATFORMS, DISCLOSURE, FORMATS, PERSONAS, TEXT_ONLY_PLATFORMS, X_FORMATS, X_QUESTIONS

URL_PLACEHOLDER = "【URL未設定】"
X_LIMIT = 140  # 全角換算の目安（URLは別枠で23文字扱い）
WEEKDAYS = "月火水木金土日"
PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _yen(n: Optional[int]) -> str:
    return f"¥{n:,}" if n else ""


def product_vars(p: dict, rng: random.Random) -> dict:
    price = p.get("price") or 0
    compare = p.get("compare_price") or 0
    discount = p.get("discount") or 0
    features = [f for f in p.get("features", []) if f]
    colors = [c for c in p.get("colors", []) if c]
    return {
        "name": p.get("name", ""),
        "full_name": f"{p.get('brand', '')} {p.get('name', '')}".strip(),
        "brand": p.get("brand", ""),
        "category": p.get("category") or "スニーカー",
        "price": _yen(price),
        "compare_price": _yen(compare) if compare > price else "",
        "diff": _yen(compare - price) if compare > price else "",
        "celebrity": p.get("celebrity", ""),
        "sole_height": p.get("sole_height", ""),
        "size_tip": p.get("size_tip", ""),
        "discount": _yen(discount) if 0 < discount < price else "",
        "sale_price": _yen(price - discount) if 0 < discount < price else "",
        "feature": rng.choice(features) if features else "",
        "color": rng.choice(colors) if colors else "実物",
        "colors": " / ".join(colors),
    }


def _deal_line(v: dict, via: str) -> str:
    return f"🎁 {via}から買うと{v['discount']}オフ（実質{v['sale_price']}）" if v["discount"] else ""


def _fill(template: str, v: dict) -> Optional[str]:
    """プレースホルダを埋める。空になる項目があれば None（そのテンプレは使わない）。"""
    for key in PLACEHOLDER_RE.findall(template):
        if key in v and not v[key]:
            return None
    return template.format_map(v)


def _usable(items: List[dict], v: dict) -> List[str]:
    out = []
    for h in items:
        if all(v.get(r) for r in h.get("requires", [])):
            filled = _fill(h["t"], v)
            if filled:
                out.append(filled)
    return out


def _points(angle: dict, v: dict) -> List[str]:
    return [s for s in (_fill(t, v) for t in angle["points"]) if s]


def hashtags(p: dict, angle_key: str) -> List[str]:
    angle = ANGLES[angle_key]
    tags = ["#PR"]
    tags += [t if t.startswith("#") else "#" + t for t in p.get("hashtags", []) if t]
    if p.get("brand"):
        tags.append("#" + re.sub(r"\s+", "", p["brand"]))
    tags += angle["tags"]
    if angle.get("celebrity_tags") and p.get("celebrity"):
        tags.append("#" + re.sub(r"\s+", "", p["celebrity"]) + "私服")
    seen, uniq = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq[:10]


def _angles_for(persona: dict, product: dict) -> List[str]:
    enabled = [a for a in product.get("angles", []) if a in ANGLES]
    if not enabled:
        enabled = [a for a in ANGLES if a != "discount"]
    if product.get("discount") and "discount" not in enabled:
        enabled.insert(1, "discount")
    # 商品の主軸(先頭)を優先しつつ、ペルソナが得意な軸と重なるものを使う
    overlap = [a for a in persona["angles"] if a in enabled]
    if not overlap:
        return enabled[:2]
    if enabled[0] not in overlap:  # 主軸はどのキャラにも必ず混ぜる
        overlap.insert(1, enabled[0])
    return overlap


def _caption(hook: str, points: List[str], v: dict, p: dict, tone: str, rng: random.Random, tags: List[str]) -> str:
    lines = [hook, ""]
    lines += [f"・{pt}" for pt in points[:3]]
    lines += ["", f"{v['full_name']}（{v['price']}）" if v["price"] else v["full_name"]]
    if v["discount"]:
        lines.append(_deal_line(v, "プロフィールのリンク"))
    if p.get("shipping_note"):
        lines.append(f"※{p['shipping_note']}")
    lines += [rng.choice(CTA[tone]), "", " ".join(tags)]
    return "\n".join(lines)


def _x_post(hook: str, point: str, v: dict, p: dict, angle_key: str, fmt: str, rng: random.Random) -> str:
    """X/Threads用。fmt は library.X_FORMATS のキー。"""
    url = p.get("url") or URL_PLACEHOLDER
    tags = " ".join(hashtags(p, angle_key)[:3])  # Xはタグ多すぎると伸びにくい
    price = f"（{v['price']}）" if v["price"] else ""
    deal = _deal_line(v, "このリンク")
    ship = f"※{p['shipping_note']}" if p.get("shipping_note") else ""

    if fmt == "question":
        q = rng.choice(X_QUESTIONS if v["colors"] else X_QUESTIONS[1:])
        colors = f"\n{v['colors']}" if "色" in q else ""
        return f"{hook}\n\n{q}{colors}\n\n{tags}\n\n――リプ欄に貼る――\n{v['full_name']}{price}\n{deal}\n{url}".replace("\n\n\n", "\n\n")
    if fmt == "thread":
        reply = "\n".join(x for x in [f"{v['full_name']}{price}", deal, ship, url] if x)
        return f"【1】{hook}\n\n{point}\n\n↓詳細はリプ欄\n{tags}\n\n【2（リプ）】\n{reply}"
    if fmt == "deal" and v["discount"]:
        body = "\n".join(x for x in [hook, "", f"{v['full_name']}", f"通常{v['price']} → このリンクから{v['sale_price']}", ship] if x is not None)
        return f"{body}\n{tags}\n{url}"

    lines = [hook, "", point, f"{v['full_name']}{price}"]
    if deal:
        lines.append(deal)
    if ship:
        lines.append(ship)
    body = "\n".join(lines)
    if len(body) > X_LIMIT - 30:  # 長すぎる場合はポイント行と注意書きを落とす
        body = "\n".join([hook, f"{v['full_name']}{price}"] + ([deal] if deal else []))
    return f"{body}\n{tags}\n{url}"


def _x_formats(v: dict) -> List[str]:
    fmts = ["single", "thread", "question"]
    if v["discount"]:
        fmts.append("deal")
    return fmts


def generate_week(
    product: dict,
    start: Optional[date] = None,
    days: int = 7,
    persona_keys: Optional[List[str]] = None,
    x_for_all: bool = True,
    x_per_day: int = 3,
    platforms: Optional[List[str]] = None,
) -> List[dict]:
    """1ペルソナ×1日=動画1本（＋X版）。速報系ペルソナはXを1日 x_per_day 本。
    platforms で出す媒体を絞る（既定は TikTok と X）。"""
    platforms = platforms or DEFAULT_PLATFORMS
    if start is None:
        today = date.today()
        start = today + timedelta(days=(7 - today.weekday()) % 7 or 7)  # 次の月曜
    persona_keys = persona_keys or list(PERSONAS)
    seed = f"{product.get('id', product.get('name'))}-{start.isoformat()}"
    posts = []

    for pk in persona_keys:
        persona = PERSONAS[pk]
        persona_platforms = [pl for pl in persona["platforms"] if pl in platforms]
        if not persona_platforms and not ("X" in platforms and x_for_all):
            continue
        rng = random.Random(f"{seed}-{pk}")
        angle_keys = _angles_for(persona, product)
        text_only = all(pl in TEXT_ONLY_PLATFORMS for pl in persona["platforms"])
        video_platforms = [pl for pl in persona_platforms if pl not in TEXT_ONLY_PLATFORMS]
        x_on = "X" in platforms and x_for_all
        used_hooks = set()

        def pick_hook(angle_key, v):
            pool = _usable(ANGLES[angle_key]["hooks"], v)
            fresh = [h for h in pool if h not in used_hooks] or pool
            h = rng.choice(fresh) if fresh else v["name"]
            used_hooks.add(h)
            return h

        for d in range(days):
            day = start + timedelta(days=d)
            day_label = f"{day.isoformat()}({WEEKDAYS[day.weekday()]})"
            angle_key = angle_keys[d % len(angle_keys)]
            angle = ANGLES[angle_key]
            v = product_vars(product, rng)
            points = _points(angle, v) or [v["name"]]

            if text_only:
                for i in range(x_per_day):
                    ak = angle_keys[(d + i) % len(angle_keys)]
                    v2 = product_vars(product, rng)
                    pts = _points(ANGLES[ak], v2) or [v2["name"]]
                    fmts = _x_formats(v2)
                    xf = fmts[(d * x_per_day + i) % len(fmts)]
                    if xf == "deal":  # 特典告知は必ず特典のフックで
                        ak = "discount"
                        pts = _points(ANGLES[ak], v2)
                    hook = pick_hook(ak, v2)
                    posts.append({
                        "date": day_label, "persona": pk, "persona_label": persona["label"],
                        "platform": " / ".join(persona_platforms), "angle": ANGLES[ak]["label"],
                        "format": X_FORMATS[xf], "hook": hook, "script": "",
                        "caption": _x_post(hook, rng.choice(pts), v2, product, ak, xf, rng), "hashtags": "",
                    })
                continue

            fkey = persona["formats"][d % len(persona["formats"])]
            hook = pick_hook(angle_key, v)
            point = rng.choice(points)
            script_vars = {**v, "hook": hook, "point": point}
            script = "\n".join(s.format_map(script_vars) for s in FORMATS[fkey]["script"])
            tags = hashtags(product, angle_key)
            if video_platforms:
                posts.append({
                    "date": day_label, "persona": pk, "persona_label": persona["label"],
                    "platform": " / ".join(video_platforms), "angle": angle["label"],
                    "format": FORMATS[fkey]["label"], "hook": hook, "script": script,
                    "caption": _caption(hook, points, v, product, persona["tone"], rng, tags),
                    "hashtags": " ".join(tags),
                })
            if x_on:
                xf = _x_formats(v)[d % len(_x_formats(v))]
                x_angle, x_hook, x_point = angle_key, hook, point
                if xf == "deal":  # 特典告知は必ず特典のフックで
                    x_angle = "discount"
                    x_hook = pick_hook(x_angle, v)
                    x_point = _points(ANGLES[x_angle], v)[0]
                posts.append({
                    "date": day_label, "persona": pk, "persona_label": persona["label"],
                    "platform": "X", "angle": ANGLES[x_angle]["label"],
                    "format": X_FORMATS[xf] + ("（同じ動画を添付）" if video_platforms else ""),
                    "hook": x_hook, "script": "",
                    "caption": _x_post(x_hook, x_point, v, product, x_angle, xf, rng), "hashtags": "",
                })

    for post in posts:
        post["disclosure"] = " / ".join(DISCLOSURE[pl] for pl in post["platform"].split(" / ") if pl in DISCLOSURE)
    posts.sort(key=lambda x: (x["date"], x["persona"]))
    return posts


def check_claims(product: dict) -> List[str]:
    """商品データに根拠のない効能・比較表現が入っていないか確認する。"""
    text = " ".join(str(v) for k, v in product.items() if k != "memo")
    return [w for w in BANNED_PHRASES if w in text]


COLUMNS = [
    ("date", "日付"), ("persona", "ペルソナ"), ("persona_label", "キャラ"), ("platform", "媒体"),
    ("angle", "訴求軸"), ("format", "フォーマット"), ("hook", "フック"), ("script", "台本"),
    ("caption", "投稿文"), ("hashtags", "ハッシュタグ"), ("disclosure", "広告表示の設定"),
]


def to_csv(posts: List[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([label for _, label in COLUMNS])
    for p in posts:
        w.writerow([p[k] for k, _ in COLUMNS])
    return "﻿" + buf.getvalue()  # BOM付き: Excel/スプレッドシートで文字化けしない


def to_markdown(product: dict, posts: List[dict]) -> str:
    out = [f"# {product.get('brand', '')} {product.get('name', '')} 投稿カレンダー", "",
           "> 投稿文の#PRに加えて、各投稿の ☑️ の広告表示設定を必ずONにすること。", ""]
    if not product.get("url"):
        out += [f"> ⚠️ URL未設定。投稿文中の `{URL_PLACEHOLDER}` を差し替えてください。", ""]
    current = None
    for p in posts:
        if p["date"] != current:
            current = p["date"]
            out += [f"## {current}", ""]
        out.append(f"### {p['persona']}｜{p['persona_label']}｜{p['platform']}｜{p['angle']}｜{p['format']}")
        if p["script"]:
            out += ["**台本**", "```", p["script"], "```"]
        out += ["**投稿文**", "```", p["caption"], "```"]
        if p.get("disclosure"):
            out.append(f"☑️ {p['disclosure']}")
        out.append("")
    return "\n".join(out)
