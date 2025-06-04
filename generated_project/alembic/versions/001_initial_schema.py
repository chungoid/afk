"""Initial schema migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create initial tables"""

    op.create_table('users',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table('audit_log',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Column('table_name', sa.String(100), nullable=True),
        sa.Column('record_id', postgresql.UUID(), nullable=False),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
    )


def downgrade():
    """Drop all tables"""
    op.drop_table('audit_log')
    op.drop_table('users')
