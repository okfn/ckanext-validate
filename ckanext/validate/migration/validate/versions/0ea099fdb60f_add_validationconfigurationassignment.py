"""Add ValidationConfigurationAssignment

Revision ID: 0ea099fdb60f
Revises: 76437dc3696c
Create Date: 2026-07-03 16:18:17.205720

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ea099fdb60f'
down_revision = '76437dc3696c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "validate_validation_configuration_assignment",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("configuration_id", sa.UnicodeText(), nullable=False),
        sa.Column("target_type", sa.UnicodeText(), nullable=False),
        sa.Column("target_id", sa.UnicodeText(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "target_type",
            "target_id",
            name="uq_validation_configuration_target",
        ),
    )

    op.create_index(
        "ix_validation_configuration_assignment_configuration",
        "validate_validation_configuration_assignment",
        ["configuration_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_validation_configuration_assignment_configuration",
        table_name="validate_validation_configuration_assignment",
    )

    op.drop_table("validate_validation_configuration_assignment")
