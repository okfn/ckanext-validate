"""create resource_validation table

Revision ID: 001_resource_validation
Revises:
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa

revision = "001_resource_validation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "resource_validation",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("resource_id", sa.UnicodeText, nullable=False),
        sa.Column("status", sa.UnicodeText, nullable=False),
        sa.Column("error_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_resource_validation_resource_id",
        "resource_validation",
        ["resource_id"],
    )
    op.create_index(
        "ix_resource_validation_created",
        "resource_validation",
        ["created"],
    )
    op.create_index(
        "ix_resource_validation_resource_id_created",
        "resource_validation",
        ["resource_id", "created"],
    )


def downgrade():
    op.drop_index("ix_resource_validation_resource_id_created", "resource_validation")
    op.drop_index("ix_resource_validation_created", "resource_validation")
    op.drop_index("ix_resource_validation_resource_id", "resource_validation")
    op.drop_table("resource_validation")
