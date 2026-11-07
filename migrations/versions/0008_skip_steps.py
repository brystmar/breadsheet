"""M2: skip a step mid-bake (skipped_at on bake_steps)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only: a nullable column the running version never reads (breadsheet#78)
    with op.batch_alter_table('bake_steps', schema=None) as batch_op:
        batch_op.add_column(sa.Column('skipped_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table('bake_steps', schema=None) as batch_op:
        batch_op.drop_column('skipped_at')
