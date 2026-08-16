#!/bin/bash
# 星読みターフ 再起動(ダブルクリックで実行)
#
# 「起動.command」は既に動いていると何もしないので、コードを更新したあとは
# こちらを使う。停止 → 作り直し → 起動 を必ず順番に通す。
cd "$(dirname "$0")"
mkdir -p backend/logs

echo "=== 星読みターフを再起動します ==="
echo ""

# --- 1) 停止 ---
for port in 8000 3000; do
  pids=$(lsof -ti :$port -sTCP:LISTEN 2>/dev/null)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null
    echo "・ポート$port を停止しました"
  fi
done
# 落ちきるのを待つ(最大10秒)
for i in $(seq 1 10); do
  lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1 || lsof -i :3000 -sTCP:LISTEN >/dev/null 2>&1 || break
  sleep 1
done
sleep 1

# --- 2) バックエンド ---
echo "・バックエンド: 起動中..."
(cd backend && nohup .venv/bin/python -m uvicorn app.main:app >> logs/server.log 2>&1 &)

# --- 3) フロントエンド(必ず作り直す) ---
echo "・フロントエンド: 作り直しています...(1〜2分。この画面に進捗が出ます)"
(cd frontend && npm run build) || {
  echo ""
  echo "ビルドに失敗しました。上のエラーを確認してください。"
  read -p "Enterで閉じる"; exit 1
}
echo "・フロントエンド: 起動中..."
# -H 127.0.0.1 = このMacの中からだけ繋がる。外へはTailscale経由でのみ公開する
  (cd frontend && nohup npm run start -- -H 127.0.0.1 >> ../backend/logs/frontend.log 2>&1 &)

# --- 4) 起動待ち → 確認 ---
echo -n "・画面の準備を待っています"
for i in $(seq 1 60); do
  if curl -s --max-time 2 -o /dev/null http://localhost:3000; then
    echo ""
    # ログインが効いているかを実際に叩いて確かめる
    CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000/api/v1/day-recommendations")
    if [ "$CODE" = "401" ]; then
      echo "・ログイン: 有効です(未ログインのアクセスを弾きました)"
    elif [ "$CODE" = "503" ]; then
      echo "・ログイン: 未設定です。「パスワード設定.command」を実行してください"
    else
      echo "・ログイン: 効いていません(応答 $CODE)。backend/.env の KEIBA_AUTH_ 行を確認してください"
    fi
    echo "・ブラウザを開きます: http://localhost:3000"
    open http://localhost:3000
    echo ""
    echo "=== 再起動しました ==="
    sleep 4
    exit 0
  fi
  echo -n "."
  sleep 2
done
echo ""
echo "起動に時間がかかっています。ログを確認してください:"
echo "  backend/logs/server.log / backend/logs/frontend.log"
read -p "Enterキーで閉じてください"
