"""競走馬占術エンジン Webアプリ — FastAPIエントリポイント(OpenAPI 3.1)。

起動時: 正本13ファイルの検証ロード → DB接続 → schema.sql適用。
検証不一致は strict=起動失敗 / 非strict=degraded(鑑定系APIは503)。
"""
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.ai.gateway import AITextAssist
from app.core.config import settings
from app.core.errors import (DegradedStateError, ForbiddenPhraseError,
                             KnowledgeGapError, KnowledgeValidationError)
from app.db.session import apply_schema, db_status
from app.domain.engine.numerology import Numerology
from app.domain.engine.wordfilter import ForbiddenFilter
from app.domain.engine.zodiac import Zodiac
from app.knowledge.loader import load_knowledge
from app.providers import base as providers_base
from app.providers import jravan_adapter  # noqa: F401 (登録のため)
from app.providers import mock  # noqa: F401 (登録のため)
from app.services.readings import ReadingService

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    kb = load_knowledge(settings.kb_dir, settings.manifest_md)
    if kb.report.status != "ok" and settings.strict_startup:
        raise KnowledgeValidationError(
            f"正本検証に失敗(strict): {kb.report.problems}")
    STATE["kb"] = kb
    STATE["provider"] = providers_base.create_provider(settings.data_provider)
    STATE["ai"] = AITextAssist(enabled=settings.ai_enabled)
    if kb.report.status == "ok":
        num = Numerology(kb, keep_masters_in_cycles=settings.keep_masters_in_cycles)
        zod = Zodiac(kb)
        ff = ForbiddenFilter(kb, mode=settings.forbidden_filter_mode)
        STATE["filter"] = ff
        STATE["service"] = ReadingService(kb, num, zod, ff,
                                          master33=settings.master_33_enabled)
        if settings.apply_schema_on_startup and kb.schema_sql:
            try:
                apply_schema(kb.schema_sql)
            except Exception as e:  # noqa: BLE001
                STATE["schema_error"] = f"{type(e).__name__}: {e}"
    yield
    STATE.clear()


app = FastAPI(
    title="競走馬占術エンジン API",
    version="0.1.0",
    description="数秘術・西洋占星術の知識ベース(正本v1.2)に基づく競走馬鑑定API。"
                "本鑑定はエンターテインメントであり、レース結果を予測・保証しません。",
    lifespan=lifespan,
)


def get_service() -> ReadingService:
    kb = STATE.get("kb")
    if kb is None or kb.report.status != "ok" or "service" not in STATE:
        raise HTTPException(
            status_code=503,
            detail={"error": "knowledge_base_degraded",
                    "problems": kb.report.problems if kb else ["not loaded"]})
    return STATE["service"]


def provider_credit() -> dict:
    return {
        "data_provider_name": settings.data_provider_name,
        "data_provider_credit": settings.data_provider_credit,
        "data_provider_license_status": settings.data_provider_license_status,
    }


@app.exception_handler(KnowledgeGapError)
async def gap_handler(_, exc: KnowledgeGapError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={
        "error": "knowledge_gap",
        "detail": str(exc),
        "action": "アプリ側では補完しません。正本(知識ベース)への追加を提案してください。"})


@app.exception_handler(ForbiddenPhraseError)
async def forbidden_handler(_, exc: ForbiddenPhraseError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={
        "error": "forbidden_phrase_detected", "hits": exc.hits,
        "detail": "生成文が禁止語フィルタに抵触したため応答を拒否しました(mode=reject)。"})


# ---------- GET /health ----------
@app.get("/health", tags=["system"])
def health():
    kb = STATE.get("kb")
    ffilter = STATE.get("filter")
    return {
        "application": "ok",
        "database": db_status(),
        "schema_apply_error": STATE.get("schema_error"),
        "knowledge_base": {
            "status": kb.report.status if kb else "not_loaded",
            "version": kb.report.version if kb else None,
            "loaded_file_count": kb.report.loaded_file_count if kb else 0,
            "expected_file_count": len(kb.report.files) if kb else 0,
            "problems": kb.report.problems if kb else ["not loaded"],
        },
        "active_data_provider": settings.data_provider,
        "forbidden_phrase_filter": ffilter.status if ffilter else "inactive",
    }


# ---------- GET /v1/profile ----------
@app.get("/v1/profile", tags=["readings"])
def get_profile(
    entity_type: str = Query(pattern="^(horse|jockey)$"),
    entity_id: str | None = None,
    birth_date: date | None = None,
    official_english_name: str | None = None,
    svc: ReadingService = Depends(get_service),
):
    name = official_english_name
    if entity_id:
        p = STATE["provider"]
        ent = p.get_horse(entity_id) if entity_type == "horse" else p.get_jockey(entity_id)
        if ent is None:
            raise HTTPException(404, f"{entity_type} {entity_id} not found")
        birth_date = ent.birth_date
        name = name or (ent.official_english_name if entity_type == "horse"
                        else ent.name_roman)
    if birth_date is None:
        raise HTTPException(400, "birth_date または entity_id が必要です")
    result = svc.profile(entity_type, birth_date, name)
    result["provider_credit"] = provider_credit()
    result["disclaimer"] = STATE["filter"].disclaimer
    return result


# ---------- GET /v1/day-fortune ----------
@app.get("/v1/day-fortune", tags=["readings"])
def get_day_fortune(
    entity_type: str = Query(pattern="^(horse|jockey)$"),
    target_date: date = Query(...),
    entity_id: str | None = None,
    birth_date: date | None = None,
    svc: ReadingService = Depends(get_service),
):
    if entity_id:
        p = STATE["provider"]
        ent = p.get_horse(entity_id) if entity_type == "horse" else p.get_jockey(entity_id)
        if ent is None:
            raise HTTPException(404, f"{entity_type} {entity_id} not found")
        birth_date = ent.birth_date
    if birth_date is None:
        raise HTTPException(400, "birth_date または entity_id が必要です")
    result = svc.day_fortune(entity_type, birth_date, target_date)
    result["disclaimer"] = STATE["filter"].disclaimer
    return result


# ---------- POST /v1/readings/horse-triad ----------
class TriadRequest(BaseModel):
    horse_id: str
    jockey_id: str
    race_id: str
    target_date: date | None = None


@app.post("/v1/readings/horse-triad", tags=["readings"])
def post_horse_triad(req: TriadRequest, svc: ReadingService = Depends(get_service)):
    p = STATE["provider"]
    horse, jockey, race = p.get_horse(req.horse_id), p.get_jockey(req.jockey_id), \
        p.get_race(req.race_id)
    for name, obj in (("horse", horse), ("jockey", jockey), ("race", race)):
        if obj is None:
            raise HTTPException(404, f"{name} not found")
    target = req.target_date or race.race_date
    return svc.horse_triad(horse, jockey, race, target, provider_credit())
