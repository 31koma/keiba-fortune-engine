#!/bin/bash
# JRDBデータを取り直す(ダブルクリックで実行)
# 直近1週間の土日+昨日+今日を取得します(成績SEDの取り直し用)
cd "$(dirname "$0")/backend"

for i in 0 1 2 3 4 5 6; do
  D=$(date -v-${i}d +%F)
  W=$(date -v-${i}d +%u)   # 6=土曜, 7=日曜
  if [ "$W" = "6" ] || [ "$W" = "7" ] || [ "$i" -le 1 ]; then
    echo "=== ${D} を取得 ==="
    .venv/bin/python -m app.providers.jrdb.fetch "$D"
  fi
done

echo ""
echo "=== 完了 ==="
read -p "Enterキーで閉じてください"
