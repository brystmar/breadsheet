"""M2: users

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only: a new table, so the running M1 version is unaffected
    op.create_table('users',
    sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
    sa.Column('username', sa.Text(), nullable=False),
    sa.Column('key_hash', sa.LargeBinary(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key_hash')
    )
    op.create_index('uq_users_username_lower', 'users', [sa.text('lower(username)')], unique=True)


def downgrade():
    op.drop_index('uq_users_username_lower', table_name='users')
    op.drop_table('users')
