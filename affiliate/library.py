"""訴求軸・投稿フォーマット・ペルソナの定義。

テンプレート内で使えるプレースホルダ:
  {name} 商品名 / {brand} ブランド名 / {price} 価格表記 / {feature} 特徴(ランダム1つ)
  {color} カラー(ランダム1つ) / {celebrity} 着用有名人 / {compare_price} 他店価格 / {diff} 差額
  {category} カテゴリ(スニーカー等)

requires に書いた項目が商品に入っていないテンプレートは使われない
(例: 有名人が未設定の商品で「◯◯着用」と出さないため)。
"""

# ─── 訴求軸 ──────────────────────────────────────────────
ANGLES = {
    "korean": {
        "label": "韓国系・K-POP",
        "hooks": [
            {"t": "韓国の子がみんな履いてる{category}、日本で買えるの知ってた？"},
            {"t": "{celebrity}が履いてる{category}、{price}で買える", "requires": ["celebrity"]},
            {"t": "{celebrity}着用の{name}、実物レビューします", "requires": ["celebrity"]},
            {"t": "韓国っぽコーデは足元で9割決まる"},
            {"t": "オルチャンになりたいなら{category}から変えて"},
            {"t": "ソウルの古着屋で見かけた系の{category}、やっと見つけた"},
        ],
        "points": [
            "韓国ファッションと相性がいいシルエット",
            "ワイドパンツ・ミニスカどっちにも合う",
            "{celebrity}の私服っぽく仕上がる",
        ],
        "tags": ["#韓国ファッション", "#韓国コーデ", "#オルチャンコーデ", "#kpop好きと繋がりたい"],
        "celebrity_tags": True,
    },
    "street": {
        "label": "ストリート・スケート",
        "hooks": [
            {"t": "ストリート好きが今いちばん欲しい{category}"},
            {"t": "スケーター上がりのブランド、{brand}って知ってる？"},
            {"t": "ゴツめ{category}探してる人、これ見て"},
            {"t": "ダボパンに合わせる{category}、正解はこれ"},
        ],
        "points": ["ボリュームのあるシルエット", "ダボっとしたパンツに映える", "{feature}"],
        "tags": ["#ストリートファッション", "#スケーター", "#ストリートコーデ", "#メンズファッション"],
    },
    "legs": {
        "label": "脚長・スタイルアップ",
        "hooks": [
            {"t": "普通の{category} vs {name}、脚の長さ見て"},
            {"t": "身長盛りたい人、この{category}一択"},
            {"t": "低身長でもスタイル良く見える{category}"},
            {"t": "履くだけで脚長に見えるの反則"},
        ],
        "points": ["厚底で自然に身長が盛れる", "ボリュームで脚が細く見える", "{feature}"],
        "tags": ["#脚長効果", "#低身長コーデ", "#厚底スニーカー", "#スタイルアップ"],
    },
    "unique": {
        "label": "人と被らない",
        "hooks": [
            {"t": "みんなと同じ{category}、もう飽きた人へ"},
            {"t": "「それどこの？」って絶対聞かれる{category}"},
            {"t": "まだ日本で知ってる人少ない{brand}"},
            {"t": "定番ブランドから卒業したい人向けの{category}"},
        ],
        "points": ["街でほぼ被らない", "知る人ぞ知るブランド", "{feature}"],
        "tags": ["#被らない", "#人と被らないファッション", "#スニーカー好きと繋がりたい"],
    },
    "y2k": {
        "label": "Y2K・古着",
        "hooks": [
            {"t": "Y2Kコーデの足元、これにしたら完成した"},
            {"t": "古着好きが選ぶ{category}"},
            {"t": "2000年代っぽさが可愛すぎる{category}"},
        ],
        "points": ["レトロな見た目", "古着と合わせやすい", "{feature}"],
        "tags": ["#y2kファッション", "#古着コーデ", "#古着好きと繋がりたい"],
    },
    "price": {
        "label": "コスパ・公式価格",
        "hooks": [
            {"t": "ハイブラ見えする{category}が{price}"},
            {"t": "他の店だと{compare_price}、公式なら{price}", "requires": ["compare_price"]},
            {"t": "買う場所で{diff}も変わる{category}", "requires": ["compare_price"]},
            {"t": "学生でも買える{price}のおしゃれ{category}"},
        ],
        "points": ["{price}で買える", "公式なら{price}（他店{compare_price}）", "{feature}"],
        "tags": ["#プチプラ", "#コスパ最強", "#買ってよかった"],
    },
    "review": {
        "label": "正直レビュー",
        "hooks": [
            {"t": "{name}、正直レビューします"},
            {"t": "{name}って実際どう？1週間履いた本音"},
            {"t": "{name}のサイズ感、買う前に見て"},
            {"t": "{brand}買って後悔したこと・良かったこと"},
        ],
        "points": ["サイズ感（普段◯cm→◯cmを選択）", "履き心地・重さ", "{feature}"],
        "tags": ["#正直レビュー", "#購入品紹介", "#サイズ感"],
    },
    "gift": {
        "label": "プレゼント",
        "hooks": [
            {"t": "彼氏・彼女へのプレゼントで外さない{category}"},
            {"t": "誕生日にもらって一番嬉しかった{category}"},
        ],
        "points": ["男女兼用で贈りやすい", "箱までおしゃれ", "{feature}"],
        "tags": ["#プレゼント", "#誕生日プレゼント", "#ギフト"],
    },
}

# ─── 投稿フォーマット（動画の型） ─────────────────────────
FORMATS = {
    "compare": {
        "label": "着用比較",
        "script": [
            "0-2秒: フック文字を大きく表示（{hook}）",
            "2-6秒: 左に普通の{category}、右に{name}で並べて比較",
            "6-10秒: 全身を正面と横から見せる",
            "10-13秒: 「{point}」を文字で表示",
            "13-15秒: 「リンクはプロフィールから」",
        ],
    },
    "size": {
        "label": "サイズ感・履き心地",
        "script": [
            "0-2秒: フック（{hook}）",
            "2-5秒: 「普段◯cm → {name}は◯cmを選択」",
            "5-9秒: つま先・かかとの余り、厚底の高さを見せる",
            "9-13秒: 歩くシーン。「{point}」",
            "13-15秒: 「カラー違いはプロフィールのリンクから」",
        ],
    },
    "outfit": {
        "label": "着回し",
        "script": [
            "0-2秒: フック（{hook}）",
            "2-12秒: コーデ3〜5パターンを2秒ずつ切り替え（音ハメ）",
            "12-14秒: 「{point}」",
            "14-15秒: 「保存して真似してね」＋プロフィールのリンクへ誘導",
        ],
    },
    "unboxing": {
        "label": "開封",
        "script": [
            "0-2秒: フック（{hook}）",
            "2-6秒: 箱を開ける（手元のみ・ASMR風）",
            "6-10秒: 実物の色（{color}）を自然光で",
            "10-13秒: 履いた足元。「{point}」",
            "13-15秒: 「{price}／リンクはプロフィールから」",
        ],
    },
    "ranking": {
        "label": "ランキング・◯選",
        "script": [
            "0-2秒: フック（{hook}）",
            "2-8秒: 3位・2位（他の候補を簡単に）",
            "8-13秒: 1位に{name}。「{point}」",
            "13-15秒: 「1位のリンクはプロフィールから」",
        ],
    },
}

# ─── ペルソナ（アカウント） ─────────────────────────────
# platforms に "X" "Threads" だけのペルソナはテキスト投稿として生成する
PERSONAS = {
    "A": {
        "label": "韓国コーデ女子",
        "platforms": ["TikTok", "Instagram"],
        "angles": ["korean", "legs", "y2k", "unique"],
        "formats": ["outfit", "compare", "unboxing", "size"],
        "tone": "girl",
    },
    "B": {
        "label": "メンズストリート",
        "platforms": ["TikTok", "Instagram"],
        "angles": ["street", "unique", "y2k", "korean"],
        "formats": ["outfit", "compare", "unboxing"],
        "tone": "boy",
    },
    "C": {
        "label": "低身長の盛り術",
        "platforms": ["TikTok", "Instagram"],
        "angles": ["legs", "korean", "review"],
        "formats": ["compare", "size", "outfit"],
        "tone": "girl",
    },
    "D": {
        "label": "スニーカーレビュー",
        "platforms": ["TikTok", "YouTubeショート"],
        "angles": ["review", "price", "unique", "gift"],
        "formats": ["size", "ranking", "unboxing", "compare"],
        "tone": "neutral",
    },
    "E": {
        "label": "速報（X）",
        "platforms": ["X", "Threads"],
        "angles": ["price", "korean", "unique", "gift"],
        "formats": [],
        "tone": "neutral",
    },
}

TEXT_ONLY_PLATFORMS = {"X", "Threads"}

# 文末の誘導文（ペルソナの口調別）
CTA = {
    "girl": ["気になる子はプロフィールのリンクからチェックしてね🤍", "色違いもプロフのリンクから見れるよ"],
    "boy": ["リンクはプロフィールに置いとく", "気になったらプロフのリンクから"],
    "neutral": ["商品ページはプロフィールのリンクから", "詳細はプロフィールのリンクへ"],
}
