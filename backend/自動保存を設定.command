#!/bin/bash
# レース前評価の自動保存セットアップ(ダブルクリックで実行)
# 金・土 21:30(前夜)と土・日 8:00(朝の保険)に、その日と翌日の
# 星読み評価をスナップショットとして自動保存するようMacに登録します。
# 保存された評価が「過去レースを見る」のレース前評価になります。
set -e
cd "$(dirname "$0")"
mkdir -p logs

PLIST_SRC="scripts/com.hoshiyomi.snapshot.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.hoshiyomi.snapshot.plist"

mkdir -p "$HOME/Library/LaunchAgents"
launchctl unload "$PLIST_DST" 2>/dev/null || true
cp "$PLIST_SRC" "$PLIST_DST"
launchctl load "$PLIST_DST"

echo "登録しました: 金・土 21:30 と 土・日 8:00 に自動保存します"
echo "(スリープ中に時刻を過ぎた場合は、Macを開いたときに1回実行されます)"
echo "ログ: backend/logs/snapshot.log"
echo ""
echo "=== 動作テスト(いま1回実行します) ==="
.venv/bin/python scripts/save_snapshots.py
echo ""
echo "解除したい場合: launchctl unload \"$PLIST_DST\" && rm \"$PLIST_DST\""
read -p "完了しました。Enterキーで閉じてください"
