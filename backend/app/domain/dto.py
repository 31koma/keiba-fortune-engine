"""共通DTO。全DataProviderはこの形式へ変換する(取得元非依存)。"""
from datetime import date, datetime

from pydantic import BaseModel


class HorseDTO(BaseModel):
    internal_id: str
    provider_id: str
    registered_name: str
    official_english_name: str | None = None
    birth_date: date
    sex: str | None = None
    sire: str | None = None
    dam: str | None = None
    trainer_id: str | None = None
    source_provider: str
    retrieved_at: datetime


class JockeyDTO(BaseModel):
    internal_id: str
    provider_id: str
    name: str
    name_roman: str | None = None
    birth_date: date
    source_provider: str
    retrieved_at: datetime


class RaceEntryDTO(BaseModel):
    horse_id: str
    jockey_id: str
    post_number: int | None = None


class RaceDTO(BaseModel):
    internal_id: str
    provider_id: str
    race_date: date
    racecourse: str
    race_number: int
    race_name: str
    distance: int
    surface: str
    race_class: str | None = None
    entries: list[RaceEntryDTO] = []
    source_provider: str
    retrieved_at: datetime
