"""Add email_locale to user

Revision ID: 8f47a1c2d3b4
Revises: 4d8e2c1f9b3a
Create Date: 2026-07-03 14:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '8f47a1c2d3b4'
down_revision = '4d8e2c1f9b3a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('email_locale', sa.String(length=5), nullable=True))


def downgrade():
    op.drop_column('users', 'email_locale')
