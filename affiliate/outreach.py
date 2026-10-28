"""TikTok Shop のクリエイター依頼セット（DM・依頼書・管理表）を商品データから作る。

ギフティング（商品は返却不要）＋売上に応じた報酬で動画作成を依頼する前提。報酬率など未決の項目は【】のまま出るので、決まったら埋めて使う。
"""
import csv
import io
from typing import Optional

from .generator import _yen

TBD = "【未定】"

TRACKER_COLUMNS = [
    "アカウント", "フォロワー", "ジャンル", "DM送信日", "返信", "サイズ", "カラー",
    "発送日", "到着日", "投稿期限", "投稿日", "動画URL", "プロモーション表示OK", "再生数", "販売数", "売上", "報酬", "次回も送るか", "メモ",
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
          sender: str = "", brand_account: str = "", perks: Optional[list] = None) -> dict:
    """commission は%（例: 12）。None なら【未定】。perks は売れた人向けの特典（1行1つ）。"""
    perks = [x for x in (perks or []) if x]
    name = f"{p.get('brand', '')} {p.get('name', '')}".strip()
    rate = f"{commission:g}%" if commission else TBD
    sender = sender or "【担当者名】"
    account = f"（{brand_account}）" if brand_account else ""
    facts = _facts(p) or ["【公式サイトに書いてある事実を入れる】"]

    perk_line = "・たくさん売れた方には、報酬アップなどの特典もあります\n" if perks else ""
    dm_first = f"""はじめまして、{p.get('brand', '')}{account}のPR担当の{sender}です。
いつも投稿を拝見していて、コーデの雰囲気が私たちのスニーカーにぴったりだと思いご連絡しました。

TikTok Shopで「{name}」を紹介していただけるクリエイターさんを探しています。
・商品を1足お送りします（返却不要。サイズとカラーを選べます）
・動画の🛒商品リンク経由で売れた分は、売上の{rate}が報酬として入ります
・お願いしたいのは、届いてから{deadline_days}日以内に🛒商品リンク付きの動画を1本投稿していただくことです
{perk_line}
ご興味があれば、お気軽にお返事ください！"""

    dm_followup = f"""先日ご連絡した{p.get('brand', '')}の{sender}です。
「{name}」のご紹介の件、もしご興味があれば、サイズとカラーだけ教えていただければすぐお送りします。
難しければ、お返事なしで大丈夫です。ありがとうございました！"""

    dm_accepted = f"""ありがとうございます！とても嬉しいです。
TikTok Shopから「{name}」のコラボ招待（売上の{rate}・無料サンプル付き）をお送りしました。

1. TikTokのクリエイターセンター →「コラボ招待」から招待を承諾してください（7日以内）
2. そのままサンプル申請で、サイズとカラーを選んでください
   ※お届け先は申請画面で入力されるので、DMで送っていただく必要はありません

承認したら発送します。投稿のお願い事項を下にまとめたので、届く前に目を通していただけると助かります。"""

    fact_lines = "\n".join(f"・{f}" for f in facts)
    perk_block = ("■ たくさん売れた方への特典\n" + "\n".join(f"・{x}" for x in perks) + "\n\n") if perks else ""
    brief = f"""【{name} 投稿のお願い】

■ 投稿内容
・TikTokに動画1本（サンプルが届いてから{deadline_days}日以内。公開後は最低3日間は消さないでください ※TikTok Shopのサンプルのルールです）
・投稿時に🛒商品リンクで「{name}」を追加してください
・実際に履いた様子が分かる動画だと、とても嬉しいです（コーデ・サイズ感・開封など自由）

■ 売れやすい動画のコツ（参考です。ご自身のスタイルで大丈夫です）
・最初の2秒で「何の動画か」が分かる一言を入れる（例:「この厚底スニーカー、正直レビュー」）
・全身を正面と横から映す（コーデ全体での見え方が一番知りたいところです）
・「普段◯cm → これは◯cmを選んだ」をはっきり言う（購入前に一番聞かれる質問です）
・ソールの高さは定規などで実物を見せる
・自然光で撮ると、色が実物に近く見えます
・最後に「画面の🛒から買えます」と一言入れる

■ 動画の例（どれか1つでOK）
・着回し: 1足で3〜5コーデを2秒ずつ切り替え
・比較: いつものスニーカーと{name}を並べて履き比べ
・サイズ感: 普段のサイズと選んだサイズ、つま先・かかとの余り
・開封: 箱を開けて実物の色を見せ、そのまま履いて歩く

■ 必ずお願いしたいこと（法律で決まっているため）
・投稿の設定で「コンテンツの開示（ブランドコンテンツ）」を必ずONにしてください
  （動画に「プロモーション」と表示され、これが広告の表示になります。本文に#PRを書く必要はありません）
・動画や本文で「案件じゃない」「自腹で買った」などとは言わないでください
・この動画を他のSNSにも載せる場合は、そちらでもタイアップ表示か#PRを付けてください

■ 言わないでほしいこと
・公式に書いていない効果（例:「細見えする」「疲れにくい」「足が痛くならない」）
・他ブランドを悪く言う比較
※ 見た目やサイズ感の感想を、ご自身の言葉で話していただくのは大歓迎です

■ 使っていただける事実（公式情報）
{fact_lines}

■ 報酬
・🛒商品リンク経由の売上の{rate}（TikTok Shopから自動で支払われます）

{perk_block}■ その他
・商品は返却不要です
・動画を{p.get('brand', '')}の公式アカウントや広告で使わせていただく場合は、事前にご相談します"""

    perk_note = ("\n\n特典の条件はこちらです。\n" + "\n".join(f"・{x}" for x in perks)) if perks else ""
    dm_report = f"""【{name} 今月の結果】
いつもありがとうございます！今月の🛒商品リンク経由の結果です。

・販売数: 【◯】足
・報酬: 【¥◯】
・いちばん売れた動画: 【URL】（【◯】足）

【この動画のどこが良かったか、ひとこと】{perk_note}

来月も楽しみにしています！"""

    return {"dm_first": dm_first, "dm_followup": dm_followup, "dm_accepted": dm_accepted,
            "brief": brief, "dm_report": dm_report}


def tracker_csv() -> str:
    buf = io.StringIO()
    csv.writer(buf).writerow(TRACKER_COLUMNS)
    return "﻿" + buf.getvalue()


def to_markdown(p: dict, kit: dict) -> str:
    sections = [("① 最初のDM", "dm_first"), ("② 返信がないとき（5日後に1回だけ）", "dm_followup"),
                ("③ OKをもらったら", "dm_accepted"), ("④ 依頼書（③と一緒に送る）", "brief"),
                ("⑤ 月1回の結果報告", "dm_report")]
    out = [f"# {p.get('brand', '')} {p.get('name', '')} クリエイター依頼セット（TikTok Shop）", ""]
    if TBD in kit["dm_first"]:
        out += [f"> ⚠️ 報酬率が {TBD} のままです。決まったら埋めてから送ってください。", ""]
    for title, key in sections:
        out += [f"## {title}", "```", kit[key], "```", ""]
    return "\n".join(out)
