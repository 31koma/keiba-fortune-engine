#!/bin/bash
# 星読みターフ 一括停止(ダブルクリックで実行)
echo "=== 星読みターフを停止します ==="
for port in 8000 3000; do
  pids=$(lsof -ti :$port -sTCP:LISTEN 2>/dev/null)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null
    echo "・ポート$port を停止しました"
  else
    echo "・ポート$port は動いていません"
  fi
done
echo "完了"
sleep 2
