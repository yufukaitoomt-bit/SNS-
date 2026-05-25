#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " SNS Analyzer セットアップ & 起動"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 仮想環境
if [ ! -d "venv" ]; then
  echo "▶ 仮想環境を作成中..."
  python3 -m venv venv
fi

source venv/bin/activate

echo "▶ パッケージをインストール中..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "▶ Playwright ブラウザをインストール中..."
python -m playwright install chromium

echo ""
echo "✅ 準備完了！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ブラウザで開く → http://localhost:8000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
