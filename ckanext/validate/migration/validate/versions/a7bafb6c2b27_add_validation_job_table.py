"""add validation_job table

Revision ID: a7bafb6c2b27
Revises: 001_resource_validation
Create Date: 2026-04-15 14:12:18.022408

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7bafb6c2b27'
down_revision = '001_resource_validation'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "resource_validation_jobs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("resource_id", sa.UnicodeText, nullable=False),
        sa.Column("status", sa.UnicodeText, nullable=False),
        sa.Column(
            "create_timestamp",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "finish_timestamp",
            sa.DateTime,
            nullable=True,
        ),
    )
    op.create_index(
        "ix_resource_validation_jobs_resource_id_create_timestamp",
        "resource_validation_jobs",
        ["resource_id", "create_timestamp"],
    )


def downgrade():
    op.drop_index("ix_resource_validation_jobs_resource_id_create_timestamp", "resource_validation_jobs")
    op.drop_table("resource_validation_jobs")
