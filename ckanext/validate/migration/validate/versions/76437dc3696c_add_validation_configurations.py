"""Add validation configurations

Revision ID: 76437dc3696c
Revises: a7bafb6c2b27
Create Date: 2026-07-02 15:17:28.828987

"""
import sqlalchemy as sa
from alembic import op
from ckan.model.types import JsonDictType


# revision identifiers, used by Alembic.
revision = '76437dc3696c'
down_revision = 'a7bafb6c2b27'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "validate_validation_configuration",
        sa.Column(
            "id",
            sa.UnicodeText(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.UnicodeText(),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.UnicodeText(),
            nullable=True,
        ),
        sa.Column(
            "schema_descriptor",
            JsonDictType(),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "create_timestamp",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            sa.DateTime(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=(
                "pk_validate_validation_configuration"
            ),
        ),
        sa.UniqueConstraint(
            "name",
            name=(
                "uq_validate_validation_configuration_name"
            ),
        ),
    )

    op.create_index(
        "ix_validate_validation_configuration_active_name",
        "validate_validation_configuration",
        ["active", "name"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_validate_validation_configuration_active_name",
        table_name="validate_validation_configuration",
    )

    op.drop_table(
        "validate_validation_configuration"
    )
