"""M3: where each Home Assistant gets "poll now" nudges (breadsheet#93)

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-09 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only: a nullable column the running version never reads
    op.add_column('connections', sa.Column('webhook_url', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('connections', 'webhook_url')
