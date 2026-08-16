#!/bin/bash
# 星読みターフをスマホから見えるようにする(Tailscale経由・ダブルクリックで実行)
#
# ネットには一切公開しません。自分のTailscaleアカウントに入っている端末だけが
# 届く経路を作ります。管理画面での設定は不要です。
cd "$(dirname "$0")"

echo "=== 星読みターフ: スマホから見る設定 ==="
echo ""

# --- 1) Tailscale本体を探す ---
TS=""
for c in /Applications/Tailscale.app/Contents/MacOS/Tailscale \
         /opt/homebrew/bin/tailscale /usr/local/bin/tailscale \
         "$(command -v tailscale 2>/dev/null)"; do
  [ -x "$c" ] && TS="$c" && break
done
if [ -z "$TS" ]; then
  echo "Tailscale が見つかりませんでした。"
  echo "  Mac:    https://tailscale.com/download/mac"
  echo "  iPhone: App Store で「Tailscale」(同じGoogleアカウントで)"
  echo "そのあと、もう一度このファイルをダブルクリックしてください。"
  read -p "Enterで閉じる"; exit 1
fi
echo "・Tailscale: 見つかりました"

# --- 2) 接続しているか ---
IP=$("$TS" ip -4 2>/dev/null | head -1)
if [ -z "$IP" ]; then
  echo "・Tailscale にログインしていません。ログイン画面を開きます..."
  "$TS" up
  IP=$("$TS" ip -4 2>/dev/null | head -1)
fi
if [ -z "$IP" ]; then
  echo "Tailscale に接続できていません。メニューバーのアイコンが Connected か確認してください。"
  read -p "Enterで閉じる"; exit 1
fi
echo "・このMacの住所: $IP"

# --- 3) アプリが動いているか ---
if ! lsof -i :3000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "・アプリが起動していません。先に「星読みターフを再起動.command」を実行してください。"
  read -p "Enterで閉じる"; exit 1
fi
echo "・アプリ: 起動しています"

# --- 4) 入口を作る ---
# まずHTTPSで試す(管理画面でHTTPS証明書がONなら成功。きれいなURLになる)
echo "・入口を作っています..."
URL=""
if "$TS" serve --bg 3000 >/dev/null 2>&1; then
  HOST=$("$TS" status --json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
print((d.get('Self',{}).get('DNSName') or '').rstrip('.'))
" 2>/dev/null)
  [ -n "$HOST" ] && URL="https://$HOST"
fi

# だめならHTTPで公開(証明書も管理画面の設定も不要。通信はTailscaleが暗号化する)
if [ -z "$URL" ]; then
  "$TS" serve --bg --http=3000 http://127.0.0.1:3000 >/dev/null 2>&1
  URL="http://$IP:3000"
fi

echo ""
echo "==================================================="
echo "  iPhoneのSafariでこれを開いてください:"
echo ""
echo "      $URL"
echo ""
echo "==================================================="
echo ""
echo "・iPhone側もTailscaleに接続していること(VPNマークが出ていればOK)"
echo "・Safariで開いたら 共有 → ホーム画面に追加 でアプリのように使えます"
echo "・Macがスリープすると繋がりません"
echo "・やめたいとき: ターミナルで  \"$TS\" serve reset"
echo ""
read -p "Enterキーで閉じてください"
