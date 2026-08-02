#!/usr/bin/env python3
"""WIN5候補 各レース3頭 — 星読みターフ

起動中のバックエンドAPI(/v1/day-recommendations)から客観シンクロ度
(あなた抜き: harmony+day_flow+collective)を取得し、WIN5対象5レースの
上位3頭ずつを端末とHTMLで出す。

WIN5対象の推定ルール:
  JRAは原則「後半の5レース」(通常3場開催では 10R/11R帯、最終Rは対象外)。
  発走 14:50〜15:50 の窓に入るレースがちょうど5つならそれを採用。
  ずれる場合は最終レースを除いた発走時刻の遅い5レースにフォールバックし、
  警告を出す(JRA公式 https://www.jra.go.jp/kouza/win5/info/racelist.html で要確認)。

使い方:
  python3 scripts/win5_picks.py [YYYY-MM-DD]
  (日付省略時はAPI側が直近開催日を自動選択)
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
import webbrowser
from collections import defaultdict
from datetime import datetime
from pathlib import Path

API_BASE = "http://localhost:8000"
OUT_DIR = Path(__file__).resolve().parent.parent / "data"

# 客観 = 総合からuser_resonanceを除いた3成分(synchro_v0の重みを再正規化)
KYAKKAN_W = {"harmony": 0.30, "day_flow": 0.25, "collective": 0.25}
HONSHITSU_W = {"harmony": 0.30, "day_flow": 0.25}


def recompute(components: dict, weights: dict[str, float]) -> float | None:
    avail = {k: w for k, w in weights.items()
             if components.get(k, {}).get("score") is not None}
    if not avail:
        return None
    wsum = sum(avail.values())
    raw = sum(components[k]["score"] * w / wsum for k, w in avail.items())
    return round(min(10.0, raw), 1)


def fetch(target_date: str | None) -> dict:
    q = {}
    if target_date:
        q["target_date"] = target_date
    url = f"{API_BASE}/v1/day-recommendations"
    if q:
        url += "?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def pick_win5_races(items: list[dict]) -> tuple[list[list[dict]], bool]:
    """(対象5レースのentriesリスト, 推定に自信ありか)を返す。"""
    races: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        races[it["race_id"]].append(it)
    groups = sorted(races.values(), key=lambda g: g[0].get("start_time") or "")
    window = [g for g in groups
              if g[0].get("start_time") and "14:50" <= g[0]["start_time"] <= "15:50"]
    if len(window) == 5:
        return window, True
    # フォールバック: 各場の最終レースを除き、発走の遅い5レース
    last_no = defaultdict(int)
    for g in groups:
        c = g[0]["racecourse"]
        last_no[c] = max(last_no[c], g[0]["race_number"])
    rest = [g for g in groups if g[0]["race_number"] != last_no[g[0]["racecourse"]]]
    return rest[-5:], False


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        data = fetch(target)
    except OSError:
        print("バックエンドに接続できません。先に「星読みターフを起動.command」を実行してください。")
        return 1
    items = data.get("items") or []
    if not items:
        print(f"レースデータがありません(target={target})")
        return 1
    day = data["target_date"]
    legs, confident = pick_win5_races(items)

    rows = []
    print(f"\n=== WIN5候補 各3頭 — {day} (客観シンクロ度順) ===")
    if not confident:
        print("⚠ 対象レースは推定です。JRA公式のWIN5対象レース表で確認してください。")
    for i, g in enumerate(legs, 1):
        head = g[0]
        name = head["race_name"] if head["race_name"] != "レース" else ""
        title = f"{head['racecourse']}{head['race_number']}R {name}".strip()
        top3 = sorted(
            g, key=lambda x: -(recompute(x["synchro"]["components"], KYAKKAN_W) or 0)
        )[:3]
        print(f"\nWIN5-{i}: {title} ({head.get('start_time')}発走)")
        leg_rows = []
        for t in top3:
            c = t["synchro"]["components"]
            kyak = recompute(c, KYAKKAN_W)
            hon = recompute(c, HONSHITSU_W)
            odds = t.get("win_odds")
            print(f"  馬番{t['post_number']:>2} {t['horse_name']:<16} "
                  f"客観{kyak} 本質{hon} 単勝{odds}")
            leg_rows.append({"post": t["post_number"], "name": t["horse_name"],
                             "jockey": t["jockey_name"], "kyak": kyak,
                             "hon": hon, "odds": odds})
        rows.append({"leg": i, "title": title, "time": head.get("start_time"),
                     "picks": leg_rows})

    print(f"\n3×3×3×3×3 = 243通り。")
    print("本鑑定は占術に基づくエンターテインメントであり、"
          "結果の予測・馬券購入の推奨ではありません。")

    html = render_html(day, rows, confident)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"win5_{day.replace('-', '')}.html"
    out.write_text(html, encoding="utf-8")
    print(f"\nHTML: {out}")
    try:
        webbrowser.open(out.as_uri())
    except Exception:
        pass
    return 0


def render_html(day: str, rows: list[dict], confident: bool) -> str:
    note = "" if confident else (
        "<p class='warn'>⚠ 対象レースは発走時刻からの推定です。"
        "<a href='https://www.jra.go.jp/kouza/win5/info/racelist.html'>JRA公式</a>"
        "で確認してください。</p>")
    legs_html = []
    for r in rows:
        picks = "".join(
            f"<tr><td class='post'>{p['post']}</td><td class='name'>{p['name']}"
            f"<span class='jockey'>{p['jockey']}</span></td>"
            f"<td>{p['kyak']}</td><td>{p['hon']}</td>"
            f"<td>{p['odds'] if p['odds'] is not None else '—'}</td></tr>"
            for p in r["picks"])
        legs_html.append(
            f"<section><h2><span class='leg'>WIN5-{r['leg']}</span> {r['title']}"
            f"<span class='time'>{r['time']}発走</span></h2>"
            f"<table><thead><tr><th>馬番</th><th>馬名</th><th>客観</th>"
            f"<th>本質</th><th>単勝</th></tr></thead><tbody>{picks}</tbody>"
            f"</table></section>")
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WIN5候補 {day} — 星読みターフ</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ font-family: "Hiragino Sans", sans-serif; background: #0e1024;
         color: #e8e6f0; max-width: 640px; margin: 0 auto; padding: 20px; }}
  h1 {{ font-size: 20px; }} h1 .star {{ color: #ffd76a; }}
  .sub {{ color: #9a97b5; font-size: 13px; }}
  section {{ background: #181b36; border-radius: 12px; padding: 12px 16px;
             margin: 14px 0; }}
  h2 {{ font-size: 15px; margin: 4px 0 10px; }}
  .leg {{ color: #ffd76a; margin-right: 6px; }}
  .time {{ color: #9a97b5; font-size: 12px; margin-left: 8px; font-weight: normal; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{ color: #9a97b5; font-weight: normal; font-size: 12px; text-align: left;
       padding: 2px 6px; }}
  td {{ padding: 6px; border-top: 1px solid #262a4d; }}
  .post {{ font-weight: bold; }}
  .jockey {{ color: #9a97b5; font-size: 12px; margin-left: 8px; }}
  .warn {{ color: #ffb36a; font-size: 13px; }}
  footer {{ color: #77748f; font-size: 11px; margin-top: 20px; line-height: 1.6; }}
</style></head><body>
<h1><span class="star">✦</span> WIN5候補 各3頭 <span class="sub">{day}</span></h1>
<p class="sub">客観シンクロ度(あなた抜き: 調和+日流+集合意識)の上位3頭 / 3^5=243通り / {generated}生成</p>
{note}
{"".join(legs_html)}
<footer>本鑑定は占術に基づくエンターテインメントであり、レース結果を予測・保証するものではありません。<br>
シンクロ度=占術の調和+集合意識(オッズ)の共鳴(synchro_v0・検証前の仮説)。馬券購入の推奨ではありません。<br>
データ提供: JRDB(個人利用契約) / WIN5対象レースはJRA公式で必ず確認してください。</footer>
</body></html>"""


if __name__ == "__main__":
    sys.exit(main())
