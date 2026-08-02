#!/bin/bash
# 星読みターフ: ローカルのコミットをGitHubへ送る(ダブルクリックで実行)
cd "$(dirname "$0")"
echo "=== GitHubへpushします (keiba-fortune-engine) ==="
git push origin main
if [ $? -eq 0 ]; then
  echo ""
  echo "✅ 完了。GitHubに複製が残りました。"
else
  echo ""
  echo "❌ 失敗。ネット接続とGitHubのSSH鍵を確認してください。"
fi
echo ""
read -p "Enterで閉じる"
