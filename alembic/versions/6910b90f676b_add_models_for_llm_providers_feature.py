"""add models for llm providers feature

Revision ID: 6910b90f676b
Revises:
Create Date: 2026-01-15 23:18:31.574610

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6910b90f676b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "llm_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_type", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("api_key_encrypted", postgresql.BYTEA(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint("latency_ms >= 0", name="ck_latency_non_negative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "provider_type",
            "model_name",
            name="uq_user_provider_model",
        ),
    )
    op.create_index(
        "ix_llm_providers_user_id", "llm_providers", ["user_id"], unique=False
    )
    op.create_index(
        "ix_llm_providers_user_provider",
        "llm_providers",
        ["user_id", "provider_type"],
        unique=False,
    )

    op.create_table(
        "llm_provider_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_provider_events_user",
        "llm_provider_events",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_llm_provider_events_user", table_name="llm_provider_events")
    op.drop_table("llm_provider_events")

    op.drop_index("ix_llm_providers_user_provider", table_name="llm_providers")
    op.drop_index("ix_llm_providers_user_id", table_name="llm_providers")
    op.drop_table("llm_providers")
