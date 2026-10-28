"""TikTok Shop のクリエイター依頼セット（DM・依頼書・管理表）を商品データから作る。

商品を送る前提。報酬率など未決の項目は【】のまま出るので、決まったら埋めて使う。
"""
import csv
import io
from typing import Optional

from .generator import _yen

TBD = "【未定】"

TRACKER_COLUMNS = [
    "アカウント", "フォロワー", "ジャンル", "DM送信日", "返信", "サイズ", "カラー",
    "発送日", "到着日", "投稿期限", "投稿日", "動画URL", "再生数", "販売数", "売上", "報酬", "次回も送るか", "メモ",
]


def _facts(p: dict) -> list:
    price = p.get("shop_price") or p.get("price")
    facts = [f"価格: {_yen(price)}（税込）"] if price else []
    if p.get("sole_height"):
        facts.append(f"ソールの高さ: {p['sole_height']}（公式表記）")
    if p.get("size_tip"):
        facts.append(f"サイズ: {p['size_tip']}（公式の案内）")
    facts += [f for f in p.get("features", []) if f]
    if p.get("colors"):
        facts.append("カラー: " + " / ".join(p["colors"]))
    return facts


def build(p: dict, commission: Optional[float] = None, deadline_days: int = 14,
          sender: str = "", brand_account: str = "") -> dict:
    """commission は%（例: 12）。None なら【未定】。"""
    name = f"{p.get('brand', '')} {p.get('name', '')}".strip()
    rate = f"{commission:g}%" if commission else TBD
    sender = sender or "【担当者名】"
    account = f"（{brand_account}）" if brand_account else ""
    facts = _facts(p) or ["【公式サイトに書いてある事実を入れる】"]

    dm_first = f"""はじめまして、{p.get('brand', '')}{account}のPR担当の{sender}です。
いつも投稿を拝見していて、コーデの雰囲気が私たちのスニーカーにぴったりだと思いご連絡しました。

TikTok Shopで「{name}」を紹介していただけるクリエイターさんを探しています。
・商品を1足お送りします（返却不要。サイズとカラーを選べます）
・動画の🛒商品リンク経由で売れた分は、売上の{rate}が報酬として入ります
・お願いしたいのは、届いてから{deadline_days}日以内に🛒商品リンク付きの動画を1本投稿していただくことです

ご興味があれば、お気軽にお返事ください！"""

    dm_followup = f"""先日ご連絡した{p.get('brand', '')}の{sender}です。
「{name}」のご紹介の件、もしご興味があれば、サイズとカラーだけ教えていただければすぐお送りします。
難しければ、お返事なしで大丈夫です。ありがとうございました！"""

    dm_accepted = f"""ありがとうございます！とても嬉しいです。
以下を教えてください。
・サイズ（普段履いているスニーカーのサイズも）
・カラー
・お届け先（お名前・住所・電話番号）

発送したらご連絡します。投稿のお願い事項を下にまとめたので、届く前に目を通していただけると助かります。"""

    fact_lines = "\n".join(f"・{f}" for f in facts)
    brief = f"""【{name} 投稿のお願い】

■ 投稿内容
・TikTokに動画1本（届いてから{deadline_days}日以内）
・投稿時に🛒商品リンクで「{name}」を追加してください
・実際に履いた様子が分かる動画だと、とても嬉しいです（コーデ・サイズ感・開封など自由）

■ 必ずお願いしたいこと（法律で決まっているため）
・投稿の設定で「コンテンツの開示」をONにしてください（「プロモーション」と表示されます）
・本文に #PR を入れてください

■ 言わないでほしいこと
・公式に書いていない効果（例:「細見えする」「疲れにくい」「足が痛くならない」）
・他ブランドを悪く言う比較
※ 見た目やサイズ感の感想を、ご自身の言葉で話していただくのは大歓迎です

■ 使っていただける事実（公式情報）
{fact_lines}

■ 報酬
・🛒商品リンク経由の売上の{rate}（TikTok Shopから自動で支払われます）

■ その他
・商品は返却不要です
・動画を{p.get('brand', '')}の公式アカウントや広告で使わせていただく場合は、事前にご相談します"""

    return {"dm_first": dm_first, "dm_followup": dm_followup, "dm_accepted": dm_accepted, "brief": brief}


def tracker_csv() -> str:
    buf = io.StringIO()
    csv.writer(buf).writerow(TRACKER_COLUMNS)
    return "﻿" + buf.getvalue()


def to_markdown(p: dict, kit: dict) -> str:
    sections = [("① 最初のDM", "dm_first"), ("② 返信がないとき（5日後に1回だけ）", "dm_followup"),
                ("③ OKをもらったら", "dm_accepted"), ("④ 依頼書（③と一緒に送る）", "brief")]
    out = [f"# {p.get('brand', '')} {p.get('name', '')} クリエイター依頼セット（TikTok Shop）", ""]
    if TBD in kit["dm_first"]:
        out += [f"> ⚠️ 報酬率が {TBD} のままです。決まったら埋めてから送ってください。", ""]
    for title, key in sections:
        out += [f"## {title}", "```", kit[key], "```", ""]
    return "\n".join(out)
