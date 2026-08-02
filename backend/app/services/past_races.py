"""過去レース閲覧ユースケース(検証用の読み取り専用ビュー)。

原則(憲章の誠実原則に基づく):
- レース前評価 = app_readings に保存済みの day_recommendation スナップショットのみ。
  発走時刻より後に保存された鑑定や、その場での再計算を「レース前評価」として
  提示しない(後付け生成の禁止。無いものは無いと明示する)。
- 確定結果 = JRDB SED(成績)ファイル。正本はローカル data_dir の配布ファイルで、
  DBには複製しない(生データ+決定的パースでいつでも再現可能)。
- 「的中率」とは呼ばず「検証結果」として提示する(結果の予測・保証ではない)。
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from app.db import repository
from app.providers.jrdb import parser

# JRDB異常区分(SED)。0=正常。表記はUI表示用の最小限
IJO_LABELS = {
    1: "出走取消", 2: "発走除外", 3: "競走除外", 4: "競走中止",
    5: "失格", 6: "落馬再騎乗", 7: "降着",
}

SURFACE_JA = {"turf": "芝", "dirt": "ダート", "jump": "障害"}

FRAMING = ("レース前に保存された評価と、確定した結果の照合です。"
           "検証のための表示であり、的中の約束や結果の予測ではありません。")

SNAPSHOT_MISSING_NOTE = "このレースは、レース前の星読み評価が保存されていません。"

_TZ = timedelta(hours=9)  # 日本時間。created_atはUTC保存(SQLite CURRENT_TIMESTAMP)


class PastRaceService:
    def __init__(self, provider, data_dir: str | Path):
        self.provider = provider
        self.data_dir = Path(data_dir)
        self._payload_cache: dict[int, dict] = {}  # reading_id → parsed payload
        self._sed_cache: dict[str, dict[str, list[dict]]] = {}  # ymd → race_key → rows

    # ---------- 確定結果(SED) ----------
    def _sed_dates(self) -> list[date]:
        out = []
        for p in sorted(self.data_dir.glob("SED[0-9]*.txt")):
            try:
                out.append(datetime.strptime(p.stem[3:], "%y%m%d").date())
            except ValueError:
                continue
        return out

    def _bac_dates(self) -> list[date]:
        out = []
        for p in sorted(self.data_dir.glob("BAC[0-9]*.txt")):
            try:
                out.append(datetime.strptime(p.stem[3:], "%y%m%d").date())
            except ValueError:
                continue
        return out

    def _sed_results(self, d: date) -> dict[str, list[dict]]:
        ymd = d.strftime("%y%m%d")
        if ymd in self._sed_cache:
            return self._sed_cache[ymd]
        path = self.data_dir / f"SED{ymd}.txt"
        by_race: dict[str, list[dict]] = {}
        if path.is_file():
            for row in parser.parse_records(path.read_bytes(), "SED"):
                ijo = parser.to_int(row["ijo_kubun"]) or 0
                by_race.setdefault(row["race_key"], []).append({
                    "post_number": parser.to_int(row["post_number"]),
                    "horse_id": row["pedigree_id"],
                    "chaku": parser.to_int(row["chakujun"]) if ijo == 0 else None,
                    "ijo": ijo,
                    "status": IJO_LABELS.get(ijo, f"異常({ijo})") if ijo != 0 else None,
                    # 取消・除外等は人気・確定オッズが無意味な値になるため出さない
                    "ninki": parser.to_int(row["ninki"]) if ijo == 0 else None,
                    "odds_final": (parser.to_float(row["win_odds_final"])
                                   if ijo == 0 else None),
                })
        self._sed_cache[ymd] = by_race
        return by_race

    def _horse_name(self, horse_id: str, fallback: str = "") -> str:
        h = self.provider.get_horse(horse_id)
        return h.registered_name if h else (fallback or horse_id)

    # ---------- レース前スナップショット(app_readings) ----------
    def _parsed_payload(self, reading: dict) -> dict:
        rid = reading["reading_id"]
        if rid not in self._payload_cache:
            try:
                self._payload_cache[rid] = json.loads(reading["payload"])
            except (TypeError, ValueError):
                self._payload_cache[rid] = {}
        return self._payload_cache[rid]

    @staticmethod
    def _race_start(race_date: date, start_time: str | None) -> datetime:
        """発走時刻(JST)。不明なら当日0時=保守側(前日までの保存のみ事前扱い)。"""
        if start_time and len(start_time) == 5 and start_time[2] == ":":
            return datetime(race_date.year, race_date.month, race_date.day,
                            int(start_time[:2]), int(start_time[3:]))
        return datetime(race_date.year, race_date.month, race_date.day)

    def _pre_race_snapshot(self, race_date: date, race_id: str,
                           start_time: str | None) -> dict | None:
        """発走前に保存された最古のスナップショットからrace_id分の項目を返す。

        客観(user_included=False)を優先する(検証は誰の誕生日にも依存させない)。
        該当が無ければ None(後付けの再計算はしない)。
        """
        readings = repository.list_day_snapshots(race_date)
        deadline = self._race_start(race_date, start_time)
        candidates = sorted(readings, key=lambda r: (r["user_included"],
                                                     r["created_at"] or ""))
        for r in candidates:
            created = r["created_at"]
            if created is None:
                continue
            if isinstance(created, str):
                created = datetime.fromisoformat(created)
            if created.tzinfo is not None:
                created = created.replace(tzinfo=None)
            if created + _TZ >= deadline:
                continue  # 発走後(または不明)に保存されたものは事前評価にしない
            payload = self._parsed_payload(r)
            items = [it for it in (payload.get("items") or [])
                     if it.get("race_id") == race_id]
            if not items:
                continue
            return {"reading": r, "created_jst": created + _TZ, "items": items}
        return None

    def _snapshot_dates(self) -> set[date]:
        return set(repository.list_snapshot_dates())

    # ---------- 一覧 ----------
    def list_days(self, today: date | None = None) -> dict:
        today = today or date.today()
        dates = sorted(set(self._sed_dates())
                       | {d for d in self._bac_dates() if d < today},
                       reverse=True)
        snapshot_dates = self._snapshot_dates()
        days = []
        for d in dates:
            races = self.provider.list_races(d)
            if not races:
                continue
            sed = self._sed_results(d)
            day_has_snap = d in snapshot_dates
            race_rows = []
            for rc in sorted(races, key=lambda r: (r.racecourse, r.race_number)):
                snap = (self._pre_race_snapshot(d, rc.internal_id, rc.start_time)
                        if day_has_snap else None)
                race_rows.append({
                    "race_id": rc.internal_id,
                    "racecourse": rc.racecourse,
                    "race_number": rc.race_number,
                    "race_name": rc.race_name,
                    "distance": rc.distance,
                    "surface": SURFACE_JA.get(rc.surface, rc.surface),
                    "start_time": rc.start_time,
                    "head_count": len(rc.entries),
                    "grade": rc.race_class,
                    "has_results": rc.internal_id in sed,
                    "has_snapshot": snap is not None,
                })
            days.append({"date": d.isoformat(), "races": race_rows})
        return {"days": days, "framing": FRAMING}

    # ---------- 詳細 ----------
    @staticmethod
    def _item_score(it: dict) -> tuple[float, str]:
        """スナップショット項目の代表スコア。収束度があれば収、無ければシンクロ度。"""
        oshi = it.get("oshi") or {}
        if isinstance(oshi.get("score"), (int, float)):
            return float(oshi["score"]), "oshi"
        sync = it.get("synchro") or {}
        return float(sync.get("score") or 0.0), "synchro"

    def race_detail(self, race_id: str) -> dict | None:
        race = self.provider.get_race(race_id)
        if race is None:
            return None
        d = race.race_date
        sed_rows = self._sed_results(d).get(race_id)

        results = None
        chaku_by_horse: dict[str, dict] = {}
        if sed_rows:
            for row in sed_rows:
                chaku_by_horse[row["horse_id"]] = row
            results = [{
                "chaku": row["chaku"],
                "post_number": row["post_number"],
                "horse_id": row["horse_id"],
                "horse_name": self._horse_name(row["horse_id"]),
                "ninki": row["ninki"],
                "odds_final": row["odds_final"],
                "status": row["status"],
            } for row in sorted(
                sed_rows, key=lambda r: (r["chaku"] is None, r["chaku"] or 99,
                                         r["post_number"] or 99))]

        snap = self._pre_race_snapshot(d, race_id, race.start_time)
        snapshot = None
        verification = None
        if snap:
            scored = []
            for it in snap["items"]:
                score, metric = self._item_score(it)
                scored.append((score, metric, it))
            scored.sort(key=lambda t: (-t[0], t[2].get("post_number") or 99))
            metric = scored[0][1] if scored else "synchro"
            items = []
            for rank, (score, _m, it) in enumerate(scored, start=1):
                sed_row = chaku_by_horse.get(it.get("horse_id") or "")
                tier = ((it.get("oshi") or {}).get("tier") if _m == "oshi"
                        else (it.get("synchro") or {}).get("tier")) or "orange"
                label = ((it.get("oshi") or {}).get("label") if _m == "oshi"
                         else (it.get("synchro") or {}).get("label")) or ""
                items.append({
                    "rank": rank,
                    "post_number": it.get("post_number"),
                    "horse_id": it.get("horse_id"),
                    "horse_name": it.get("horse_name") or "",
                    "jockey_name": it.get("jockey_name") or "",
                    "win_odds": it.get("win_odds"),
                    "score": score,
                    "tier": tier,
                    "label": label,
                    "confidence": (it.get("oshi") or {}).get("confidence"),
                    "chaku": sed_row["chaku"] if sed_row else None,
                    "status": sed_row["status"] if sed_row else None,
                })
            r = snap["reading"]
            snapshot = {
                "saved_at": snap["created_jst"].strftime("%Y-%m-%d %H:%M"),
                "rules_ver": r["rules_ver"],
                "engine_ver": r["engine_ver"],
                "metric": metric,
                "metric_label": "収束度" if metric == "oshi" else "シンクロ度",
                "items": items,
            }
            if results:
                ranked = [x for x in items if x["chaku"] is not None]
                top1 = next((x for x in ranked if x["rank"] == 1), None)
                top3 = [x for x in items if x["rank"] <= 3]
                winner = next((x for x in ranked if x["chaku"] == 1), None)
                verification = {
                    "top1_chaku": top1["chaku"] if top1 else None,
                    "top1_in_top3": (top1["chaku"] <= 3) if top1 else None,
                    "top3_in_top3": sum(1 for x in top3
                                        if x["chaku"] is not None and x["chaku"] <= 3),
                    "winner_rank": winner["rank"] if winner else None,
                    "winner_ninki": (chaku_by_horse.get(winner["horse_id"], {})
                                     .get("ninki") if winner else None),
                }

        return {
            "race": {
                "race_id": race.internal_id,
                "date": d.isoformat(),
                "racecourse": race.racecourse,
                "race_number": race.race_number,
                "race_name": race.race_name,
                "distance": race.distance,
                "surface": SURFACE_JA.get(race.surface, race.surface),
                "start_time": race.start_time,
                "head_count": len(race.entries),
                "grade": race.race_class,
            },
            "results": results,
            "snapshot": snapshot,
            "snapshot_note": None if snapshot else SNAPSHOT_MISSING_NOTE,
            "verification": verification,
            "framing": FRAMING,
        }
