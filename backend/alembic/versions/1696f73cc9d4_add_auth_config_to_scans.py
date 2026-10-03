"""add auth config to scans

Revision ID: 1696f73cc9d4
Revises: 4f6545b2d107
Create Date: 2026-10-03 17:41:10.934494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1696f73cc9d4'
down_revision: Union[str, None] = '4f6545b2d107'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column("auth_config_json", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scans", "auth_config_json")