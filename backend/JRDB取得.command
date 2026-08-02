#!/bin/bash
# JRDBデータ取得(ダブルクリックで実行)
# 直近の騎手マスタ(木曜配布)と開催日データをまとめて取得します
cd "$(dirname "$0")"
echo "=== JRDBデータを取得します(今日+明日+直近の週末) ==="
.venv/bin/python scripts/jrdb_auto_fetch.py
for d in $(date -v-1d +%Y-%m-%d 2>/dev/null || date -d yesterday +%Y-%m-%d) \
         $(date -v-5d +%Y-%m-%d 2>/dev/null || date -d "5 days ago" +%Y-%m-%d) \
         $(date -v-6d +%Y-%m-%d 2>/dev/null || date -d "6 days ago" +%Y-%m-%d); do
  echo "--- $d ---"
  .venv/bin/python -m app.providers.jrdb.fetch "$d"
done
echo ""
echo "=== 取得済みファイル一覧 ==="
ls -la data/jrdb/
echo ""
read -p "完了しました。Enterキーでこのウィンドウを閉じてください"
