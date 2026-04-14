"""add_organization_fields_to_users

Revision ID: f0a6f9e4bf04
Revises: 39239e8f225f
Create Date: 2026-04-12 11:16:41.562837

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0a6f9e4bf04'
down_revision: Union[str, None] = '39239e8f225f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('organization', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('inn', sa.String(12), nullable=True))
    op.add_column('users', sa.Column('ogrn', sa.String(15), nullable=True))
    op.add_column('users', sa.Column('kpp', sa.String(9), nullable=True))
    op.add_column('users', sa.Column('media_outlets', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'media_outlets')
    op.drop_column('users', 'kpp')
    op.drop_column('users', 'ogrn')
    op.drop_column('users', 'inn')
    op.drop_column('users', 'organization')
