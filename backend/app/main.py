"""競走馬占術エンジン Webアプリ — FastAPIエントリポイント(OpenAPI 3.1)。

起動時: 正本13ファイルの検証ロード → DB接続 → schema.sql適用。
検証不一致は strict=起動失敗 / 非strict=degraded(鑑定系APIは503)。
"""
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.ai.gateway import AITextAssist
from app.core.config import settings
from app.core.errors import (DegradedStateError, ForbiddenPhraseError,
                             KnowledgeGapError, KnowledgeValidationError)
from app.db import repository
from app.db.migrate import upgrade_app_schema
from app.db.session import apply_schema, db_status
from app.domain.engine.numerology import Numerology
from app.domain.engine.wordfilter import ForbiddenFilter
from app.domain.engine.zodiac import Zodiac
from app.knowledge.loader import load_knowledge
from app.providers import base as providers_base
from app.providers import jravan_adapter  # noqa: F401 (登録のため)
from app.providers import jrdb  # noqa: F401 (登録のため)
from app.providers import mock  # noqa: F401 (登録のため)
from app.domain.engine.synchro import SynchroEngine
from app.services.past_races import PastRaceService
from app.services.readings import ReadingService
from app.services.recommend import RecommendService

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    kb = load_knowledge(settings.kb_dir, settings.manifest_md)
    if kb.report.status != "ok" and settings.strict_startup:
        raise KnowledgeValidationError(
            f"正本検証に失敗(strict): {kb.report.problems}")
    STATE["kb"] = kb
    STATE["provider"] = providers_base.create_provider(settings.data_provider)
    STATE["past"] = PastRaceService(STATE["provider"], settings.jrdb_data_dir)
    STATE["ai"] = AITextAssist(enabled=settings.ai_enabled)
    try:  # アプリ運用テーブル(app_*)。正本schema.sqlとは独立にAlembicで管理
        upgrade_app_schema()
        repository.prune_duplicates()  # 鑑定履歴のハウスキーピング(重複整理+VACUUM)
    except Exception as e:  # noqa: BLE001
        STATE["app_schema_error"] = f"{type(e).__name__}: {e}"
    if kb.report.status == "ok":
        num = Numerology(kb, keep_masters_in_cycles=settings.keep_masters_in_cycles)
        zod = Zodiac(kb)
        ff = ForbiddenFilter(kb, mode=settings.forbidden_filter_mode)
        STATE["filter"] = ff
        STATE["service"] = ReadingService(kb, num, zod, ff,
                                          master33=settings.master_33_enabled)
        STATE["recommend"] = RecommendService(
            SynchroEngine(kb, num, zod), ff, STATE["provider"])
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

# フロントエンド(Next.js開発サーバー)からのアクセス許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"], allow_headers=["*"],
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
        "app_schema_error": STATE.get("app_schema_error"),
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
    entity_type: str = Query(pattern="^(horse|jockey|human)$"),
    target_date: date = Query(...),
    entity_id: str | None = None,
    birth_date: date | None = None,
    svc: ReadingService = Depends(get_service),
):
    if entity_id and entity_type != "human":
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


# ---------- GET /v1/month-calendar ----------
@app.get("/v1/month-calendar", tags=["readings"])
def get_month_calendar(
    birth_date: date = Query(...),
    year: int = Query(ge=1900, le=2200),
    month: int = Query(ge=1, le=12),
    entity_type: str = Query("human", pattern="^(horse|jockey|human)$"),
    svc: ReadingService = Depends(get_service),
):
    """日別カレンダー: 指定月の日ごとのパーソナルデー数字+テーマ語。

    正本temporal_cycles.period_roles.personal_day(use_for: 日別カレンダー)準拠。
    テーマ語の提示のみで、吉凶や結果の断定はしない。
    """
    result = svc.month_calendar(entity_type, birth_date, year, month)
    result["disclaimer"] = STATE["filter"].disclaimer
    return result


# ---------- GET /v1/day-recommendations ----------
@app.get("/v1/day-recommendations", tags=["readings"])
def get_day_recommendations(
    target_date: date | None = None,
    user_birth_date: date | None = None,
    _svc: ReadingService = Depends(get_service),  # KB検証済みであることの保証
):
    """今日のおすすめ: 対象日の全出走のシンクロ度(占術4者調和+集合意識=オッズ)。

    target_date省略時は今日から14日先までで最初にレースがある日を自動選択する。
    synchro_v0規則(app_hypothesis/validation_required)による観戦視点の提案であり、
    レース結果の予測・馬券購入の推奨ではない。
    """
    rec: RecommendService = STATE["recommend"]
    if target_date is None:
        # 今日→14日先を優先、無ければ直近過去7日へ(手元の最新開催を出す)
        base = date.today()
        target_date = base
        for i in list(range(0, 15)) + list(range(-1, -8, -1)):
            d = base + timedelta(days=i)
            if STATE["provider"].list_races(d):
                target_date = d
                break
    result = rec.day_recommendations(target_date, user_birth_date, provider_credit())
    top = result.get("recommendation") or {}
    kb_ver = STATE["kb"].report.version
    # 同一条件(日付×ユーザー×版)の鑑定は再保存しない(DB肥大化防止。
    # 生データ+決定的計算なのでいつでも再現可能)
    existing = repository.find_reading_id(
        "day_recommendation", kb_ver, "oshi_v0",
        target_date, user_birth_date)
    result["reading_id"] = existing if existing is not None else \
        repository.save_reading(
            "day_recommendation", kb_ver, result,
            target_date=target_date, user_birth_date=user_birth_date,
            race_id=top.get("race_id"), horse_id=top.get("horse_id"),
            jockey_id=top.get("jockey_id"), rules_ver="oshi_v0",
            score=(top.get("oshi") or {}).get("score"))
    return result


# ---------- GET /v1/past-races(過去レース: 検証用の読み取り専用ビュー) ----------
@app.get("/v1/past-races", tags=["past"])
def get_past_races():
    """過去レース一覧: 開催日(新しい順)ごとのレースと、結果確定・事前評価の有無。

    レース前評価は保存済みスナップショット(app_readings)のみ。確定結果はSED
    (JRDB成績ファイル)由来。KB劣化時でも結果閲覧は可能(鑑定は行わないため)。
    """
    svc: PastRaceService = STATE["past"]
    return svc.list_days()


@app.get("/v1/past-races/{race_id}", tags=["past"])
def get_past_race_detail(race_id: str):
    """過去レース詳細: レース前に保存された星読み評価と確定結果の照合。

    発走後に保存された鑑定は事前評価として返さない(後付け生成の禁止)。
    評価が無い場合は snapshot=null + snapshot_note を返し、結果のみ表示できる。
    """
    svc: PastRaceService = STATE["past"]
    result = svc.race_detail(race_id)
    if result is None:
        raise HTTPException(404, f"race {race_id} not found")
    return result


# ---------- GET /v1/readings(鑑定履歴) ----------
@app.get("/v1/readings", tags=["readings"])
def get_readings(limit: int = Query(20, ge=1, le=100), kind: str | None = None):
    return {"items": repository.list_readings(limit=limit, kind=kind)}


@app.get("/v1/readings/{reading_id:int}", tags=["readings"])
def get_reading_detail(reading_id: int):
    r = repository.get_reading(reading_id)
    if r is None:
        raise HTTPException(404, f"reading {reading_id} not found")
    return r


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
    result = svc.horse_triad(horse, jockey, race, target, provider_credit())
    result["reading_id"] = repository.save_reading(
        "horse_triad", STATE["kb"].report.version, result,
        target_date=target, race_id=req.race_id, horse_id=req.horse_id,
        jockey_id=req.jockey_id, rules_ver="triad_provisional",
        score=result["compatibility_components"]["zodiac_combined_score"]["score"])
    return result
