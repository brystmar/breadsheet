"""M2: usernames unique with `-` and `_` treated as the same (breadsheet#83)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-08 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None

NORMALIZED = "replace(lower(username), '-', '_')"


def upgrade():
    # Safe for the running version: the new index is stricter than the old one, and signup already turns a
    # unique violation into 409 username_taken. Existing users who would now collide stop the migration.
    collisions = op.get_bind().execute(sa.text(f"""
        SELECT {NORMALIZED} AS name, string_agg(username, ', ' ORDER BY created_at) AS usernames
        FROM users GROUP BY 1 HAVING count(*) > 1""")).all()
    if collisions:
        raise RuntimeError("Usernames that would collide once `-` and `_` count as the same: "
                           + "; ".join(row.usernames for row in collisions)
                           + ". Rename one of each before running this migration.")

    op.create_index('uq_users_username_normalized', 'users', [sa.text(NORMALIZED)], unique=True)
    op.drop_index('uq_users_username_lower', table_name='users')


def downgrade():
    op.create_index('uq_users_username_lower', 'users', [sa.text('lower(username)')], unique=True)
    op.drop_index('uq_users_username_normalized', table_name='users')
