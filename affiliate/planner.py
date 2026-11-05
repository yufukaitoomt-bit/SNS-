"""テーマ別アカウント（accounts.py）の1週間分の投稿計画を作る。

- OLD ORDERを出さない枠: テーマのネタ出し（下書き）。他社情報は【要確認】のまま出す
- OLD ORDERを出す枠: 商品データから投稿文まで作る。1行目に広告表示
1つのネタを4つのSNS（TikTok / Instagram / X / YouTube）向けに書き分ける。
"""
import csv
import io
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .accounts import ACCOUNTS, BIO_FOOTER, OO_DISCLOSURE, PLATFORMS, SHARED_POSTS
from .generator import URL_PLACEHOLDER, WEEKDAYS, _points, _usable, hashtags, product_vars
from .library import ANGLES, DISCLOSURE

LINKS_FILE = Path(__file__).parent / "data" / "account_links.json"

FORMAT = {
    "TikTok": "フォトモード（画像5枚）or 15秒動画",
    "Instagram": "カルーセル（画像5枚）",
    "X": "画像1枚＋本文",
    "YouTube": "ショート（画像スライド動画＋字幕・15秒）",
}
OO_DISCLOSURE_SETTING = {
    "TikTok": DISCLOSURE["TikTok"],
    "Instagram": "本文1行目の【PR】が広告表示（タイアップ投稿ラベルは提携先の設定が必要）",
    "X": DISCLOSURE["X"],
    "YouTube": DISCLOSURE["YouTubeショート"],
}


def load_links() -> Dict[str, Dict[str, str]]:
    """{アカウントID: {SNS: 専用リンク}}。会社から発行されたら data/account_links.json に入れる。"""
    if LINKS_FILE.exists():
        return json.loads(LINKS_FILE.read_text(encoding="utf-8"))
    return {}


def profile(account_id: str) -> str:
    a = ACCOUNTS[account_id]
    return f"{a['bio']}\n{BIO_FOOTER}"


def _oo_days(n: int, offset: int) -> List[int]:
    """1週間(0-6)のうちOLD ORDERを出す日。アカウントごとにずらして同じ日に固まらないようにする。"""
    base = {1: [3], 2: [1, 4], 3: [0, 2, 5]}.get(n, [3])
    return sorted((d + offset) % 7 for d in base)


def _oo_caption(platform: str, hook: str, points: List[str], v: dict, p: dict, angle_key: str, link: str) -> str:
    price = f"（{v['price']}）" if v["price"] else ""
    if platform == "X":
        tags = " ".join(hashtags(p, angle_key)[:2])
        return f"{OO_DISCLOSURE}\n{hook}\n{v['full_name']}{price}\n{tags}\n{link}"
    lines = [OO_DISCLOSURE, hook, ""] + [f"・{pt}" for pt in points[:3]]
    lines += ["", f"{v['full_name']}{price}"]
    if p.get("shipping_note"):
        lines.append(f"※{p['shipping_note']}")
    lines += ["商品ページはプロフィールのリンクから", "", " ".join(hashtags(p, angle_key))]
    return "\n".join(lines)


def _draft_caption(platform: str, account: dict, post: dict) -> str:
    title = f"【下書き】{post['label']}"
    if platform == "X":
        return f"{title}\n{post['brief']}"
    return f"{title}\n{post['brief']}\n\n（構成）1枚目: タイトル／2〜4枚目: 中身／5枚目: まとめ・保存のお願い"


def plan_week(account_id: str, product: dict, start: date, week_index: int = 0,
              links: Optional[Dict[str, Dict[str, str]]] = None) -> List[dict]:
    a = ACCOUNTS[account_id]
    links = links if links is not None else load_links()
    offset = list(ACCOUNTS).index(account_id)
    rng = random.Random(f"{account_id}-{start.isoformat()}")
    oo_days = _oo_days(a["oo_per_week"], offset)

    normal = [x for x in a["posts"] if not x["oo"]]
    oo_posts = [x for x in a["posts"] if x["oo"]]
    if "size" in a["shared"]:
        oo_posts.append(SHARED_POSTS["size"])
    # お手入れは2週に1回、OLD ORDERを出さない日に1回だけ
    care_day = next((d for d in range(7) if d not in oo_days and (d + week_index) % 7 == 5), None) \
        if "care" in a["shared"] and (week_index + offset) % 2 == 0 else None

    rows, used_hooks, ni, oi = [], set(), week_index, week_index
    for d in range(7):
        day = start + timedelta(days=d)
        label = f"{day.isoformat()}({WEEKDAYS[day.weekday()]})"
        if d in oo_days:
            post = oo_posts[oi % len(oo_posts)]
            oi += 1
            angle_key = post.get("angle", a["angles"][0])
            v = product_vars(product, rng)
            pool = [h for h in _usable(ANGLES[angle_key]["hooks"], v) if h not in used_hooks] or [v["name"]]
            hook = rng.choice(pool)
            used_hooks.add(hook)
            points = _points(ANGLES[angle_key], v) or [v["name"]]
            for pl in PLATFORMS:
                link = links.get(account_id, {}).get(pl) or URL_PLACEHOLDER
                rows.append({
                    "date": label, "account": account_id, "account_name": a["name"], "platform": pl,
                    "type": post["label"], "oo": "○", "format": FORMAT[pl], "brief": post["brief"],
                    "caption": _oo_caption(pl, hook, points, v, product, angle_key, link),
                    "disclosure": OO_DISCLOSURE_SETTING[pl],
                })
            continue
        post = SHARED_POSTS["care"] if d == care_day else normal[ni % len(normal)]
        if d != care_day:
            ni += 1
        for pl in PLATFORMS:
            rows.append({
                "date": label, "account": account_id, "account_name": a["name"], "platform": pl,
                "type": post["label"], "oo": "", "format": FORMAT[pl], "brief": post["brief"],
                "caption": _draft_caption(pl, a, post), "disclosure": "",
            })
    return rows


def plan_all(product: dict, start: date, week_index: int = 0, account_ids: Optional[List[str]] = None) -> List[dict]:
    links = load_links()
    rows = []
    for aid in account_ids or list(ACCOUNTS):
        rows += plan_week(aid, product, start, week_index, links)
    return rows


COLUMNS = [("date", "日付"), ("account_name", "アカウント"), ("platform", "SNS"), ("type", "投稿の型"),
           ("oo", "OLD ORDER"), ("format", "形式"), ("brief", "ネタ・指示"), ("caption", "投稿文"),
           ("disclosure", "広告表示の設定")]


def to_csv(rows: List[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([label for _, label in COLUMNS])
    for r in rows:
        w.writerow([r[k] for k, _ in COLUMNS])
    return "﻿" + buf.getvalue()


def to_markdown(account_id: str, rows: List[dict]) -> str:
    a = ACCOUNTS[account_id]
    out = [f"# {a['name']}（{a['group']}）", "", f"> {a['concept']}", "",
           "## プロフィール（4SNS共通）", "```", profile(account_id), "```", "",
           f"- 見た目: {a['visual']}", f"- OLD ORDERを出す回数: 週{a['oo_per_week']}回", ""]
    current = None
    for r in rows:
        if r["account"] != account_id:
            continue
        if r["date"] != current:
            current = r["date"]
            mark = "（OLD ORDER回）" if r["oo"] else ""
            out += [f"## {current}　{r['type']}{mark}", "", f"ネタ・指示: {r['brief']}", ""]
        out += [f"### {r['platform']}｜{r['format']}", "```", r["caption"], "```"]
        if r["disclosure"]:
            out.append(f"☑️ {r['disclosure']}（公開前に確認）")
        out.append("")
    return "\n".join(out)
