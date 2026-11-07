"""M2: bakes and bake steps

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-06 10:02:30.791507

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only: two new tables the running version never touches (breadsheet#31)
    op.create_table('bakes',
    sa.Column('public_suffix', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('recipe_id', sa.Uuid(), nullable=True),
    sa.Column('name_snapshot', sa.Text(), nullable=False),
    sa.Column('anchor_type', sa.Text(), nullable=False),
    sa.Column('anchor_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('time_zone', sa.Text(), nullable=False),
    sa.Column('alert_mode', sa.Text(), server_default='simple', nullable=False),
    sa.Column('status', sa.Text(), server_default='not_started', nullable=False),
    sa.Column('created_via', sa.Text(), nullable=False),
    sa.Column('idempotency_key', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('projected_end', sa.DateTime(timezone=True), nullable=False),
    sa.Column('outcome', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
    sa.CheckConstraint("alert_mode IN ('simple', 'fancy')", name='alert_mode_valid'),
    sa.CheckConstraint("anchor_type IN ('start', 'finish')", name='anchor_type_valid'),
    sa.CheckConstraint("created_via IN ('web', 'ha', 'agent')", name='created_via_valid'),
    sa.CheckConstraint("status IN ('not_started', 'in_progress', 'completed')", name='bake_status_valid'),
    sa.CheckConstraint("outcome IN ('finished', 'canceled', 'expired')", name='bake_outcome_valid'),
    sa.CheckConstraint("(status = 'completed') = (outcome IS NOT NULL)", name='outcome_only_when_completed'),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], name='fk_bakes_recipe_id_recipes', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_bakes_user_id_users', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('public_suffix', name='uq_bakes_public_suffix'),
    sa.UniqueConstraint('user_id', 'idempotency_key', name='uq_bakes_user_idempotency_key')
    )
    with op.batch_alter_table('bakes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bakes_recipe_id'), ['recipe_id'], unique=False)
        batch_op.create_index('ix_bakes_user_id_status', ['user_id', 'status'], unique=False)

    op.create_table('bake_steps',
    sa.Column('bake_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('text_snapshot', sa.Text(), nullable=False),
    sa.Column('note_snapshot', sa.Text(), nullable=True),
    sa.Column('wait_min', sa.Integer(), nullable=False),
    sa.Column('wait_max', sa.Integer(), nullable=False),
    sa.Column('wait_chosen', sa.Integer(), nullable=False),
    sa.Column('active_seconds', sa.Integer(), nullable=True),
    sa.Column('needs_presence', sa.Boolean(), nullable=True),
    sa.Column('skipped', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
    sa.CheckConstraint('wait_chosen >= 0', name='wait_chosen_valid'),
    sa.ForeignKeyConstraint(['bake_id'], ['bakes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('bake_id', 'position', name='uq_bake_steps_bake_id_position')
    )


def downgrade():
    op.drop_table('bake_steps')
    with op.batch_alter_table('bakes', schema=None) as batch_op:
        batch_op.drop_index('ix_bakes_user_id_status')
        batch_op.drop_index(batch_op.f('ix_bakes_recipe_id'))

    op.drop_table('bakes')
