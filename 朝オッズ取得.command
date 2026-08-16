#!/bin/bash
# 朝オッズ取得 — 当日の実オッズ(単勝・複勝)を取得して backend/data/jrdb/RTO{yymmdd}.json に保存する。
# 使い方: レース当日の朝、これをダブルクリックするだけ(JRDBデータ取得.command の後に実行)。
#
# ★実行は9時以降にすること。
#   2026-08-15に06:33で実行したときは1レースも取れなかった。原因はバグではなく
#   「その時刻にはまだオッズが公開されていなかった」だけ(同日の札幌1Rの
#   official_datetime は 10:09)。早朝に叩いても空で終わる。
# 取得元: netkeiba JRAオッズAPI(1レース1リクエスト・1.2秒間隔の低頻度・個人利用)。
#
# 2026-08-16 修正: 9時12分に実行して36レース全滅(data が空文字・reason='result odds empty')。
#   原因は時刻ではなく URL。この API は action=init が無いとオッズを返さない。
#   同一レースで比較して確認済み:
#     action 無し → {"status":"middle","data":"","update_count":"0","reason":"result odds empty"}
#     action=init → data.odds に単勝・複勝が入る(official_datetime 2026-08-16 08:55:16)
#   よって URL に &locale=ja&action=init を追加した。
#
# 2026-08-15 改訂: 8/15の初実走で「races が空・エラーなし」で終わったため、
#   ① 成功判定を status 文字列に頼るのをやめ、実際にオッズが取れたかで判定する
#   ② 最初の1レースの生レスポンスを RTOdebug{yymmdd}.json に保存する
#   ③ 失敗したときは必ず理由を画面に出す(黙って空ファイルを作らない)
#   を入れた。
#
# 明日を待たずに試すとき:
#   ターミナルで  TEST=1 bash "朝オッズ取得.command"   → 先頭1レースだけ叩いて中身を全部見せる
#   前日でも、翌日の日付を指定して試せる:  DATE=260816 TEST=1 bash "朝オッズ取得.command"
cd "$(dirname "$0")"
export HOSHIYOMI_BASE="$(pwd)"
/usr/bin/python3 - <<'PYEOF'
import json, time, urllib.request, urllib.error, datetime, os, sys

BASE = os.environ.get("HOSHIYOMI_BASE") or os.getcwd()
JRDB = os.path.join(BASE, "backend", "data", "jrdb")
TEST = os.environ.get("TEST") == "1"

yymmdd = os.environ.get("DATE") or datetime.date.today().strftime("%y%m%d")
try:
    target = datetime.datetime.strptime(yymmdd, "%y%m%d").date()
except ValueError:
    print(f"DATE の形式が不正です: {yymmdd}(YYMMDD で指定してください)")
    sys.exit(1)

bac_path = os.path.join(JRDB, f"BAC{yymmdd}.txt")
if not os.path.exists(bac_path):
    print(f"BAC{yymmdd}.txt がありません。先に「JRDBデータ取得.command」を実行してください。")
    sys.exit(1)

# BACからレース一覧(race_key)を読む
race_keys = []
with open(bac_path, "rb") as f:
    for line in f.read().split(b"\n"):
        if len(line) < 100:
            continue
        rk = line[0:8].decode("cp932", "replace")
        if rk[:2].isdigit():
            race_keys.append(rk)
print(f"対象: {len(race_keys)}レース ({yymmdd})")
if not race_keys:
    print("BACからレースを1つも読めませんでした。BACファイルの中身を確認してください。")
    sys.exit(1)
if TEST:
    race_keys = race_keys[:1]
    print("※ TEST=1 のため先頭1レースだけ取得します")


def netkeiba_id(rk):
    # JRDB race_key: 場2 + 年2 + 回1 + 日1(16進) + R2 → netkeiba: 20YY + 場2 + 回2 + 日2 + R2
    venue, yy, kai, day_hex, rr = rk[0:2], rk[2:4], rk[4:5], rk[5:6], rk[6:8]
    return f"20{yy}{venue}{int(kai):02d}{int(day_hex, 16):02d}{rr}"


def extract(data):
    """レスポンスから {馬番: 単複} を取り出す。取れなければ (None, 理由)。"""
    if not isinstance(data, dict):
        return None, f"JSONが辞書でない({type(data).__name__})"
    body = data.get("data")
    if not isinstance(body, dict):
        return None, f"data が無い(トップの項目: {sorted(data.keys())[:8]})"
    odds = body.get("odds")
    if not isinstance(odds, dict):
        return None, f"data.odds が無い(dataの項目: {sorted(body.keys())[:8]})"
    tan, fuku = odds.get("1"), odds.get("2")
    if not isinstance(tan, dict) or not tan:
        return None, f"単勝(odds.1)が空(oddsの項目: {sorted(odds.keys())[:8]})"
    if not isinstance(fuku, dict):
        fuku = {}

    def fl(s):
        try:
            return float(s)
        except (TypeError, ValueError):
            return None

    horses = {}
    for pn, v in tan.items():
        v = list(v) + ["", "", ""]
        f_ = list(fuku.get(pn, [])) + ["", "", ""]
        try:
            num = str(int(pn))
        except (TypeError, ValueError):
            continue
        horses[num] = {"win": fl(v[0]), "win_rank": (lambda r: int(r) if str(r).isdigit() else None)(v[2]),
                       "place_low": fl(f_[0]), "place_high": fl(f_[1])}
    if not horses:
        return None, "単勝はあったが馬番を1頭も解釈できなかった"
    return horses, None


out = {"target_date": target.strftime("%Y-%m-%d"),
       "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
       "source": "netkeiba api_get_jra_odds type=1(単勝・複勝)", "races": {}}
ok = 0
reasons = {}
first_raw = None

for rk in race_keys:
    rid = netkeiba_id(rk)
    # 2026-08-16 修正: action=init が無いと data が空文字で返る(status=middle /
    #   reason='result odds empty')。8/16の朝9時台に36レース全滅した原因はこれ。
    #   同じレースでも action=init を付けると odds が入って返ってくる(実測確認済み)。
    url = ("https://race.netkeiba.com/api/api_get_jra_odds.html"
           f"?type=1&locale=ja&race_id={rid}&action=init")
    raw = None
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh) hoshiyomi-personal/1.0",
            "Referer": f"https://race.netkeiba.com/odds/index.html?race_id={rid}"})
        with urllib.request.urlopen(req, timeout=15) as res:
            raw = res.read().decode("utf-8", "replace")
        data = json.loads(raw)
    except urllib.error.HTTPError as e:
        reasons.setdefault(f"HTTP {e.code}", []).append(rk)
        print(f"  {rk} ({rid}): HTTP {e.code}")
        time.sleep(1.2)
        continue
    except json.JSONDecodeError:
        reasons.setdefault("JSONとして読めない(HTMLが返っている可能性)", []).append(rk)
        print(f"  {rk} ({rid}): JSONでない。先頭200字: {(raw or '')[:200]!r}")
        time.sleep(1.2)
        continue
    except Exception as e:
        reasons.setdefault(f"{type(e).__name__}: {e}", []).append(rk)
        print(f"  {rk} ({rid}): 取得失敗 {e}")
        time.sleep(1.2)
        continue

    if first_raw is None:
        first_raw = {"race_key": rk, "netkeiba_id": rid, "url": url,
                     "status": data.get("status") if isinstance(data, dict) else None,
                     "response": data}

    horses, why = extract(data)
    if horses is None:
        st = data.get("status") if isinstance(data, dict) else None
        reasons.setdefault(f"{why} / status={st!r}", []).append(rk)
        print(f"  {rk} ({rid}): オッズを取れず — {why}(status={st!r})")
        time.sleep(1.2)
        continue

    out["races"][rk] = {"netkeiba_id": rid,
                        "official_datetime": (data.get("data") or {}).get("official_datetime"),
                        "status": data.get("status"), "horses": horses}
    ok += 1
    if TEST:
        print(f"  {rk} ({rid}): 成功 — {len(horses)}頭")
        print("  中身の例:", json.dumps(dict(list(horses.items())[:3]), ensure_ascii=False))
    time.sleep(1.2)

# 最初のレスポンスは必ず残す(次回の原因究明用)
if first_raw is not None:
    dbg = os.path.join(JRDB, f"RTOdebug{yymmdd}.json")
    with open(dbg, "w", encoding="utf-8") as f:
        json.dump(first_raw, f, ensure_ascii=False, indent=1)
    print(f"\n最初の1レースの生レスポンス: {dbg}")

path = os.path.join(JRDB, f"RTO{yymmdd}.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"保存: {path}({ok}/{len(race_keys)}レース)")

if ok == 0:
    print("\n■ オッズを1レースも取れませんでした。理由の内訳:")
    for why, rks in reasons.items():
        print(f"  ・{why} … {len(rks)}レース")
    now_h = datetime.datetime.now().hour
    if now_h < 9:
        print(f"\n  → いま{now_h}時台です。**時刻が早すぎるのがほぼ確実な原因です。**")
        print("     オッズの公開は9時以降。9時をすぎてからもう一度実行してください。")
        print("     (2026-08-15に06:33で実行して1レースも取れなかったのはこれが理由でした)")
    else:
        print("\n  よくある原因: ①まだ発売前 ②APIの応答形式が変わった")
    print(f"  上の RTOdebug{yymmdd}.json をAIに見せれば原因を特定できます。")
    print("  ※ オッズが無くても予想は前日オッズ(OZ)で成立します。先へ進んで構いません。")
    sys.exit(0)

# 前日オッズ(OZ)と比較して人気帯が動いた馬を表示
oz_path = os.path.join(JRDB, f"OZ{yymmdd}.txt")


def band(r):
    return None if not r else ("1-3" if r <= 3 else "4-6" if r <= 6 else "7+")


if os.path.exists(oz_path):
    moved = []
    with open(oz_path, "rb") as f:
        for line in f.read().split(b"\n"):
            if len(line) < 200:
                continue
            rk = line[0:8].decode("cp932", "replace")
            if rk not in out["races"]:
                continue
            odds_prev = []
            for i in range(18):
                s = line[10 + i * 5:15 + i * 5].decode("cp932", "replace").strip()
                try:
                    odds_prev.append(float(s))
                except ValueError:
                    odds_prev.append(None)
            valid = sorted([o for o in odds_prev if o and o > 0])
            for pn0, o in enumerate(odds_prev):
                if not o or o <= 0:
                    continue
                prev_rank = valid.index(o) + 1
                now = out["races"][rk]["horses"].get(str(pn0 + 1))
                if not now or not now["win_rank"]:
                    continue
                b0, b1 = band(prev_rank), band(now["win_rank"])
                if b0 != b1:
                    moved.append(f"  {rk} {pn0+1}番: 前日{prev_rank}人気({b0}) → 現在{now['win_rank']}人気({b1})")
    if moved:
        print("\n■ 人気帯が動いた馬(◎の帯判定に注意):")
        print("\n".join(moved))
    else:
        print("\n人気帯の変動なし")
print("\n完了。このウインドウは閉じてOKです。")
PYEOF
read -p "Enterで閉じる"
