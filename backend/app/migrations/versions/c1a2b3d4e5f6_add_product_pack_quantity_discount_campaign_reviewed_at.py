"""add product pack_of/quantity/discount and campaign.reviewed_at

Revision ID: c1a2b3d4e5f6
Revises: b3c7e9a1f052
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = 'b3c7e9a1f052'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('product', sa.Column('pack_of', sa.String(length=50), nullable=True))
    op.add_column('product', sa.Column('quantity', sa.String(length=50), nullable=True))
    op.add_column('product', sa.Column('discount', sa.String(length=50), nullable=True))
    op.add_column('campaign', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('campaign', 'reviewed_at')
    op.drop_column('product', 'discount')
    op.drop_column('product', 'quantity')
    op.drop_column('product', 'pack_of')
