"""Tests for the Alembic migrations: the schema they build, and data changes made inside them."""
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from backend.database import db
from flask_migrate import downgrade, upgrade
from sqlalchemy import text


def test_0003_backfills_default_slugs_oldest_first(app, database):
    with app.app_context():
        db.session.execute(text("TRUNCATE recipes, recipe_steps, replacements, users"))
        db.session.commit()
        downgrade(revision='0002')
        try:
            db.session.execute(text("""
                INSERT INTO recipes (name, date_added) VALUES
                    ('Pain de Campagne', '2019-01-01'),
                    ('Crème Brûlée Brioche', '2019-01-02'),
                    ('Pain de Campagne', '2019-01-03')
            """))
            db.session.commit()
            upgrade(revision='0003')

            rows = db.session.execute(text("SELECT name, slug FROM recipes ORDER BY date_added")).all()
            assert [tuple(r) for r in rows] == [
                ('Pain de Campagne', 'pain-de-campagne'),
                ('Crème Brûlée Brioche', 'creme-brulee-brioche'),
                ('Pain de Campagne', 'pain-de-campagne-2'),
            ]
        finally:
            db.session.rollback()
            db.session.execute(text("TRUNCATE recipes, recipe_steps, replacements, users"))
            db.session.commit()
            upgrade()


def test_migrations_match_the_models(app, database):
    """The schema the migrations build must be exactly what the models describe."""
    with app.app_context(), db.engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={'compare_type': True})
        differences = compare_metadata(context, db.metadata)
    assert differences == [], "The models and migrations differ; add a migration (flask db migrate)"
