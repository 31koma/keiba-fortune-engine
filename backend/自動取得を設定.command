#!/bin/bash
# JRDB自動取得のセットアップ(ダブルクリックで実行)
# 木・金・土の21:00に、その日と翌日のJRDBデータを自動取得するようMacに登録します
set -e
cd "$(dirname "$0")"
mkdir -p logs

PLIST_SRC="scripts/com.hoshiyomi.jrdb-fetch.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.hoshiyomi.jrdb-fetch.plist"

mkdir -p "$HOME/Library/LaunchAgents"
launchctl unload "$PLIST_DST" 2>/dev/null || true
cp "$PLIST_SRC" "$PLIST_DST"
launchctl load "$PLIST_DST"

echo "登録しました: 木・金・土 21:00 に自動取得します"
echo "ログ: backend/logs/jrdb_fetch.log"
echo ""
echo "=== 動作テスト(いま1回実行します) ==="
.venv/bin/python scripts/jrdb_auto_fetch.py
echo ""
echo "解除したい場合: launchctl unload \"$PLIST_DST\" && rm \"$PLIST_DST\""
read -p "完了しました。Enterキーで閉じてください"
