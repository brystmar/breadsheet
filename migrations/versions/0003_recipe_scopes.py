"""M2: recipe scopes (owner, slug, public suffix, source recipe)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-05 12:00:00.000000

"""
import re
import unicodedata
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def slugify(name: str) -> str:
    """A frozen copy of backend/slugs.py's slugify(), so this migration never changes behavior."""
    ascii_name = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_name.lower()).strip('-')
    return slug[:60].rstrip('-') or 'recipe'


def upgrade():
    # Expand-only: every column is nullable, so the running version (which knows none of them) keeps
    #   working. v1 creates default recipes, which have no owner and no suffix.
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('slug', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('public_suffix', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source_recipe_id', sa.Uuid(), nullable=True))
        batch_op.create_foreign_key('fk_recipes_owner_id_users', 'users', ['owner_id'], ['id'], ondelete='RESTRICT')
        batch_op.create_foreign_key('fk_recipes_source_recipe_id_recipes', 'recipes', ['source_recipe_id'], ['id'],
                                    ondelete='SET NULL')
        batch_op.create_index('ix_recipes_owner_id', ['owner_id'], unique=False)
        batch_op.create_unique_constraint('uq_recipes_public_suffix', ['public_suffix'])
        batch_op.create_check_constraint('suffix_only_for_personal',
                                         '(owner_id IS NULL) = (public_suffix IS NULL)')

    # Default slugs are unique among defaults; personal recipes are found by their suffix instead
    op.create_index('uq_recipes_default_slug', 'recipes', ['slug'], unique=True,
                    postgresql_where=sa.text('owner_id IS NULL'))

    # Give the existing default recipes their slugs, oldest first, so the earlier recipe keeps the plain slug
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT id, name FROM recipes WHERE owner_id IS NULL AND slug IS NULL ORDER BY date_added, id")).all()
    taken = set(connection.execute(sa.text(
        "SELECT slug FROM recipes WHERE owner_id IS NULL AND slug IS NOT NULL")).scalars())
    for recipe_id, name in rows:
        base = candidate = slugify(name)
        n = 2
        while candidate in taken:
            candidate = f'{base}-{n}'
            n += 1
        taken.add(candidate)
        connection.execute(sa.text("UPDATE recipes SET slug = :slug WHERE id = :id"),
                           {'slug': candidate, 'id': recipe_id})


def downgrade():
    op.drop_index('uq_recipes_default_slug', table_name='recipes', postgresql_where=sa.text('owner_id IS NULL'))
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_constraint('suffix_only_for_personal', type_='check')
        batch_op.drop_constraint('uq_recipes_public_suffix', type_='unique')
        batch_op.drop_index('ix_recipes_owner_id')
        batch_op.drop_constraint('fk_recipes_source_recipe_id_recipes', type_='foreignkey')
        batch_op.drop_constraint('fk_recipes_owner_id_users', type_='foreignkey')
        batch_op.drop_column('source_recipe_id')
        batch_op.drop_column('public_suffix')
        batch_op.drop_column('slug')
        batch_op.drop_column('owner_id')
