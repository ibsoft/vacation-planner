"""Add user profile fields

Revision ID: 4d8e2c1f9b3a
Revises: 3a36b0a77512
Create Date: 2026-07-03 08:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '4d8e2c1f9b3a'
down_revision = '3a36b0a77512'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('mobile', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('internal_phone', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('avatar_url', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('is_top_management', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_top_management')
        batch_op.drop_column('avatar_url')
        batch_op.drop_column('internal_phone')
        batch_op.drop_column('mobile')
        batch_op.drop_column('phone')
