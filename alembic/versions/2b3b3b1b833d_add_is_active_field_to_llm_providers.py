"""add_is_active_field_to_llm_providers

Revision ID: 2b3b3b1b833d
Revises: 5cc099bb7657
Create Date: 2026-01-20 11:21:01.372907

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b3b3b1b833d"
down_revision: Union[str, Sequence[str], None] = "5cc099bb7657"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_active column with default False
    op.add_column(
        "llm_providers",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Create index on is_active for faster queries
    op.create_index("ix_llm_providers_is_active", "llm_providers", ["is_active"])

    # Create partial unique index to ensure only one active provider per user
    op.create_index(
        "ix_llm_providers_user_active",
        "llm_providers",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_llm_providers_user_active", table_name="llm_providers")
    op.drop_index("ix_llm_providers_is_active", table_name="llm_providers")

    # Drop column
    op.drop_column("llm_providers", "is_active")
