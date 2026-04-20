"""Add check_type to check_history

Revision ID: a1b2c3d4e5f6
Revises: f0a6f9e4bf04
Create Date: 2026-04-20 16:12:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f0a6f9e4bf04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "check_history",
        sa.Column(
            "check_type", sa.String(length=50), server_default="text", nullable=False
        ),
    )
    op.create_index("ix_check_history_check_type", "check_history", ["check_type"])


def downgrade() -> None:
    op.drop_index("ix_check_history_check_type", table_name="check_history")
    op.drop_column("check_history", "check_type")
