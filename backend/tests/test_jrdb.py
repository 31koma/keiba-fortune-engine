"""JRDBアダプタのテスト。公式仕様書のレイアウトどおりに合成した固定長レコードで、
パーサ→共通DTO→シンクロエンジンまでの通し動作を確認する(実データ不使用)。
"""
from datetime import date
from pathlib import Path

import pytest

from app.providers.jrdb.adapter import JRDBDataProvider
from app.providers.jrdb.spec import LAYOUTS

@pytest.fixture(scope="module")
def kb():
    from app.core.config import settings
    from app.knowledge.loader import load_knowledge
    store = load_knowledge(settings.kb_dir, settings.manifest_md)
    assert store.report.status == "ok", store.report.problems
    return store


YMD = "260726"  # 2026-07-26
RACE_KEY = "06261111"  # 中山・26年・1回・1日目・11R


def _record(kind: str, fields: dict[str, str]) -> bytes:
    """spec.pyのレイアウトに従い、1始まりバイト位置へ値を書き込んだレコードを作る。"""
    layout = LAYOUTS[kind]
    buf = bytearray(b" " * layout["record_len"])
    buf[-2:] = b"\r\n"
    for name, value in fields.items():
        start, length = layout["fields"][name]
        raw = value.encode("cp932")
        assert len(raw) <= length, f"{kind}.{name} が長すぎます"
        buf[start - 1:start - 1 + len(raw)] = raw
    return bytes(buf)


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    # BAC(番組)
    (tmp_path / f"BAC{YMD}.txt").write_bytes(_record("BAC", {
        "race_key": RACE_KEY, "yyyymmdd": "20260726", "start_hhmm": "1540",
        "distance": "2000", "track_code": "1", "grade_code": "1",
        "race_name": "テスト記念", "head_count": "02",
    }))
    # KYI(出走馬)×2
    kyi = _record("KYI", {
        "race_key": RACE_KEY, "post_number": "01", "pedigree_id": "12345678",
        "horse_name": "テストスター", "base_win_odds": "  2.4",
        "jockey_code": "00001",
    }) + _record("KYI", {
        "race_key": RACE_KEY, "post_number": "02", "pedigree_id": "87654321",
        "horse_name": "テストウインド", "base_win_odds": "  6.0",
        "jockey_code": "00002",
    })
    (tmp_path / f"KYI{YMD}.txt").write_bytes(kyi)
    # UKC(馬マスタ)×2
    ukc = _record("UKC", {
        "pedigree_id": "12345678", "horse_name": "テストスター",
        "sex_code": "1", "birth_date": "20220408",
    }) + _record("UKC", {
        "pedigree_id": "87654321", "horse_name": "テストウインド",
        "sex_code": "2", "birth_date": "20210321",
    })
    (tmp_path / f"UKC{YMD}.txt").write_bytes(ukc)
    # KZA(騎手マスタ)×2
    kza = _record("KZA", {
        "jockey_code": "00001", "jockey_name": "試験太郎", "birth_date": "19900808",
    }) + _record("KZA", {
        "jockey_code": "00002", "jockey_name": "試験花子", "birth_date": "19951102",
    })
    (tmp_path / f"KZA{YMD}.txt").write_bytes(kza)
    # OZ(基準オッズ): 単勝2頭分。2頭目はOZ優先確認のためKYIと違う値にする
    (tmp_path / f"OZ{YMD}.txt").write_bytes(_record("OZ", {
        "race_key": RACE_KEY, "head_count": "02",
        "win_odds": "  2.4  5.8" + " " * 80,
    }))
    return tmp_path


def test_jrdb_provider_dto(data_dir):
    p = JRDBDataProvider(data_dir=data_dir)
    races = p.list_races(date(2026, 7, 26))
    assert len(races) == 1
    race = races[0]
    assert race.internal_id == RACE_KEY
    assert race.racecourse == "中山" and race.race_number == 11
    assert race.distance == 2000 and race.surface == "turf"
    assert race.race_class == "G1"
    assert [e.post_number for e in race.entries] == [1, 2]
    # OZの単勝が優先(2頭目: OZ=5.8, KYI基準=6.0)
    assert race.entries[0].win_odds == 2.4
    assert race.entries[1].win_odds == 5.8

    horse = p.get_horse("12345678")
    assert horse is not None and horse.birth_date == date(2022, 4, 8)
    assert horse.registered_name == "テストスター" and horse.sex == "牡"
    jockey = p.get_jockey("00001")
    assert jockey is not None and jockey.birth_date == date(1990, 8, 8)

    # race_keyからの単独取得(dataディレクトリ走査)
    p2 = JRDBDataProvider(data_dir=data_dir)
    assert p2.get_race(RACE_KEY) is not None


def test_jrdb_missing_odds_fallback(data_dir):
    """OZファイルが無い日はKYIの基準オッズへフォールバックする。"""
    (data_dir / f"OZ{YMD}.txt").unlink()
    p = JRDBDataProvider(data_dir=data_dir)
    race = p.list_races(date(2026, 7, 26))[0]
    assert race.entries[0].win_odds == 2.4
    assert race.entries[1].win_odds == 6.0


def test_jrdb_synchro_end_to_end(kb, data_dir):
    """JRDBのDTOがシンクロエンジンにそのまま流せること(結合確認)。"""
    from app.domain.engine.numerology import Numerology
    from app.domain.engine.synchro import SynchroEngine
    from app.domain.engine.zodiac import Zodiac
    p = JRDBDataProvider(data_dir=data_dir)
    race = p.list_races(date(2026, 7, 26))[0]
    eng = SynchroEngine(kb, Numerology(kb), Zodiac(kb))
    e = race.entries[0]
    r = eng.compute(p.get_horse(e.horse_id), p.get_jockey(e.jockey_id),
                    race, race.race_date, e.win_odds, None)
    assert 0.0 <= r["score"] <= 10.0
    assert r["components"]["collective"]["win_odds"] == 2.4
