"""M2: recipe categories, prerequisites, and archiving

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

STARTER = 'revive-a-refrigerated-sourdough-starter'
SOURDOUGHS = ('country-sourdough-pain-de-campagne', 'basic-open-crumb-sourdough')


def upgrade():
    # Expand-only: the running version doesn't know these columns or the table, and keeps working
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category', sa.Text(), server_default='bread', nullable=False))
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'recipe_prerequisites',
        sa.Column('recipe_id', sa.Uuid(), nullable=False),
        sa.Column('prerequisite_recipe_id', sa.Uuid(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.CheckConstraint('recipe_id <> prerequisite_recipe_id', name='prerequisite_not_self'),
        sa.ForeignKeyConstraint(['prerequisite_recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('recipe_id', 'prerequisite_recipe_id'),
    )
    op.create_index('ix_recipe_prerequisites_prerequisite_recipe_id', 'recipe_prerequisites',
                    ['prerequisite_recipe_id'])

    # The migrated defaults: the starter recipe is the first prep recipe, and the wild-yeast (sourdough)
    #   breads list it. Poolish and commercial-yeast recipes need nothing beforehand. Matched by default
    #   slug, so a database without these recipes (tests, a fresh branch) is left alone.
    op.execute(f"UPDATE recipes SET category = 'prep' WHERE owner_id IS NULL AND slug = '{STARTER}'")
    op.execute(f"""
        INSERT INTO recipe_prerequisites (recipe_id, prerequisite_recipe_id, position)
        SELECT bread.id, starter.id, 1
        FROM recipes bread, recipes starter
        WHERE bread.owner_id IS NULL AND bread.slug IN {SOURDOUGHS}
          AND starter.owner_id IS NULL AND starter.slug = '{STARTER}'
    """)


def downgrade():
    op.drop_index('ix_recipe_prerequisites_prerequisite_recipe_id', table_name='recipe_prerequisites')
    op.drop_table('recipe_prerequisites')
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_column('archived_at')
        batch_op.drop_column('category')
