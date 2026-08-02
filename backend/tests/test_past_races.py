"""過去レース閲覧(PastRaceService)のテスト。

公式仕様書レイアウトどおりの合成レコードで、一覧・詳細・照合・
「発走後に保存された評価を事前評価として出さない」誠実ゲートを確認する。
"""
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from app.providers.jrdb.adapter import JRDBDataProvider
from app.providers.jrdb.spec import LAYOUTS
from app.services import past_races as pr

YMD = "260720"          # 2026-07-20(過去日として扱う)
RACE_DATE = date(2026, 7, 20)
RACE_KEY = "06262011"


def _record(kind: str, fields: dict[str, str]) -> bytes:
    layout = LAYOUTS[kind]
    buf = bytearray(b" " * layout["record_len"])
    buf[-2:] = b"\r\n"
    for name, value in fields.items():
        start, length = layout["fields"][name]
        raw = value.encode("cp932")
        assert len(raw) <= length
        buf[start - 1:start - 1 + len(raw)] = raw
    return bytes(buf)


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    (tmp_path / f"BAC{YMD}.txt").write_bytes(_record("BAC", {
        "race_key": RACE_KEY, "yyyymmdd": "20260720", "start_hhmm": "1540",
        "distance": "1800", "track_code": "1",
        "race_name": "テスト過去記念", "head_count": "02",
    }))
    (tmp_path / f"KYI{YMD}.txt").write_bytes(
        _record("KYI", {"race_key": RACE_KEY, "post_number": "01",
                        "pedigree_id": "11111111", "horse_name": "ホシノアルファ",
                        "base_win_odds": "  2.4", "jockey_code": "00001"})
        + _record("KYI", {"race_key": RACE_KEY, "post_number": "02",
                          "pedigree_id": "22222222", "horse_name": "ホシノベータ",
                          "base_win_odds": "  6.0", "jockey_code": "00001"}))
    (tmp_path / f"UKC{YMD}.txt").write_bytes(
        _record("UKC", {"pedigree_id": "11111111", "horse_name": "ホシノアルファ",
                        "sex_code": "1", "birth_date": "20220408"})
        + _record("UKC", {"pedigree_id": "22222222", "horse_name": "ホシノベータ",
                          "sex_code": "2", "birth_date": "20220521"}))
    (tmp_path / f"KZA{YMD}.txt").write_bytes(_record("KZA", {
        "jockey_code": "00001", "jockey_name": "テスト騎手",
        "birth_date": "19950115"}))
    # SED(確定成績): 2番が1着(3人気)、1番が2着(1人気)
    (tmp_path / f"SED{YMD}.txt").write_bytes(
        _record("SED", {"race_key": RACE_KEY, "post_number": "01",
                        "pedigree_id": "11111111", "ymd": "20260720",
                        "chakujun": "02", "ijo_kubun": "0", "ninki": "01",
                        "win_odds_final": "   2.1"})
        + _record("SED", {"race_key": RACE_KEY, "post_number": "02",
                          "pedigree_id": "22222222", "ymd": "20260720",
                          "chakujun": "01", "ijo_kubun": "0", "ninki": "03",
                          "win_odds_final": "   7.5"}))
    return tmp_path


def _snapshot_reading(created_at: datetime) -> dict:
    """スナップショット1件(星読み順位: アルファ1位・ベータ2位)。"""
    payload = {"items": [
        {"race_id": RACE_KEY, "post_number": 1, "horse_id": "11111111",
         "horse_name": "ホシノアルファ", "jockey_name": "テスト騎手",
         "win_odds": 2.4, "synchro": {"score": 7.2, "tier": "green", "label": "高"},
         "oshi": {"score": 6.8, "tier": "green", "label": "収束", "confidence": "full"}},
        {"race_id": RACE_KEY, "post_number": 2, "horse_id": "22222222",
         "horse_name": "ホシノベータ", "jockey_name": "テスト騎手",
         "win_odds": 6.0, "synchro": {"score": 5.0, "tier": "blue", "label": "中"},
         "oshi": {"score": 4.1, "tier": "blue", "label": "静", "confidence": "medium"}},
    ]}
    return {"reading_id": 1, "created_at": created_at, "rules_ver": "oshi_v0",
            "engine_ver": "v1.2_test", "user_included": False,
            "payload": json.dumps(payload, ensure_ascii=False)}


def _service(data_dir, monkeypatch, readings):
    monkeypatch.setattr(pr.repository, "list_day_snapshots",
                        lambda d: readings if d == RACE_DATE else [])
    monkeypatch.setattr(pr.repository, "list_snapshot_dates",
                        lambda: [RACE_DATE] if readings else [])
    return pr.PastRaceService(JRDBDataProvider(data_dir=data_dir), data_dir)


def test_list_days(data_dir, monkeypatch):
    # 発走15:40(JST)より前=前日22:00(UTC 13:00)に保存 → 事前評価あり
    svc = _service(data_dir, monkeypatch,
                   [_snapshot_reading(datetime(2026, 7, 19, 13, 0))])
    out = svc.list_days(today=date(2026, 7, 25))
    assert len(out["days"]) == 1
    day = out["days"][0]
    assert day["date"] == "2026-07-20"
    race = day["races"][0]
    assert race["has_results"] is True
    assert race["has_snapshot"] is True
    assert race["surface"] == "芝" and race["distance"] == 1800


def test_detail_join_and_verification(data_dir, monkeypatch):
    svc = _service(data_dir, monkeypatch,
                   [_snapshot_reading(datetime(2026, 7, 19, 13, 0))])
    det = svc.race_detail(RACE_KEY)
    assert det["results"][0]["chaku"] == 1
    assert det["results"][0]["horse_name"] == "ホシノベータ"
    snap = det["snapshot"]
    assert snap["metric"] == "oshi"
    assert [it["rank"] for it in snap["items"]] == [1, 2]
    assert snap["items"][0]["horse_name"] == "ホシノアルファ"
    assert snap["items"][0]["chaku"] == 2   # 星読み1位は確定2着
    v = det["verification"]
    assert v["top1_chaku"] == 2 and v["top1_in_top3"] is True
    assert v["winner_rank"] == 2 and v["winner_ninki"] == 3


def test_post_race_saving_is_not_a_snapshot(data_dir, monkeypatch):
    """発走(15:40 JST)後に保存された鑑定は事前評価として出さない。"""
    svc = _service(data_dir, monkeypatch,
                   [_snapshot_reading(datetime(2026, 7, 20, 8, 0))])  # UTC=17:00 JST
    det = svc.race_detail(RACE_KEY)
    assert det["snapshot"] is None
    assert det["snapshot_note"] == pr.SNAPSHOT_MISSING_NOTE
    assert det["results"] is not None  # 結果のみは表示できる


def test_no_snapshot_at_all(data_dir, monkeypatch):
    svc = _service(data_dir, monkeypatch, [])
    det = svc.race_detail(RACE_KEY)
    assert det["snapshot"] is None and det["verification"] is None
    assert det["snapshot_note"] == pr.SNAPSHOT_MISSING_NOTE
