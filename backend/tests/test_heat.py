"""熱量エンジンv1のテスト。

期待値の出どころ:
- 日柱アンカー: 正本 sizhu_day_pillar.json の verification_anchors
- 実データ照合: 2026-08-02 の heat_snapshot(発走前保存)と app_readings id=101 を
  387/387頭で逆算照合して確定した係数(セッションログ 2026-08-02 参照)。
  本テストの期待熱量は「スナップショットの熱量 − ギャップ点」(v1はギャップ非搭載のため)。
"""
import json
from pathlib import Path

import pytest

from app.domain.engine.heat import (
    HeatEngine, day_pillar, load_rules, venue_element, bearing_to_sector)

KB_DIR = Path(__file__).resolve().parents[3] / "KomaVault" / "05_Knowledge" / "占術知識ベース_v1.3"


@pytest.fixture(scope="module")
def engine():
    sizhu = json.loads((KB_DIR / "sizhu_day_pillar.json").read_text(encoding="utf-8"))
    geo = json.loads((KB_DIR / "racecourse_geography.json").read_text(encoding="utf-8"))
    return HeatEngine(load_rules(), sizhu, geo)


# ---- 日柱(正本アンカー+当日) ----

def test_day_pillar_anchors():
    assert day_pillar("1900-01-01") == "甲戌"
    assert day_pillar("2000-01-01") == "戊午"


def test_day_pillar_20260802():
    assert day_pillar("2026-08-02") == "戊申"


# ---- 開催地の五行(方位→五行。2026-08-02の3場) ----

def test_venue_elements(engine):
    geo = engine.geography
    assert venue_element(geo, "sapporo") == "water"   # 北 → 水
    assert venue_element(geo, "niigata") == "water"   # 北 → 水
    assert venue_element(geo, "chukyo") == "metal"    # 西 → 金
    # 基準点(東京)から50km未満の中山・東京は「同じ場」→ 土
    assert venue_element(geo, "tokyo") == "earth"
    assert venue_element(geo, "nakayama") == "earth"


def test_bearing_sector_boundaries():
    assert bearing_to_sector(0.0) == "北"
    assert bearing_to_sector(22.4) == "北"
    assert bearing_to_sector(22.6) == "北東"
    assert bearing_to_sector(337.4) == "北西"
    assert bearing_to_sector(337.6) == "北"


# ---- 実データ照合(2026-08-02、期待値=スナップショット熱量−ギャップ点) ----

CASES = [
    # horse,               birth,        course,    oshi, 期待heat, 期待chi, 期待ten
    ("シーズザスローン",   "2023-03-06", "sapporo", 7.9, 8.90, "同", 5),   # 癸亥 snap9.57-gap0.667
    ("ホウオウヘッセン",   "2023-05-15", "sapporo", 8.1, 9.10, "同", 5),   # 癸酉 snap9.41-gap0.308
    ("ベルヴィヴァン",     "2022-03-18", "niigata", 7.7, 7.70, "出", 5),   # 庚午 snap9.08-gap1.385
    ("ゼルダ",             "2023-04-07", "sapporo", 6.5, 7.00, "育", 3),   # 乙未 snap8.80-gap1.8
    ("セルヴァンス",       "2022-03-08", "chukyo",  6.5, 8.00, "同", 6),   # 庚申 snap8.40-gap0.4
]


@pytest.mark.parametrize("name,birth,course,oshi,want_heat,want_chi,want_ten", CASES)
def test_heat_matches_snapshot_minus_gap(engine, name, birth, course, oshi,
                                         want_heat, want_chi, want_ten):
    r = engine.evaluate(oshi_score=oshi, horse_birth_date=birth,
                        target_date="2026-08-02", course_key=course)
    assert r["heat"] == pytest.approx(want_heat, abs=0.011), name
    assert r["components"]["chi"]["label_ja"] == want_chi, name
    assert r["components"]["ten"]["score"] == want_ten, name


# ---- ギャップ点が存在しないこと(v1の本質) ----

def test_gap_never_scores(engine):
    """fit1位・最低人気でも、人気を渡しても熱量は変わらない。"""
    base = engine.evaluate(oshi_score=7.0, horse_birth_date="2023-03-06",
                           target_date="2026-08-02", course_key="sapporo")
    with_ranks = engine.evaluate(oshi_score=7.0, horse_birth_date="2023-03-06",
                                 target_date="2026-08-02", course_key="sapporo",
                                 fit_rank=1, pop_rank=14)
    assert base["heat"] == with_ranks["heat"]
    # 代わりに物語チップが付く
    assert any(c["id"] == "hidden_heat" for c in with_ranks["story_chips"])
    assert not base["story_chips"]


def test_hidden_heat_threshold(engine):
    """ギャップ3未満はチップも付かない。"""
    r = engine.evaluate(oshi_score=7.0, horse_birth_date="2023-03-06",
                        target_date="2026-08-02", course_key="sapporo",
                        fit_rank=1, pop_rank=3)
    assert not r["story_chips"]


# ---- conf low除外・★ ----

def test_conf_low_excluded(engine):
    r = engine.evaluate(oshi_score=9.0, horse_birth_date="2023-03-06",
                        target_date="2026-08-02", course_key="sapporo", confidence="low")
    assert r["eligible"] is False


def test_race_stars(engine):
    # v1スケールの再較正閾値(2026-08-02、2日62レースの経験分布)
    assert engine.race_stars(9.1) == 6
    assert engine.race_stars(8.9) == 6
    assert engine.race_stars(8.4) == 5
    assert engine.race_stars(7.9) == 4
    assert engine.race_stars(7.3) == 3
    assert engine.race_stars(6.5) == 2
    assert engine.race_stars(6.3) == 1
