"""app_readings: 鑑定履歴テーブル(アプリ運用データ。正本テーブルとは分離)

Revision ID: 0001_app_readings
Revises:
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_app_readings"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_readings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("race_id", sa.String(32), nullable=True),
        sa.Column("horse_id", sa.String(32), nullable=True),
        sa.Column("jockey_id", sa.String(32), nullable=True),
        sa.Column("user_birth_date", sa.Date(), nullable=True),
        sa.Column("engine_ver", sa.String(64), nullable=False),
        sa.Column("rules_ver", sa.String(64), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    op.create_index("ix_app_readings_kind", "app_readings", ["kind"])
    op.create_index("ix_app_readings_target_date", "app_readings", ["target_date"])


def downgrade() -> None:
    op.drop_index("ix_app_readings_target_date", table_name="app_readings")
    op.drop_index("ix_app_readings_kind", table_name="app_readings")
    op.drop_table("app_readings")
