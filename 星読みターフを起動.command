#!/bin/bash
# 星読みターフ 一括起動(ダブルクリックで実行)
# バックエンド(API)とフロントエンド(画面)を起動してブラウザを開きます
cd "$(dirname "$0")"
mkdir -p backend/logs

echo "=== 星読みターフを起動します ==="

# --- バックエンド(ポート8000) ---
if lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "・バックエンド: すでに起動しています"
else
  echo "・バックエンド: 起動中..."
  (cd backend && nohup .venv/bin/python -m uvicorn app.main:app \
    >> logs/server.log 2>&1 &)
fi

# --- フロントエンド(ポート3000・本番モード) ---
if lsof -i :3000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "・フロントエンド: すでに起動しています"
else
  NEED_BUILD=0
  if [ ! -f frontend/.next/BUILD_ID ]; then
    NEED_BUILD=1
  elif [ -n "$(find frontend/app frontend/lib -newer frontend/.next/BUILD_ID -print -quit 2>/dev/null)" ]; then
    NEED_BUILD=1  # コードが更新されている
  fi
  if [ "$NEED_BUILD" = "1" ]; then
    echo "・フロントエンド: ビルド中...(1〜2分。この画面に進捗が出ます)"
    (cd frontend && npm run build) || { echo "ビルド失敗。ログを確認してください"; read -p "Enterで閉じる"; exit 1; }
  fi
  echo "・フロントエンド: 起動中..."
  (cd frontend && nohup npm run start >> ../backend/logs/frontend.log 2>&1 &)
fi

# --- 起動待ち → ブラウザを開く ---
echo -n "・画面の準備を待っています"
for i in $(seq 1 60); do
  if curl -s --max-time 2 -o /dev/null http://localhost:3000; then
    echo ""
    echo "・ブラウザを開きます: http://localhost:3000"
    open http://localhost:3000
    echo ""
    echo "=== 起動完了 ==="
    echo "止めたいときは「星読みターフを停止.command」をダブルクリック"
    sleep 3
    exit 0
  fi
  echo -n "."
  sleep 2
done
echo ""
echo "起動に時間がかかっています。ログを確認してください:"
echo "  backend/logs/server.log / backend/logs/frontend.log"
read -p "Enterキーで閉じてください"
