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
    assert kb.report.version.startswith("v1.2")


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
