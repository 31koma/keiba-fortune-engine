"""熱量v1ランキング生成(発走前スナップショット用)。

使い方:
    python3 scripts/heat_ranking.py 2026-08-02

入力:
- app.db の当日の客観 day_recommendation(oshi_v0スコア。user_included=false の最新)
- JRDB UKC(馬の生年月日)
- 正本v1.3 の sizhu_day_pillar.json / racecourse_geography.json
- knowledge/proposals/heat_v1.json

出力:
- backend/data/heat_v1_snapshot_YYYYMMDD.json(発走前保存。検証=答え合わせはSEDと照合)
- 標準出力に上位20と★一覧

標準ライブラリのみ。venv不要でそのまま動く。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.domain.engine.heat import HeatEngine, load_rules  # noqa: E402

KB_DIR = BACKEND.parent.parent / "KomaVault" / "05_Knowledge" / "占術知識ベース_v1.3"
COURSE_KEYS = {"札幌": "sapporo", "函館": "hakodate", "福島": "fukushima", "新潟": "niigata",
               "東京": "tokyo", "中山": "nakayama", "中京": "chukyo", "京都": "kyoto",
               "阪神": "hanshin", "小倉": "kokura"}


def load_birth_dates(ymd: str) -> dict[str, str]:
    path = BACKEND / "data" / "jrdb" / f"UKC{ymd[2:].replace('-', '')}.txt"
    out: dict[str, str] = {}
    for line in path.read_bytes().split(b"\r\n"):
        if len(line) < 165:
            continue
        pid = line[0:8].decode("cp932", "replace").strip()
        b = line[157:165].decode("cp932", "replace").strip()
        if pid and b.isdigit():
            out[pid] = f"{b[:4]}-{b[4:6]}-{b[6:]}"
    return out


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    con = sqlite3.connect(BACKEND / "data" / "app.db")
    con.row_factory = sqlite3.Row
    row = None
    for r in con.execute(
            "select id, payload from app_readings where kind='day_recommendation' "
            "and target_date=? order by id desc", (target,)):
        p = json.loads(r["payload"])
        if not p.get("user_included"):
            row = (r["id"], p)
            break
    if row is None:
        raise SystemExit(f"客観のday_recommendationが見つかりません: {target}。先に予想(スナップショット保存)を実行してください")
    reading_id, payload = row

    birth = load_birth_dates(target)
    sizhu = json.loads((KB_DIR / "sizhu_day_pillar.json").read_text(encoding="utf-8"))
    geo = json.loads((KB_DIR / "racecourse_geography.json").read_text(encoding="utf-8"))
    engine = HeatEngine(load_rules(), sizhu, geo)

    # レースごとに fit_rank(oshi順) と pop_rank(前日単勝オッズ順)
    races: dict[str, list[dict]] = {}
    for it in payload["items"]:
        races.setdefault(it["race_id"], []).append(it)
    results = []
    for race_id, items in races.items():
        by_oshi = sorted(items, key=lambda x: -(x["oshi"]["score"]))
        fit = {id(x): i + 1 for i, x in enumerate(by_oshi)}
        with_odds = [x for x in items if x.get("win_odds")]
        by_pop = sorted(with_odds, key=lambda x: x["win_odds"])
        pop = {id(x): i + 1 for i, x in enumerate(by_pop)}
        for it in items:
            b = birth.get(it["horse_id"])
            if not b:
                continue
            r = engine.evaluate(
                oshi_score=it["oshi"]["score"], horse_birth_date=b, target_date=target,
                course_key=COURSE_KEYS[it["racecourse"]],
                confidence=it["oshi"].get("confidence", "full"),
                fit_rank=fit[id(it)], pop_rank=pop.get(id(it)))
            results.append({
                "racecourse": it["racecourse"], "race_number": it["race_number"],
                "race_name": it.get("race_name"), "start": it.get("start_time"),
                "post": it["post_number"], "horse": it["horse_name"],
                "jockey": it.get("jockey_name"), "head_count": it.get("head_count"),
                "win_odds": it.get("win_odds"),
                "heat": r["heat"], "eligible": r["eligible"],
                "pillar": r["pillar"], "chi": r["components"]["chi"]["label_ja"],
                "ten": r["components"]["ten"]["score"], "oshi": it["oshi"]["score"],
                "conf": it["oshi"].get("confidence"),
                "fit_rank": fit[id(it)], "pop_rank": pop.get(id(it)),
                "story_chips": r["story_chips"],
            })

    ranked = sorted([x for x in results if x["eligible"]], key=lambda x: -x["heat"])
    # レース★=そのレースの最大熱量
    race_max: dict[tuple, float] = {}
    for x in ranked:
        key = (x["racecourse"], x["race_number"])
        race_max[key] = max(race_max.get(key, -99), x["heat"])
    race_stars = {f"{k[0]}{k[1]}R": engine.race_stars(v) for k, v in race_max.items()}

    snapshot = {
        "kind": "heat_v1_ranking",
        "target_date": target,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rule": "heat_v1(app_hypothesis) — ギャップ点なし。heat = oshi + 地運 + (天運-4)*0.5",
        "source_reading_id": reading_id,
        "n_total": len(results),
        "n_eligible": len(ranked),
        "top20": ranked[:20],
        "race_stars": race_stars,
        "all_ranked": [{k: x[k] for k in ("racecourse", "race_number", "post", "horse",
                                          "heat", "oshi", "chi", "ten", "fit_rank",
                                          "pop_rank", "conf")} for x in ranked],
        "disclaimer": "本予想は占術に基づく分析であり、レース結果を保証するものではありません。馬券の購入はご自身の判断と責任で行ってください",
    }
    out = BACKEND / "data" / f"heat_v1_snapshot_{target.replace('-', '')}.json"
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"熱量v1ランキング {target}(対象{len(ranked)}頭/全{len(results)}頭)")
    print(f"保存: {out}")
    print("\n=== 上位20 ===")
    for i, x in enumerate(ranked[:20], 1):
        chip = " ★隠れ熱" if x["story_chips"] else ""
        print(f"{i:2d}. {x['heat']:5.2f} {x['start'] or '--:--'} {x['racecourse']}{x['race_number']}R "
              f"{x['post']}番 {x['horse']}({x['pillar']} {x['chi']}/{x['ten']} oshi{x['oshi']}){chip}")
    print("\n=== レース★(5以上) ===")
    for k, v in sorted(race_stars.items(), key=lambda kv: -kv[1]):
        if v >= 5:
            print(f"★{v} {k}")


if __name__ == "__main__":
    main()
