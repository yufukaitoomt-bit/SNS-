"""商品データ → 1週間分の台本・投稿文を生成する。"""
import csv
import io
import random
import re
from datetime import date, timedelta
from typing import List, Optional

from .library import ANGLES, CTA, FORMATS, PERSONAS, TEXT_ONLY_PLATFORMS

URL_PLACEHOLDER = "【URL未設定】"
X_LIMIT = 140  # 全角換算の目安（URLは別枠で23文字扱い）
WEEKDAYS = "月火水木金土日"
PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _yen(n: Optional[int]) -> str:
    return f"¥{n:,}" if n else ""


def product_vars(p: dict, rng: random.Random) -> dict:
    price = p.get("price") or 0
    compare = p.get("compare_price") or 0
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
        "feature": rng.choice(features) if features else "",
        "color": rng.choice(colors) if colors else "実物",
    }


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
        enabled = list(ANGLES)
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
    if p.get("shipping_note"):
        lines.append(f"※{p['shipping_note']}")
    lines += [rng.choice(CTA[tone]), "", " ".join(tags)]
    return "\n".join(lines)


def _x_post(hook: str, point: str, v: dict, p: dict, angle_key: str) -> str:
    """X/Threads用。リンクを本文に直接入れられるので、短く言い切ってURLで締める。"""
    url = p.get("url") or URL_PLACEHOLDER
    tags = hashtags(p, angle_key)[:3]  # Xはタグ多すぎると伸びにくい
    price = f"（{v['price']}）" if v["price"] else ""
    body = f"{hook}\n\n{point}\n{v['full_name']}{price}"
    if p.get("shipping_note"):
        body += f"\n※{p['shipping_note']}"
    # 本文が長すぎる場合はポイント行を落とす
    if len(body) > X_LIMIT - 30:
        body = f"{hook}\n{v['full_name']}{price}"
    return f"{body}\n{' '.join(tags)}\n{url}"


def generate_week(
    product: dict,
    start: Optional[date] = None,
    days: int = 7,
    persona_keys: Optional[List[str]] = None,
    x_for_all: bool = True,
    x_per_day: int = 3,
) -> List[dict]:
    """1ペルソナ×1日=動画1本（＋X版）。速報系ペルソナはXを1日 x_per_day 本。"""
    if start is None:
        today = date.today()
        start = today + timedelta(days=(7 - today.weekday()) % 7 or 7)  # 次の月曜
    persona_keys = persona_keys or list(PERSONAS)
    seed = f"{product.get('id', product.get('name'))}-{start.isoformat()}"
    posts = []

    for pk in persona_keys:
        persona = PERSONAS[pk]
        rng = random.Random(f"{seed}-{pk}")
        angle_keys = _angles_for(persona, product)
        text_only = all(pl in TEXT_ONLY_PLATFORMS for pl in persona["platforms"])
        video_platforms = [pl for pl in persona["platforms"] if pl not in TEXT_ONLY_PLATFORMS]
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
                    posts.append({
                        "date": day_label, "persona": pk, "persona_label": persona["label"],
                        "platform": " / ".join(persona["platforms"]), "angle": ANGLES[ak]["label"],
                        "format": "テキスト", "hook": pick_hook(ak, v2), "script": "",
                        "caption": "", "hashtags": "",
                    })
                    posts[-1]["caption"] = _x_post(posts[-1]["hook"], rng.choice(pts), v2, product, ak)
                continue

            fkey = persona["formats"][d % len(persona["formats"])]
            hook = pick_hook(angle_key, v)
            point = rng.choice(points)
            script_vars = {**v, "hook": hook, "point": point}
            script = "\n".join(s.format_map(script_vars) for s in FORMATS[fkey]["script"])
            tags = hashtags(product, angle_key)
            posts.append({
                "date": day_label, "persona": pk, "persona_label": persona["label"],
                "platform": " / ".join(video_platforms), "angle": angle["label"],
                "format": FORMATS[fkey]["label"], "hook": hook, "script": script,
                "caption": _caption(hook, points, v, product, persona["tone"], rng, tags),
                "hashtags": " ".join(tags),
            })
            if x_for_all:
                posts.append({
                    "date": day_label, "persona": pk, "persona_label": persona["label"],
                    "platform": "X", "angle": angle["label"],
                    "format": "テキスト（同じ動画を添付可）", "hook": hook, "script": "",
                    "caption": _x_post(hook, point, v, product, angle_key), "hashtags": "",
                })

    posts.sort(key=lambda x: (x["date"], x["persona"]))
    return posts


COLUMNS = [
    ("date", "日付"), ("persona", "ペルソナ"), ("persona_label", "キャラ"), ("platform", "媒体"),
    ("angle", "訴求軸"), ("format", "フォーマット"), ("hook", "フック"), ("script", "台本"),
    ("caption", "投稿文"), ("hashtags", "ハッシュタグ"),
]


def to_csv(posts: List[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([label for _, label in COLUMNS])
    for p in posts:
        w.writerow([p[k] for k, _ in COLUMNS])
    return "﻿" + buf.getvalue()  # BOM付き: Excel/スプレッドシートで文字化けしない


def to_markdown(product: dict, posts: List[dict]) -> str:
    out = [f"# {product.get('brand', '')} {product.get('name', '')} 投稿カレンダー", ""]
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
        out += ["**投稿文**", "```", p["caption"], "```", ""]
    return "\n".join(out)
