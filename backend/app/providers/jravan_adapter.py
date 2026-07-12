"""JRA-VANアダプター骨格。JV-Link実接続は行わない。

JV-LinkはWindows専用のため、実装時は別プロジェクトのWindows取得ワーカー
(JV-Link→共通DTO変換→Web側DB/キュー送信)が担当し、Webアプリ本体は
このアダプター経由でDB/キューから共通DTOを読むだけにする。
本アプリはWindows依存コードを一切含まない。
"""
from app.domain.dto import HorseDTO, JockeyDTO, RaceDTO
from app.providers.base import DataProviderSet, register_provider


@register_provider("jravan")
class JraVanAdapter(DataProviderSet):
    """骨格のみ。呼び出すと明示的に未実装エラー。"""

    def get_horse(self, horse_id: str) -> HorseDTO | None:
        raise NotImplementedError("JRA-VAN連携は未実装(Windowsワーカー側で取得予定)")

    def get_jockey(self, jockey_id: str) -> JockeyDTO | None:
        raise NotImplementedError("JRA-VAN連携は未実装(Windowsワーカー側で取得予定)")

    def get_race(self, race_id: str) -> RaceDTO | None:
        raise NotImplementedError("JRA-VAN連携は未実装(Windowsワーカー側で取得予定)")
