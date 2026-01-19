"""add documents table for resume parsing

Revision ID: 5cc099bb7657
Revises: 6910b90f676b
Create Date: 2026-01-19 10:14:52.869761

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5cc099bb7657"
down_revision: Union[str, Sequence[str], None] = "6910b90f676b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create documents table."""
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("s3_key", sa.String(length=1000), nullable=True),
        sa.Column("s3_bucket", sa.String(length=255), nullable=True),
        sa.Column(
            "document_type",
            sa.String(length=50),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("markdown_content", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("graph_node_id", sa.String(length=255), nullable=True),
        sa.Column("ontology_version", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_documents_user_id", "documents", ["user_id"], unique=False)
    op.create_index("ix_documents_task_id", "documents", ["task_id"], unique=False)
    op.create_index(
        "ix_documents_user_status", "documents", ["user_id", "status"], unique=False
    )
    op.create_index(
        "ix_documents_user_created",
        "documents",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop documents table."""
    op.drop_index("ix_documents_user_created", table_name="documents")
    op.drop_index("ix_documents_user_status", table_name="documents")
    op.drop_index("ix_documents_task_id", table_name="documents")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_table("documents")
