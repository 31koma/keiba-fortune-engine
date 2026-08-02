"""最小自動テスト: 正本検証・改ざん検知・決定的計算・禁止語・API通し。"""
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.knowledge.loader import load_knowledge


@pytest.fixture(scope="session")
def kb():
    store = load_knowledge(settings.kb_dir, settings.manifest_md)
    assert store.report.status == "ok", store.report.problems
    return store


def test_knowledge_loads_13_files(kb):
    assert kb.report.loaded_file_count == 13
    assert kb.report.version != "unknown"


def test_tamper_detection(tmp_path, kb):
    """1バイト改変でdegradedになること(黙って継続しない)。"""
    kbdir = tmp_path / "db"
    shutil.copytree(settings.kb_dir, kbdir)
    target = kbdir / "numerology_core.json"
    data = json.loads(target.read_text(encoding="utf-8"))
    data["meanings"]["8"]["day_theme"] = "改ざんテスト"
    target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    store = load_knowledge(kbdir, settings.manifest_md)
    assert store.report.status == "degraded"
    assert any("numerology_core" in p for p in store.report.problems)


def test_numerology_deterministic(kb):
    from datetime import date
    from app.domain.engine.numerology import Numerology
    n = Numerology(kb)
    # Decoz法: 2022-04-08 → reduce(4)+reduce(8)+reduce(2+0+2+2=6)=18 → 9
    assert n.life_path(date(2022, 4, 8))["value"] == 9
    # マスターナンバー保持: 1990-08-08 → 8+8+reduce(19)=8+8+1=17→8? 検算: 1+9+9+0=19→10→1; 8+8+1=17→8
    assert n.life_path(date(1990, 8, 8))["value"] == 8
    # universal_day: 2026-07-26 → 2+0+2+6+7+2+6=25→7
    assert n.universal_day(date(2026, 7, 26))["value"] == 7


def test_zodiac_sign_and_boundary(kb):
    from datetime import date
    from app.domain.engine.zodiac import Zodiac
    z = Zodiac(kb)
    s = z.sign_for_date(date(2022, 4, 8))
    assert s["name_en"] == "Aries" and s["boundary_flag"] is False
    b = z.sign_for_date(date(2021, 3, 21))  # 牡羊座開始日=境界
    assert b["boundary_flag"] is True


def test_forbidden_filter(kb):
    from app.core.errors import ForbiddenPhraseError
    from app.domain.engine.wordfilter import ForbiddenFilter
    f = ForbiddenFilter(kb, mode="reject")
    assert f.find("この馬は必ず勝つ") == ["必ず勝つ"]
    with pytest.raises(ForbiddenPhraseError):
        f.apply("的中保証つき")
    assert f.apply("先行有利が出やすい流れ") == "先行有利が出やすい流れ"


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health").json()
    assert r["knowledge_base"]["status"] == "ok"
    assert r["knowledge_base"]["loaded_file_count"] == 13
    assert r["active_data_provider"] == "mock"


def test_profile_mock(client):
    r = client.get("/v1/profile", params={"entity_type": "horse", "entity_id": "H001"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["core_numerology"]["life_path"]["value"] == 9
    assert body["sun_sign"]["name_ja"] == "牡羊座"
    assert "disclaimer" in body and body["used_rules"]


def test_day_fortune(client):
    r = client.get("/v1/day-fortune", params={
        "entity_type": "horse", "entity_id": "H001", "target_date": "2026-07-26"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["universal_day"]["value"] == 7
    assert "interpretation_parts" in body


def test_readings_persisted(client):
    """鑑定がapp_readingsへ保存され、engine_ver=知識ベース版が記録されること。"""
    kb_ver = client.get("/health").json()["knowledge_base"]["version"]
    tr = client.post("/v1/readings/horse-triad", json={
        "horse_id": "H001", "jockey_id": "J001", "race_id": "R001"}).json()
    assert isinstance(tr["reading_id"], int)
    dr = client.get("/v1/day-recommendations",
                    params={"target_date": "2026-07-26"}).json()
    assert isinstance(dr["reading_id"], int)

    lst = client.get("/v1/readings").json()["items"]
    assert len(lst) >= 2
    latest = lst[0]
    assert latest["kind"] == "day_recommendation"
    assert latest["engine_ver"] == kb_ver
    assert latest["rules_ver"] == "oshi_v0"  # 2026-07-19: おすすめ選定は推し度基準

    detail = client.get(f"/v1/readings/{tr['reading_id']}").json()
    assert detail["kind"] == "horse_triad"
    assert detail["payload"]["validation_status"] == "validation_required"
    assert client.get("/v1/readings/999999").status_code == 404


def test_synchro_deterministic(kb):
    """シンクロ度が決定的で0..10に収まり、規則JSON(app_hypothesis)駆動であること。"""
    from datetime import date
    from app.domain.engine.numerology import Numerology
    from app.domain.engine.synchro import SynchroEngine
    from app.domain.engine.zodiac import Zodiac
    from app.providers.mock import MockDataProvider
    p = MockDataProvider()
    eng = SynchroEngine(kb, Numerology(kb), Zodiac(kb))
    race = p.get_race("R001")
    r1 = eng.compute(p.get_horse("H001"), p.get_jockey("J001"), race,
                     date(2026, 7, 26), 2.4, date(1992, 5, 5))
    r2 = eng.compute(p.get_horse("H001"), p.get_jockey("J001"), race,
                     date(2026, 7, 26), 2.4, date(1992, 5, 5))
    assert r1 == r2  # 決定的
    assert 0.0 <= r1["score"] <= 10.0
    assert r1["hypothesis_status"] == "app_hypothesis"
    assert r1["validation_status"] == "validation_required"
    assert r1["pattern"]["type"] in ("resonance", "hidden", "heat", "quiet")
    # 集合意識: オッズが低い(支持が厚い)ほど注目度が高い
    low = eng.collective(2.0)["score"]
    high = eng.collective(50.0)["score"]
    assert low > high
    # オッズ未取得は中立5.0
    assert eng.collective(None)["score"] == 5.0


def test_day_recommendations(client):
    r = client.get("/v1/day-recommendations", params={
        "target_date": "2026-07-26", "user_birth_date": "1992-05-05"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_included"] is True
    assert body["recommendation"] is not None
    assert len(body["items"]) == 4  # R001×2頭 + R002×2頭
    scores = [it["oshi"]["score"] for it in body["items"]]
    assert scores == sorted(scores, reverse=True)  # 推し度降順(最終評価で統一)
    assert body["rule"] == "oshi_v0"
    assert body["recommendation"]["oshi"]["score"] == scores[0]
    # 戦績数秘・調律理論(独自指標): 0-10・本実装(mockでない)・4信号
    for it in body["items"]:
        pn = it["pattern_numerology"]
        assert 0.0 <= pn["score"] <= 10.0
        assert pn["mock"] is False and pn["version"] == "choritsu/1.1"
        assert pn["insufficient"] is False  # mock providerは全馬に戦績あり
        assert pn["mode"] == "full"  # mockは5走=理想窓
        assert pn["confidence"] == 1.0
        assert set(pn["signals"]) == {"phase", "rhythm", "resilience", "keynote"}
    # おすすめ(推し度): 全馬に付与・オッズ非依存・理由と正直な限界表示
    for it in body["items"]:
        o = it["oshi"]
        assert 0.0 <= o["score"] <= 10.0
        assert o["version"] == "oshi/1.0"
        assert o["confidence"] in ("full", "medium", "low")
        assert len(o["reasons"]) >= 1
        assert o["adjusters"]["applied"] == []  # v0: 検証前の要素は不参加
        assert o["hypothesis_status"] == "app_hypothesis"
    assert body["validation_status"] == "validation_required"
    assert "エンターテインメント" in body["disclaimer"]
    # 提示文言が禁止語ゼロであること
    from app.main import STATE
    for it in body["items"]:
        assert STATE["filter"].find(it["synchro"]["pattern"]["line"]) == []
    assert STATE["filter"].find(body["framing"]) == []
    # 利用者なしでも動作(重みを再正規化)
    r2 = client.get("/v1/day-recommendations", params={"target_date": "2026-07-26"})
    assert r2.status_code == 200
    assert r2.json()["user_included"] is False
    # 同一条件の再取得は同じreading_idを返す(重複保存しない)
    r3 = client.get("/v1/day-recommendations", params={"target_date": "2026-07-26"})
    assert r3.json()["reading_id"] == r2.json()["reading_id"]


def test_choritsu_analyzer():
    """調律理論v1: 決定的・境界・構造感度(上昇系列>下降系列)・データ不足の明示。"""
    from app.domain.engine.pattern_numerology import analyze, quality
    # 質変換の性質: 1着と2着の差 > 11着と12着の差(非線形)
    assert (quality(1) - quality(2)) > (quality(11) - quality(12))
    assert quality(1) == 1.0 and quality(18) == 0.0
    # 決定的
    a = analyze([1, 2, 1, 5, 3])
    assert a.score == analyze([1, 2, 1, 5, 3]).score
    assert a.mock is False and 0.0 <= a.score <= 10.0
    # 構造感度: 良化中(新しい順で上昇)は悪化中(その逆)より高い
    improving = analyze([1, 2, 4, 7, 10])   # 新しい順=直近1着へ良化
    declining = analyze([10, 7, 4, 2, 1])   # 直近10着へ悪化
    assert improving.score > declining.score
    # v1.1 適応解析: 走数に応じてモード切替、1走でも読める
    assert analyze([1, 2, 4, 7, 10]).mode == "full"      # 4-5走: 4信号
    trio = analyze([2, 5, 3])                            # 2-3走: 律を除く3信号
    assert trio.mode == "trio" and set(trio.signals) == {"phase", "resilience", "keynote"}
    solo = analyze([1])                                  # 1走: 基調のみ
    assert solo.mode == "solo" and set(solo.signals) == {"keynote"}
    assert solo.insufficient is False and solo.confidence == 0.2
    # 縮約: 1走1着でも満点にはならない(中立5.0へ寄せる)
    assert solo.score < 7.0
    # 信頼度は走数に単調
    assert analyze([1, 2, 1, 5, 3]).confidence > trio.confidence > solo.confidence
    # 解析不能=0走のみ。でっち上げない
    none = analyze(None)
    assert none.insufficient is True and none.mode == "none" and none.score == 5.0
    # 旧版 v1.0 はレジストリに残っている(2走未満はデータ不足)
    old_v = analyze([3], analyzer="choritsu/1.0")
    assert old_v.insufficient is True and old_v.version == "choritsu/1.0"


def test_triad(client):
    r = client.post("/v1/readings/horse-triad", json={
        "horse_id": "H001", "jockey_id": "J001", "race_id": "R001"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["validation_status"] == "validation_required"
    assert "エンターテインメント" in body["disclaimer"]
    assert body["unweighted_raw_features"]["group_score"] in (1, 2, 3)
    # 生成文が禁止語ゼロであること(フィルタ通過済みだが二重確認)
    from app.main import STATE
    assert STATE["filter"].find(body["generated_interpretation"]) == []
