#!/bin/bash
# WIN5候補 各レース3頭(ダブルクリックで実行)
# 起動中のバックエンドから客観シンクロ度を取得してHTMLを開きます
cd "$(dirname "$0")/backend"

if ! lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "バックエンドが起動していないため起動します..."
  mkdir -p logs
  (nohup .venv/bin/python -m uvicorn app.main:app >> logs/server.log 2>&1 &)
  for i in $(seq 1 30); do
    curl -s --max-time 2 -o /dev/null http://localhost:8000/health && break
    sleep 1
  done
fi

.venv/bin/python scripts/win5_picks.py "$@"
echo ""
read -p "Enterキーで閉じてください"
