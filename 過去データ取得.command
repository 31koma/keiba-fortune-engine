#!/bin/bash
# 過去の開催日について「まだ持っていないファイル」だけを取り直す(ダブルクリックで実行)
#
# 使いどころ: 新しい種別をFILE_KINDSに足したとき。
#   通常の「JRDBデータ取得.command」は直近1週間しか見ないので、
#   過去分は取りに行かない。こちらは SED があるのに HJC が無い日を探して取得する。
#
# 注意: JRDBは開催日の 08:00-19:00 に当日データ以外のアクセスを制限している。
#   過去分の一括取得は夜か平日に行うこと。
cd "$(dirname "$0")/backend" || exit 1

MISSING=0
for sed in data/jrdb/SED*.txt; do
  [ -e "$sed" ] || continue
  base=$(basename "$sed" .txt)
  ymd=${base#SED}
  if [ ! -f "data/jrdb/HJC${ymd}.txt" ]; then
    MISSING=$((MISSING+1))
    d="20${ymd:0:2}-${ymd:2:2}-${ymd:4:2}"
    echo ""
    echo "=== ${d} の不足分を取得 ==="
    .venv/bin/python -m app.providers.jrdb.fetch "$d"
  fi
done

echo ""
if [ "$MISSING" -eq 0 ]; then
  echo "=== 不足なし(すべての開催日にHJCがそろっています) ==="
else
  echo "=== 完了: ${MISSING}日ぶんを取りに行きました ==="
  echo "そろったファイル:"
  ls -1 data/jrdb/HJC*.txt 2>/dev/null | sed 's|data/jrdb/||'
fi
read -r -p "Enterキーで閉じてください"
