"""Alembic環境。対象は app_* テーブルのみ(正本schema.sql由来のテーブルは管理しない)。"""
from alembic import context
from sqlalchemy import create_engine

from app.core.config import settings
from app.db.models import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def include_object(obj, name, type_, reflected, compare_to):
    """autogenerate時、app_*以外(=正本テーブル)を無視する。"""
    if type_ == "table":
        return name.startswith("app_") or name == "alembic_version"
    return True


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata,
                      literal_binds=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), pool_pre_ping=True, future=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
