"""アプリ運用テーブル(app_*)のORMモデル。

正本schema.sql(知識ベース由来・16テーブル)とは完全に分離する:
- 正本テーブル … Google Drive正本のDDLを無変更適用(db/session.py)。Alembic対象外
- app_*テーブル … アプリの運用データ(鑑定履歴等)。Alembic(migrations/)で差分管理

占術の知識・意味・ルールは一切持たない。
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AppReading(Base):
    """鑑定履歴。engine_ver=生成時の知識ベース版、rules_ver=使用した規則の版。"""

    __tablename__ = "app_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), index=True)  # horse_triad / day_recommendation
    target_date: Mapped[date | None] = mapped_column(Date)
    race_id: Mapped[str | None] = mapped_column(String(32))
    horse_id: Mapped[str | None] = mapped_column(String(32))
    jockey_id: Mapped[str | None] = mapped_column(String(32))
    user_birth_date: Mapped[date | None] = mapped_column(Date)
    engine_ver: Mapped[str] = mapped_column(String(64))   # 知識ベース版(正本参照.md由来)
    rules_ver: Mapped[str | None] = mapped_column(String(64))  # 例: synchro_score_v0
    score: Mapped[float | None] = mapped_column(Float)
    payload: Mapped[str] = mapped_column(Text)  # 応答全文(JSON文字列。SQLiteはTEXT/PGはJSONB相当)
