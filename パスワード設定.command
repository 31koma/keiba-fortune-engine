#!/bin/bash
# 星読みターフ ログインパスワードの設定(ダブルクリックで実行)
#
# 入力したパスワードは、このMacの中でハッシュ化されてから backend/.env に書かれます。
# 平文はファイルにもログにも残りません。変更したくなったら、いつでも実行し直してください。
cd "$(dirname "$0")"

PY="backend/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "=== 星読みターフ ログイン設定 ==="
echo ""

read -p "メールアドレス: " EMAIL
if [ -z "$EMAIL" ]; then
  echo "メールアドレスが空です。中止しました。"; read -p "Enterで閉じる"; exit 1
fi

# -s = 画面に表示しない
read -s -p "パスワード: " PASS1; echo ""
read -s -p "もう一度   : " PASS2; echo ""
if [ -z "$PASS1" ]; then
  echo "パスワードが空です。中止しました。"; read -p "Enterで閉じる"; exit 1
fi
if [ "$PASS1" != "$PASS2" ]; then
  echo "2回の入力が一致しませんでした。中止しました。"; read -p "Enterで閉じる"; exit 1
fi
if [ ${#PASS1} -lt 8 ]; then
  echo "パスワードが短すぎます(8文字以上にしてください)。中止しました。"
  read -p "Enterで閉じる"; exit 1
fi

ENV_FILE="backend/.env"
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"

# 既存のセッション署名鍵は引き継ぐ(作り直すと今ログイン中の端末が全部切れるため)
SECRET=$(grep -E '^KEIBA_AUTH_SECRET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)

HASH=$(PASSWORD="$PASS1" "$PY" -c "
import os, sys
sys.path.insert(0, 'backend')
from app.core.auth import hash_password
print(hash_password(os.environ['PASSWORD']))
") || { echo "ハッシュ生成に失敗しました。backend の準備を確認してください。"; read -p "Enterで閉じる"; exit 1; }

unset PASS1 PASS2

if [ -z "$SECRET" ]; then
  SECRET=$("$PY" -c "import secrets; print(secrets.token_urlsafe(48))")
  echo "・セッション署名鍵を新しく作りました"
else
  echo "・セッション署名鍵は既存のものを引き継ぎました(ログイン中の端末は切れません)"
fi

# 認証まわりの行だけ入れ替える(他の設定はそのまま残す)
TMP=$(mktemp)
grep -v -E '^KEIBA_(AUTH_REQUIRED|AUTH_EMAIL|AUTH_PASSWORD_HASH|AUTH_SECRET|AUTH_SESSION_DAYS)=' \
  "$ENV_FILE" > "$TMP" 2>/dev/null
{
  echo "KEIBA_AUTH_REQUIRED=1"
  echo "KEIBA_AUTH_EMAIL=$EMAIL"
  echo "KEIBA_AUTH_PASSWORD_HASH=$HASH"
  echo "KEIBA_AUTH_SECRET=$SECRET"
  echo "KEIBA_AUTH_SESSION_DAYS=30"
} >> "$TMP"
mv "$TMP" "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo ""
echo "=== 設定しました ==="
echo "・メールアドレス: $EMAIL"
echo "・パスワード: ハッシュ化して保存(平文はどこにも残っていません)"
echo "・ログインの保持: 30日"
echo ""
echo "反映するには「星読みターフを停止.command」→「星読みターフを起動.command」の順に実行してください。"
echo ""
read -p "Enterキーで閉じてください"
