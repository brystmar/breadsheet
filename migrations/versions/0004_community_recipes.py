"""M2: community recipes (published_at)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-05 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only: a nullable column the running version doesn't know about, so it keeps working
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_check_constraint('published_only_personal',
                                         'owner_id IS NOT NULL OR published_at IS NULL')

    op.create_index('ix_recipes_published_at', 'recipes', ['published_at'],
                    postgresql_where=sa.text('published_at IS NOT NULL'))


def downgrade():
    op.drop_index('ix_recipes_published_at', table_name='recipes', postgresql_where=sa.text('published_at IS NOT NULL'))
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_constraint('published_only_personal', type_='check')
        batch_op.drop_column('published_at')
