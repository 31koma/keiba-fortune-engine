"""DB接続(SQLAlchemy 2)。本番=PostgreSQL(docker-compose)、テスト時のみSQLiteフォールバック可。"""
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

if settings.database_url.startswith("sqlite"):
    Path("./data").mkdir(exist_ok=True)

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def db_status() -> str:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}"


def _to_sqlite_dialect(sql: str) -> str:
    """SQLite開発/テスト時のみの機械的方言変換。正本(schema.sql)は一切変更しない。
    PostgreSQL(本番)では無変換で適用する。意味・構造の変更は行わない。"""
    return (sql
            .replace("DEFAULT now()", "DEFAULT CURRENT_TIMESTAMP")
            .replace("BIGSERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
            .replace("JSONB", "TEXT"))


def apply_schema(schema_sql: str) -> None:
    """正本schema.sqlを適用(既適用ならスキップ)。Alembicは将来導入。"""
    if engine.dialect.name == "sqlite":
        schema_sql = _to_sqlite_dialect(schema_sql)
    with engine.begin() as conn:
        exists = True
        try:
            conn.execute(text("SELECT 1 FROM sources LIMIT 1"))
        except Exception:  # noqa: BLE001
            exists = False
        if exists:
            return
    # コメントを除去し、;区切りで実行(正本のDDLは変更しない)
    stmts = []
    buf: list[str] = []
    for line in schema_sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmts.append("\n".join(buf))
            buf = []
    with engine.begin() as conn:
        for stmt in stmts:
            if stmt.strip():
                conn.exec_driver_sql(stmt)
