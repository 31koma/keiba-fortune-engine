"""鑑定履歴(app_readings)の保存・取得。

保存失敗は鑑定応答を妨げない(Noneを返しAPIは継続)。知識・文言は持たない。
"""
import json
from datetime import date

from sqlalchemy import select

from app.db.models import AppReading
from app.db.session import SessionLocal


def save_reading(kind: str, engine_ver: str, payload: dict, *,
                 target_date: date | None = None,
                 race_id: str | None = None,
                 horse_id: str | None = None,
                 jockey_id: str | None = None,
                 user_birth_date: date | None = None,
                 rules_ver: str | None = None,
                 score: float | None = None) -> int | None:
    try:
        with SessionLocal() as s, s.begin():
            row = AppReading(
                kind=kind, engine_ver=engine_ver,
                payload=json.dumps(payload, ensure_ascii=False, default=str),
                target_date=target_date, race_id=race_id, horse_id=horse_id,
                jockey_id=jockey_id, user_birth_date=user_birth_date,
                rules_ver=rules_ver, score=score)
            s.add(row)
            s.flush()
            return row.id
    except Exception:  # noqa: BLE001 保存失敗で鑑定を落とさない
        return None


def find_reading_id(kind: str, engine_ver: str, rules_ver: str | None,
                    target_date: date | None,
                    user_birth_date: date | None) -> int | None:
    """同一条件の既存鑑定を探す(重複保存の回避用)。"""
    try:
        with SessionLocal() as s:
            q = (select(AppReading.id)
                 .filter_by(kind=kind, engine_ver=engine_ver, rules_ver=rules_ver,
                            target_date=target_date, user_birth_date=user_birth_date)
                 .order_by(AppReading.id.desc()).limit(1))
            return s.execute(q).scalar()
    except Exception:  # noqa: BLE001
        return None


def list_readings(limit: int = 20, kind: str | None = None) -> list[dict]:
    with SessionLocal() as s:
        q = select(AppReading).order_by(AppReading.id.desc()).limit(limit)
        if kind:
            q = q.filter_by(kind=kind)
        return [{
            "reading_id": r.id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "kind": r.kind,
            "target_date": r.target_date.isoformat() if r.target_date else None,
            "race_id": r.race_id, "horse_id": r.horse_id, "jockey_id": r.jockey_id,
            "user_included": r.user_birth_date is not None,
            "engine_ver": r.engine_ver, "rules_ver": r.rules_ver,
            "score": r.score,
        } for r in s.execute(q).scalars()]


def list_day_snapshots(target_date: date) -> list[dict]:
    """指定日のday_recommendation鑑定(レース前スナップショット候補)を返す。

    created_at昇順。payloadは文字列のまま返し、解釈は呼び出し側が行う。
    """
    try:
        with SessionLocal() as s:
            q = (select(AppReading)
                 .filter_by(kind="day_recommendation", target_date=target_date)
                 .order_by(AppReading.created_at.asc(), AppReading.id.asc()))
            return [{
                "reading_id": r.id,
                "created_at": r.created_at,
                "rules_ver": r.rules_ver,
                "engine_ver": r.engine_ver,
                "user_included": r.user_birth_date is not None,
                "payload": r.payload,
            } for r in s.execute(q).scalars()]
    except Exception:  # noqa: BLE001 読み取り失敗は「保存なし」と同じ扱い
        return []


def list_snapshot_dates() -> list[date]:
    """day_recommendation鑑定が存在するtarget_dateの一覧(重複なし)。"""
    try:
        with SessionLocal() as s:
            q = (select(AppReading.target_date).distinct()
                 .filter_by(kind="day_recommendation")
                 .filter(AppReading.target_date.is_not(None)))
            return [d for (d,) in s.execute(q) if d is not None]
    except Exception:  # noqa: BLE001
        return []


def prune_duplicates() -> int:
    """day_recommendationの重複(同一 日付×ユーザー×版)を最新1件だけ残して削除。
    起動時のハウスキーピング用。削除件数を返す。"""
    from sqlalchemy import text
    try:
        with SessionLocal() as s, s.begin():
            r = s.execute(text("""
                DELETE FROM app_readings WHERE kind='day_recommendation'
                AND id NOT IN (
                  SELECT MAX(id) FROM app_readings WHERE kind='day_recommendation'
                  GROUP BY target_date, COALESCE(user_birth_date,''),
                           engine_ver, COALESCE(rules_ver,'')
                )"""))
            deleted = r.rowcount or 0
        if deleted:
            from app.db.session import engine
            if engine.dialect.name == "sqlite":
                with engine.connect() as conn:
                    conn.exec_driver_sql("VACUUM")
        return deleted
    except Exception:  # noqa: BLE001 掃除失敗で起動を止めない
        return 0


def get_reading(reading_id: int) -> dict | None:
    with SessionLocal() as s:
        r = s.get(AppReading, reading_id)
        if r is None:
            return None
        return {"reading_id": r.id, "kind": r.kind, "engine_ver": r.engine_ver,
                "rules_ver": r.rules_ver, "created_at":
                    r.created_at.isoformat() if r.created_at else None,
                "payload": json.loads(r.payload)}
