"""DataProvider抽象層。占術エンジン・API・文章生成はこの層より下(JV-Link等)を直接参照しない。"""
from abc import ABC, abstractmethod

from app.domain.dto import HorseDTO, JockeyDTO, RaceDTO


class HorseDataProvider(ABC):
    @abstractmethod
    def get_horse(self, horse_id: str) -> HorseDTO | None: ...

    def get_recent_positions(self, horse_id: str) -> list[int] | None:
        """直近の着順系列(新しい順)。未対応プロバイダはNone(戦績数秘は擬似系列で動く)。"""
        return None


class JockeyDataProvider(ABC):
    @abstractmethod
    def get_jockey(self, jockey_id: str) -> JockeyDTO | None: ...


class RaceDataProvider(ABC):
    @abstractmethod
    def get_race(self, race_id: str) -> RaceDTO | None: ...

    def list_races(self, race_date) -> list[RaceDTO]:
        """指定日の開催レース一覧。未対応プロバイダは空リスト(オプション機能)。"""
        return []


class RaceResultProvider(ABC):
    """成績取得(検証設計用)。MVPでは未使用。"""

    @abstractmethod
    def get_results(self, race_id: str) -> list[dict]: ...


class DataProviderSet(HorseDataProvider, JockeyDataProvider, RaceDataProvider, ABC):
    """1プロバイダで馬・騎手・レースを提供する複合インターフェース。"""

    name: str = "abstract"


_REGISTRY: dict[str, type[DataProviderSet]] = {}


def register_provider(name: str):
    def deco(cls: type[DataProviderSet]):
        cls.name = name
        _REGISTRY[name] = cls
        return cls
    return deco


def create_provider(name: str) -> DataProviderSet:
    if name not in _REGISTRY:
        raise KeyError(f"unknown data provider: {name} (available: {list(_REGISTRY)})")
    return _REGISTRY[name]()
