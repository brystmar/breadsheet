"""M2: recipe detail levels, the Then Wait, and drafts

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-05 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only. The running version doesn't know these columns: new recipes it writes get the server
    #   defaults (simple, not a draft), and steps it writes get a null then_wait with wait_min == wait_max,
    #   whose default wait is that same value.
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('detail_level', sa.Text(), server_default='simple', nullable=False))
        batch_op.add_column(sa.Column('is_draft', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.create_check_constraint('detail_level_valid', "detail_level IN ('simple', 'detailed')")
        batch_op.create_check_constraint('drafts_only_personal', 'owner_id IS NOT NULL OR NOT is_draft')
        batch_op.create_check_constraint('drafts_never_published', 'NOT is_draft OR published_at IS NULL')

    with op.batch_alter_table('recipe_steps', schema=None) as batch_op:
        batch_op.add_column(sa.Column('then_wait', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('active_seconds', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('needs_presence', sa.Boolean(), nullable=True))
        batch_op.create_check_constraint('then_wait_valid', 'then_wait >= 0')
        batch_op.create_check_constraint('active_seconds_valid', 'active_seconds >= 0')

    # Every existing step is simple: its one wait is its Then Wait
    op.execute("UPDATE recipe_steps SET then_wait = wait_min")


def downgrade():
    with op.batch_alter_table('recipe_steps', schema=None) as batch_op:
        batch_op.drop_constraint('active_seconds_valid', type_='check')
        batch_op.drop_constraint('then_wait_valid', type_='check')
        batch_op.drop_column('needs_presence')
        batch_op.drop_column('active_seconds')
        batch_op.drop_column('then_wait')

    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_constraint('drafts_never_published', type_='check')
        batch_op.drop_constraint('drafts_only_personal', type_='check')
        batch_op.drop_constraint('detail_level_valid', type_='check')
        batch_op.drop_column('is_draft')
        batch_op.drop_column('detail_level')
