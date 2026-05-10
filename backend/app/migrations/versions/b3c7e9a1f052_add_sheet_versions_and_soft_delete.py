"""add sheet_versions, sheet_version_rows, and product.deleted_at

Revision ID: b3c7e9a1f052
Revises: 1dc5331458ba
Create Date: 2026-05-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3c7e9a1f052'
down_revision: Union[str, None] = '1dc5331458ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'product',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'sheet_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('source_ref', sa.String(length=500), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('imported_by', sa.Uuid(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaign.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['imported_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'sheet_version_rows',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('version_id', sa.Uuid(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('data_json', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['version_id'], ['sheet_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('sheet_version_rows')
    op.drop_table('sheet_versions')
    op.drop_column('product', 'deleted_at')
