"""app_*テーブルのAlembicマイグレーション実行(プログラム起動時用)。

正本schema.sql(知識テーブル)の適用は db/session.py:apply_schema が担い、
本モジュールはアプリ運用テーブル(app_readings等)のみを対象とする。
"""
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import APP_ROOT, settings


def upgrade_app_schema(database_url: str | None = None) -> None:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(APP_ROOT) / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url or settings.database_url)
    command.upgrade(cfg, "head")
