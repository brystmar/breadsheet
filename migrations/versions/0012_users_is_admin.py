"""M3: an admin flag on users (breadsheet#86)

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-09 06:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade():
    # Expand-only: a column with a server default, which the running version never reads
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade():
    op.drop_column('users', 'is_admin')
