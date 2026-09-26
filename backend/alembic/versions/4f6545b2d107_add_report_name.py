"""add report name

Revision ID: 4f6545b2d107
Revises: f77516fcb3f2
Create Date: 2026-09-26 14:28:02.075142

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f6545b2d107"
down_revision: Union[str, None] = "f77516fcb3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the column as nullable first so existing reports can be populated.
    op.add_column(
        "reports",
        sa.Column(
            "report_name",
            sa.String(length=255),
            nullable=True,
        ),
    )

    # Give existing reports a safe legacy name.
    op.execute(
        """
        UPDATE reports
        SET report_name = 'legacy-report-' || id::text
        WHERE report_name IS NULL
        """
    )

    # New reports must always have a name.
    op.alter_column(
        "reports",
        "report_name",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("reports", "report_name")