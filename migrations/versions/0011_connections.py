"""M3: Home Assistant pairing codes and connections (breadsheet#27)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only: new tables the running version never touches
    op.create_table(
        'connections',
        sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('token_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_connections_user_id'), 'connections', ['user_id'])

    op.create_table(
        'pairing_codes',
        sa.Column('code_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('code_hash')
    )
    op.create_index(op.f('ix_pairing_codes_user_id'), 'pairing_codes', ['user_id'])


def downgrade():
    op.drop_index(op.f('ix_pairing_codes_user_id'), table_name='pairing_codes')
    op.drop_table('pairing_codes')
    op.drop_index(op.f('ix_connections_user_id'), table_name='connections')
    op.drop_table('connections')
