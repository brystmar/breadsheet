"""created replacement table

Revision ID: 7f0b919bb42d
Revises: c0a8430af76b
Create Date: 2019-02-18 20:39:09.821875

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f0b919bb42d'
down_revision = 'c0a8430af76b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('replacement',
    sa.Column('old', sa.String(length=20), nullable=False),
    sa.Column('new', sa.String(length=20), nullable=True),
    sa.Column('where', sa.String(length=1), nullable=False),
    sa.PrimaryKeyConstraint('old', 'where')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('replacement')
    # ### end Alembic commands ###