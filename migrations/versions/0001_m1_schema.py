"""M1 schema: recipes, recipe_steps, replacements

Revision ID: 0001
Revises: 
Create Date: 2026-11-03 12:34:17.633590

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # M1 tables only; M2 adds ownership, slug, suffix, community, detail, and draft columns
    op.create_table('recipes',
    sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('author', sa.Text(), nullable=True),
    sa.Column('source', sa.Text(), nullable=True),
    sa.Column('url', sa.Text(), nullable=True),
    sa.Column('difficulty', sa.Text(), server_default='Beginner', nullable=False),
    sa.Column('solve_for_start', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_modified', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('replacements',
    sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
    sa.Column('scope', sa.Text(), nullable=False),
    sa.Column('old', sa.Text(collation='C'), nullable=False),
    sa.Column('new', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('scope', 'old')
    )
    op.create_table('recipe_steps',
    sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
    sa.Column('recipe_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('wait_min', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('wait_max', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.CheckConstraint('wait_min >= 0 AND wait_min <= wait_max', name='wait_range_valid'),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('recipe_steps', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recipe_steps_recipe_id'), ['recipe_id'], unique=False)



def downgrade():
    # Drops every M1 table; only for rebuilding a dev or test database
    with op.batch_alter_table('recipe_steps', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recipe_steps_recipe_id'))

    op.drop_table('recipe_steps')
    op.drop_table('replacements')
    op.drop_table('recipes')
