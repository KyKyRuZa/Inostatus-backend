"""remove_is_verified_column_from_users

Revision ID: abc123def456
Revises: f0a6f9e4bf04
Create Date: 2026-04-23 15:13:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "abc123def456"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "is_verified")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_verified", sa.Boolean(), nullable=True, server_default=sa.text("false")
        ),
    )
    # If server_default doesn't work, set client default
    # op.alter_column('users', 'is_verified', server_default=None)
