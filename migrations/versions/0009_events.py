"""M2: product events for usage metrics (breadsheet#34)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only: a new table the running version never touches
    op.create_table(
        'events',
        sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('recipe_id', sa.Uuid(), nullable=True),
        sa.Column('bake_id', sa.Uuid(), nullable=True),
        sa.Column('value', sa.Integer(), nullable=True),
        sa.Column('client', sa.Text(), server_default='web', nullable=False),
        sa.Column('agent_name', sa.Text(), nullable=True),
        sa.CheckConstraint("client IN ('web', 'ha', 'agent')", name='event_client_valid'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_events_type_occurred_at', 'events', ['type', 'occurred_at'])
    op.create_index(op.f('ix_events_user_id'), 'events', ['user_id'])


def downgrade():
    op.drop_index(op.f('ix_events_user_id'), table_name='events')
    op.drop_index('ix_events_type_occurred_at', table_name='events')
    op.drop_table('events')
