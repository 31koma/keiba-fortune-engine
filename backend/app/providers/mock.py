"""MockDataProvider: 外部接続なしの固定データ。API動作確認用。"""
from datetime import date, datetime, timezone

from app.domain.dto import HorseDTO, JockeyDTO, RaceDTO, RaceEntryDTO
from app.providers.base import DataProviderSet, register_provider

_NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)

_HORSES = {
    "H001": HorseDTO(
        internal_id="H001", provider_id="mock-h-001",
        registered_name="モックスター", official_english_name="MOCK STAR",
        birth_date=date(2022, 4, 8), sex="牡", sire="MOCK SIRE", dam="MOCK DAM",
        trainer_id="T001", source_provider="mock", retrieved_at=_NOW),
    "H002": HorseDTO(
        internal_id="H002", provider_id="mock-h-002",
        registered_name="モックウインド", official_english_name="MOCK WIND",
        birth_date=date(2021, 3, 21), sex="牝", sire="MOCK GALE", dam="MOCK BREEZE",
        trainer_id="T002", source_provider="mock", retrieved_at=_NOW),
}

_JOCKEYS = {
    "J001": JockeyDTO(
        internal_id="J001", provider_id="mock-j-001", name="模擬 太郎",
        name_roman="TARO MOGI", birth_date=date(1990, 8, 8),
        source_provider="mock", retrieved_at=_NOW),
    "J002": JockeyDTO(
        internal_id="J002", provider_id="mock-j-002", name="模擬 花子",
        name_roman="HANAKO MOGI", birth_date=date(1995, 11, 2),
        source_provider="mock", retrieved_at=_NOW),
}

_RACES = {
    "R001": RaceDTO(
        internal_id="R001", provider_id="mock-r-001", race_date=date(2026, 7, 26),
        racecourse="モック競馬場", race_number=11, race_name="モック記念",
        distance=2000, surface="turf", race_class="G1",
        entries=[RaceEntryDTO(horse_id="H001", jockey_id="J001", post_number=1),
                 RaceEntryDTO(horse_id="H002", jockey_id="J002", post_number=2)],
        source_provider="mock", retrieved_at=_NOW),
}


@register_provider("mock")
class MockDataProvider(DataProviderSet):
    def get_horse(self, horse_id: str) -> HorseDTO | None:
        return _HORSES.get(horse_id)

    def get_jockey(self, jockey_id: str) -> JockeyDTO | None:
        return _JOCKEYS.get(jockey_id)

    def get_race(self, race_id: str) -> RaceDTO | None:
        return _RACES.get(race_id)
