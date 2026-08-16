"""回収率バックテスト — 選定ルールが「当たった」のではなく「増えた」のかを測る。

背景(2026-08-16):
    run1〜12 の検証はすべて勝率・複勝率(=的中率)で測っており、回収率を一度も
    測っていなかった。的中率が上がっても、その上がりぶんがオッズに織り込まれて
    いれば手元は増えない。とくに1-3人気帯はそれが起きやすい。
    そこで、手元にある全開催日について「そのルールで買っていたら回収率は
    いくつだったか」を出す物差しをつくる。

測り方:
    単勝回収率 = Σ(勝った馬の確定単勝オッズ) / 点数
        SED(175,6)の確定単勝オッズは実配当そのものなので **正確** に出せる。
    複勝回収率 = Σ(3着以内に来た馬の前日複勝オッズ) / 点数
        JRDBは確定複勝配当を配布しないため、OZ(101,90)の前日複勝オッズを
        払戻の近似として使う。**概算であり実配当ではない**。
        全馬買いの複勝回収が理論値(約80%)より低く出るので、
        個々のルールは100%と比べるのではなく **「全馬(基準)」行と比べる**こと。

読むときの注意:
    - 期間バイアス: 全馬買いの単勝回収が理論値80%を下回る期間は「人気が堅かった」
      期間であり、人気薄を買うルールに不利・人気馬を買うルールに有利に出る。
      必ず基準行と同時に見る。
    - p表v4はこの期間のデータから作っているので、帯×セルの数字は自己言及(in-sample)。
      合・収束度によるルールはp表を使っていないのでその汚染がない。
    - 「最大配当1点を除く」列と「日別中央値」「100%超の日数」を必ず見る。
      1頭の万馬券で全体が持ち上がっていないかの確認。

使い方:
    cd 競馬アプリ && python3 backend/scripts/roi_backtest.py
"""
import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
JR = REPO / "backend" / "data" / "jrdb"
os.environ.setdefault("KEIBA_DATA_PROVIDER", "jrdb")
os.environ.setdefault("KEIBA_JRDB_DATA_DIR", str(JR))
sys.path.insert(0, str(REPO / "backend"))

from app.core.config import settings                       # noqa: E402
from app.domain.engine.numerology import Numerology        # noqa: E402
from app.domain.engine.synchro import SynchroEngine        # noqa: E402
from app.domain.engine.wordfilter import ForbiddenFilter   # noqa: E402
from app.domain.engine.zodiac import Zodiac                # noqa: E402
from app.knowledge.loader import load_knowledge            # noqa: E402
from app.providers import base as providers_base           # noqa: E402
from app.providers import jrdb                             # noqa: F401,E402
from app.services.recommend import RecommendService        # noqa: E402


def recs(path: Path, rec_len: int) -> list[bytes]:
    data = path.read_bytes()
    out, pos = [], 0
    while pos + rec_len <= len(data):
        r = data[pos:pos + rec_len]
        pos += rec_len
        if r.strip():
            out.append(r)
    return out


def fl(r: bytes, st: int, ln: int) -> str:
    return r[st - 1:st - 1 + ln].decode("cp932", errors="replace").strip()


def fnum(s: str):
    try:
        return float(s.strip())
    except ValueError:
        return None


def inum(s: str):
    s = s.strip()
    return int(s) if s and s.lstrip("-").isdigit() else None


def collect() -> list[dict]:
    """SEDのある全開催日について、エンジンを決定的に流して1頭1行に畳む。"""
    kb = load_knowledge(settings.kb_dir, settings.manifest_md)
    if kb.report.status != "ok":
        raise SystemExit(f"正本の検証に失敗: {kb.report.problems}")
    svc = RecommendService(SynchroEngine(kb, Numerology(kb), Zodiac(kb)),
                           ForbiddenFilter(kb, mode=settings.forbidden_filter_mode),
                           providers_base.create_provider("jrdb"))
    rows: list[dict] = []
    for sedfile in sorted(JR.glob("SED*.txt")):
        ymd = sedfile.stem[3:]
        d = date(2000 + int(ymd[:2]), int(ymd[2:4]), int(ymd[4:6]))
        sed = {(fl(r, 1, 8), inum(fl(r, 9, 2))): {
            "chaku": inum(fl(r, 141, 2)), "ijo": inum(fl(r, 143, 1)),
            "win_odds": fnum(fl(r, 175, 6))} for r in recs(sedfile, 376)}
        place_odds: dict = {}
        if (JR / f"OZ{ymd}.txt").exists():
            for r in recs(JR / f"OZ{ymd}.txt", 957):
                raw = r[100:190].decode("cp932", errors="replace")
                for i in range(18):
                    v = fnum(raw[i * 5:(i + 1) * 5])
                    if v:
                        place_odds[(fl(r, 1, 8), i + 1)] = v
        head = {fl(r, 1, 8): inum(fl(r, 95, 2)) for r in recs(JR / f"BAC{ymd}.txt", 184)}
        for it in svc.day_recommendations(d, None, {})["items"]:
            s = sed.get((it["race_id"], it["post_number"]))
            if not s or s["ijo"] != 0:
                continue  # 異常区分は除外
            ph = it.get("physical") or {}
            parts = [v for v in (ph.get("idm10"), ph.get("cyokyo10"), ph.get("joc10"))
                     if v is not None]
            oshi = (it.get("oshi") or {}).get("score")
            phys = sum(parts) / len(parts) if parts else None
            if oshi is not None and phys is not None:
                fifty = round((oshi + phys) / 2, 1)
            else:
                fifty = round(oshi, 1) if oshi is not None else (
                    round(phys, 1) if phys is not None else None)
            n = head.get(it["race_id"]) or 0
            thr = 2 if 0 < n <= 7 else 3      # 7頭以下は複勝=2着以内
            rows.append({
                "day": ymd, "race_id": it["race_id"], "post": it["post_number"],
                "oshi": oshi, "conf": (it.get("oshi") or {}).get("confidence"),
                "fifty": fifty, "band": ph.get("pop_band"), "cell": ph.get("v4_cell"),
                "p_v4": ph.get("p_v4"), "pop_rank": ph.get("pop_rank"),
                "chaku": s["chaku"], "win": 1 if s["chaku"] == 1 else 0,
                "place": 1 if (s["chaku"] is not None and s["chaku"] <= thr) else 0,
                "win_odds": s["win_odds"],
                "place_odds": place_odds.get((it["race_id"], it["post_number"])),
            })
        print(f"  {ymd}: {sum(1 for r in rows if r['day'] == ymd)}頭", file=sys.stderr)
    return rows


def report(sub: list[dict], label: str) -> None:
    n = len(sub)
    if not n:
        return
    pw = sorted((r["win_odds"] for r in sub if r["win"]), reverse=True)
    pp = sorted((r["place_odds"] for r in sub if r["place"] and r["place_odds"]),
                reverse=True)
    day = defaultdict(list)
    for r in sub:
        day[r["day"]].append(r)
    dw = [100 * sum(x["win_odds"] for x in v if x["win"]) / len(v) for v in day.values()]
    print(f"  {label:<28} n={n:<5} 勝{100*sum(r['win'] for r in sub)/n:5.1f}% "
          f"複{100*sum(r['place'] for r in sub)/n:5.1f}% | "
          f"単{100*sum(pw)/n:6.1f}%(最大除く{100*sum(pw[1:])/n:6.1f}%) "
          f"複{100*sum(pp)/n:6.1f}% | 日中央値{statistics.median(dw):6.1f}% "
          f"100%超{sum(1 for x in dw if x >= 100)}/{len(dw)}日")


def main() -> None:
    cache = REPO / "backend" / "data" / "roi_rows.json"
    if cache.exists() and "--fresh" not in sys.argv:
        rows = json.loads(cache.read_text())
        print(f"キャッシュを使用: {cache}(作り直すなら --fresh)", file=sys.stderr)
    else:
        rows = collect()
        cache.write_text(json.dumps(rows))
    by_race = defaultdict(list)
    for r in rows:
        by_race[(r["day"], r["race_id"])].append(r)
        r["ev"] = (r["p_v4"] * r["place_odds"]) if (r["p_v4"] and r["place_odds"]) else None

    def race_top(key):
        out = []
        for lst in by_race.values():
            c = ([r for r in lst if r[key] is not None and r["conf"] != "low"]
                 or [r for r in lst if r[key] is not None])
            if c:
                out.append(max(c, key=lambda r: r[key]))
        return out

    print("=" * 108)
    print(f"回収率バックテスト  {len(set(r['day'] for r in rows))}開催日 / "
          f"{len(rows)}頭 / {len(by_race)}レース")
    print("  単=確定単勝オッズによる正確値 / 複=前日複勝オッズによる概算(基準行と比べること)")
    print("=" * 108)
    print("\n【基準 — すべてこの行と比べる】")
    report(rows, "全馬(基準)")
    report([r for r in rows if r["pop_rank"] == 1], "前日1番人気を全部")
    print("\n【レース内トップ1点】")
    report(race_top("fifty"), "合トップ(=現行の◎)")
    report(race_top("oshi"), "収束度トップ(占術単独)")
    print("\n【人気帯 × p表v4セル ※in-sample】")
    for b in ("1-3", "4-6", "7+"):
        report([r for r in rows if r["band"] == b], f"帯{b} 全馬")
        for c in ("high/high", "low/low"):
            report([r for r in rows if r["band"] == b and r["cell"] == c], f"  {b} {c}")
    print("\n【帯7+ を掘る】")
    f7 = sorted([r for r in rows if r["band"] == "7+" and r["fifty"] is not None],
                key=lambda r: -r["fifty"])
    for n in (100, 300, 600):
        report(f7[:n], f"帯7+ 合top{n}")
    report([r for r in race_top("oshi") if r["band"] == "7+"], "収トップ かつ 帯7+")
    print("\n【EV(p_v4 × 前日複勝オッズ)】")
    for lo in (1.0, 1.2, 1.5):
        report([r for r in rows if r["ev"] and r["ev"] >= lo], f"EV>={lo}")


if __name__ == "__main__":
    main()
