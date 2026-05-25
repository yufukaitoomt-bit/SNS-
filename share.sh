#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  SNS Analyzer 外部公開スクリプト（サインアップ不要）
#  使い方: bash share.sh
# ─────────────────────────────────────────────────────────────
cd "$(dirname "$0")"

# サーバーが起動していなければ起動
if ! curl -s http://localhost:8000/login > /dev/null 2>&1; then
  echo "▶ SNS Analyzerサーバーを起動中..."
  source venv/bin/activate
  APP_PASSWORD="${APP_PASSWORD:-newprime2024}" \
    uvicorn main:app --host 0.0.0.0 --port 8000 &
  SERVER_PID=$!
  until curl -s http://localhost:8000/login > /dev/null 2>&1; do sleep 2; done
  echo "✅ サーバー起動完了 (PID: $SERVER_PID)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SNS Analyzer を外部公開します"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  パスワード: ${APP_PASSWORD:-newprime2024}"
echo "  Ctrl+C で共有停止"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  公開URL を発行中..."
echo ""

# localhost.run でトンネル作成（SSH経由・サインアップ不要）
# URLが出たら自動でコピーして表示
ssh -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -o ExitOnForwardFailure=yes \
    -R 80:localhost:8000 \
    nokey@localhost.run 2>&1 | while IFS= read -r line; do
  echo "  $line"
  # URLを検出してハイライト表示
  if echo "$line" | grep -qE 'https://[a-z0-9-]+\.lhr\.life'; then
    url=$(echo "$line" | grep -oE 'https://[a-z0-9-]+\.lhr\.life')
    echo ""
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║  ✅ 公開URL:                             ║"
    echo "  ║  $url  ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo ""
    echo "  パスワード: ${APP_PASSWORD:-newprime2024}"
    echo ""
    # クリップボードにコピー（macOS）
    echo "$url" | pbcopy 2>/dev/null && echo "  （URLをクリップボードにコピーしました）"
    echo ""
  fi
done
