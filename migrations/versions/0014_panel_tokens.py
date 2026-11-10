"""M3: short-lived tokens for Home Assistant's sidebar panel (breadsheet-hass#5)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only: a new table the running version never reads
    op.create_table(
        'panel_tokens',
        sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('token_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('connection_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index(op.f('ix_panel_tokens_connection_id'), 'panel_tokens', ['connection_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_panel_tokens_connection_id'), table_name='panel_tokens')
    op.drop_table('panel_tokens')
