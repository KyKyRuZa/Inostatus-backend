"""Add key_type, max_uses, used_count to api_keys

Revision ID: 661142230d88
Revises: 4b4a89d8378f
Create Date: 2026-03-26 14:11:55.701414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '661142230d88'
down_revision: Union[str, None] = '4b4a89d8378f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('api_keys', sa.Column('key_type', sa.String(length=50), server_default='free', nullable=False))
    op.add_column('api_keys', sa.Column('max_uses', sa.Integer(), server_default='2', nullable=False))
    op.add_column('api_keys', sa.Column('used_count', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('api_keys', 'used_count')
    op.drop_column('api_keys', 'max_uses')
    op.drop_column('api_keys', 'key_type')
