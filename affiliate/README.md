# アフィリエイト投稿ジェネレーター

商品を登録すると、キャラ（アカウント）別に1週間分の **動画台本・投稿文・X投稿** を自動生成します。
毎週売る商品が変わっても、商品を登録して「今週の商品」に切り替えるだけで対応できます。

## 使い方（画面）
1. `bash run.sh` で起動 → http://localhost:8000/affiliate
2. ① 商品を登録（ブランド・商品名・公式価格・特徴・訴求軸）。**最初にチェックした訴求軸が主軸**になり全キャラに混ざる
3. ② 「生成する」→ コピーして投稿、またはCSVを予約投稿ツールに取り込む
4. URLが発行されたら商品のURL欄に貼って保存 → 再生成で全投稿に反映

## 使い方（コマンド）
```
python -m affiliate.cli list
python -m affiliate.cli week --start 2026-10-19          # out/ にCSVとMarkdown
python -m affiliate.cli set-url oldorder-turbo-gt https://...
python -m affiliate.cli activate <商品ID>
```

## 編集する場所
- 訴求軸・フック・台本の型・キャラ: `affiliate/library.py`
- 商品データ: `affiliate/data/products.json`

## 注意
- 全投稿に `#PR` が自動で付きます（ステマ規制対応）。消さないこと
- 「◯◯着用」は事実の場合のみ有名人欄に入力。他店価格は投稿日に確認
- Render無料プランではディスクが再起動で消えるため、画面で登録した商品は products.json にコミットしておく
