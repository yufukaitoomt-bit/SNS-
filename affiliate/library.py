"""訴求軸・投稿フォーマット・ペルソナの定義。

テンプレート内で使えるプレースホルダ:
  {name} 商品名 / {brand} ブランド名 / {price} 価格表記 / {feature} 特徴(ランダム1つ)
  {color} カラー(ランダム1つ) / {celebrity} 着用有名人 / {compare_price} 他店価格 / {diff} 差額
  {category} カテゴリ(スニーカー等) / {sole_height} ソールの高さ / {size_tip} 公式のサイズ案内
  {discount} リンク経由の割引額 / {sale_price} 割引後の価格

requires に書いた項目が商品に入っていないテンプレートは使われない
(例: 有名人が未設定の商品で「◯◯着用」と出さないため)。
"""

# ─── 訴求軸 ──────────────────────────────────────────────
ANGLES = {
    "korean": {
        "label": "韓国系・K-POP",
        "hooks": [
            {"t": "韓国っぽコーデに合わせたい{category}、日本で買えるの知ってた？"},
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
        "label": "厚底・身長盛り",
        "hooks": [
            {"t": "普通の{category} vs {name}、並べて比べてみた"},
            {"t": "身長盛りたい人へ。ソール{sole_height}の{category}", "requires": ["sole_height"]},
            {"t": "低身長コーデの足元、{name}にしてみた"},
            {"t": "厚底{category}で全身バランス変えてみた"},
        ],
        "points": ["ソールの高さ{sole_height}（公式表記）", "{feature}"],
        "tags": ["#低身長コーデ", "#厚底スニーカー", "#身長盛り"],
    },
    "unique": {
        "label": "人と被らない",
        "hooks": [
            {"t": "みんなと同じ{category}、もう飽きた人へ"},
            {"t": "「それどこの？」って絶対聞かれる{category}"},
            {"t": "まだ日本で知ってる人少ない{brand}"},
            {"t": "定番ブランドから卒業したい人向けの{category}"},
        ],
        "points": ["まだ周りと被りにくい", "知る人ぞ知るブランド", "{feature}"],
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
            {"t": "{brand}の{category}、公式なら{price}"},
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
        "points": ["サイズ感（普段◯cm→◯cmを選択）", "公式のサイズ案内: {size_tip}", "{feature}"],
        "tags": ["#正直レビュー", "#購入品紹介", "#サイズ感"],
    },
    "discount": {
        "label": "リンク限定特典",
        "hooks": [
            {"t": "このリンクから買うと{discount}オフになる{category}", "requires": ["discount"]},
            {"t": "公式価格からさらに{discount}オフで買える方法", "requires": ["discount"]},
            {"t": "{name}、実質{sale_price}で買えるの知ってた？", "requires": ["discount"]},
            {"t": "{name}買うなら、普通に買うより{discount}お得なやり方ある", "requires": ["discount"]},
        ],
        "points": ["リンク経由で{discount}オフ（実質{sale_price}）", "{feature}"],
        "tags": ["#お得情報", "#クーポン", "#買ってよかった"],
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
        "label": "サイズ感",
        "script": [
            "0-2秒: フック（{hook}）",
            "2-5秒: 「普段◯cm → {name}は◯cmを選択」（自分の実測のみ）",
            "5-9秒: つま先・かかとの余り、ソールの高さを定規で見せる",
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
        "angles": ["review", "price", "discount", "unique", "gift"],
        "formats": ["size", "ranking", "unboxing", "compare"],
        "tone": "neutral",
    },
    "E": {
        "label": "速報（X）",
        "platforms": ["X", "Threads"],
        "angles": ["discount", "price", "korean", "unique", "gift"],
        "formats": [],
        "tone": "neutral",
    },
}

TEXT_ONLY_PLATFORMS = {"X", "Threads"}

# 投稿時に各媒体でONにする広告表示の設定（#PRと両方やる。設定は後から本人が消せない）
DISCLOSURE = {
    "X": "投稿時に「有料パートナーシップ」ラベルをON",
    "TikTok": "投稿時に「コンテンツの開示（ブランドコンテンツ）」をON",
    "Instagram": "投稿時に「タイアップ投稿ラベル」をON",
    "YouTubeショート": "「有料プロモーションを含む」をON",
    "Threads": "本文の#PRで表示",
}

# 根拠のない効能・比較表現。商品データや追加テンプレに混ざっていたら生成を止める
BANNED_PHRASES = ["細見え", "細く見え", "疲れにくい", "疲れない", "履き心地抜群", "ハイブラ見え", "着痩せ", "No.1", "日本一", "最安"]
ALL_PLATFORMS = ["TikTok", "X", "Instagram", "YouTubeショート", "Threads"]
DEFAULT_PLATFORMS = ["TikTok", "X"]  # 主戦場。他は余力があれば同じ動画を転用

# ─── X投稿の型 ───────────────────────────────────────
# single: 1投稿で完結 / question: 返信を集める / thread: 本文は伸ばしリンクはリプ欄 / deal: 特典告知
X_FORMATS = {
    "single": "1投稿",
    "question": "質問（リプ集め）",
    "thread": "ツリー（リンクはリプ欄）",
    "deal": "特典告知",
}
X_QUESTIONS = [
    "みんななら何色にする？",
    "これ履くならどんなコーデ合わせる？",
    "アリ？ナシ？正直に教えて",
    "これ知ってた人いる？",
]

# 文末の誘導文（ペルソナの口調別）
CTA = {
    "girl": ["気になる子はプロフィールのリンクからチェックしてね🤍", "色違いもプロフのリンクから見れるよ"],
    "boy": ["リンクはプロフィールに置いとく", "気になったらプロフのリンクから"],
    "neutral": ["商品ページはプロフィールのリンクから", "詳細はプロフィールのリンクへ"],
}

# TikTok Shop出店商品: 動画に🛒商品リンクを付けるので、誘導先を動画内に変える
CTA_SHOP = {
    "girl": ["この動画の🛒から買えるよ🤍", "色違いも🛒の商品ページから見れるよ"],
    "boy": ["動画の🛒から買える", "気になったら🛒の商品ページから"],
    "neutral": ["動画の🛒（商品リンク）から購入できます", "詳細は🛒の商品ページへ"],
}
SHOP_SCRIPT_REPLACE = [
    ("「リンクはプロフィールから」", "「画面の🛒から買えます」"),
    ("「カラー違いはプロフィールのリンクから」", "「カラー違いは🛒の商品ページから」"),
    ("＋プロフィールのリンクへ誘導", "＋画面の🛒へ誘導"),
    ("リンクはプロフィールから", "画面の🛒から"),
    ("「1位のリンクはプロフィールから」", "「1位は画面の🛒から」"),
]
