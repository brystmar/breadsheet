"""
Usage metrics (breadsheet#34; spec: Usage metrics): one read-only query per question in the spec, run with
`flask --app main metrics`. Product events come from backend/events.py; the rest reads the existing tables.
Metrics for M3 and M4 features (HA pairing, agent imports) report zero until those features record anything.
Test users (usernames starting `test-`, see backend/smoke_users.py) and everything they do are left out.
"""
import click
from flask.cli import with_appcontext
from sqlalchemy import text

# A check-off up to this many seconds after its scheduled time counts as on time
ON_TIME_GRACE = 5 * 60

# The ids of test users, whose activity every metric leaves out
TEST_USER_IDS = "(SELECT id FROM users WHERE lower(username) LIKE 'test-%')"


def real(column: str) -> str:
    """A condition that's true unless `column` (a user id, possibly null) is a test user."""
    return f"({column} IS NULL OR {column} NOT IN {TEST_USER_IDS})"


BAKE_ACTIVITY = "('bake_started', 'step_completed', 'step_skipped', 'bake_completed', 'bake_canceled', 'ics_exported')"

METRICS = [
    ('weekly_active_bakers', "Is anyone using it, and is it growing?", f"""
        SELECT date_trunc('week', occurred_at)::date AS week, count(DISTINCT user_id) AS bakers
        FROM events
        WHERE user_id IS NOT NULL AND {real('user_id')} AND type IN {BAKE_ACTIVITY} AND occurred_at >= now() - interval '12 weeks'
        GROUP BY 1 ORDER BY 1"""),

    ('bakes_started_vs_finished', "Do people finish what they start?", f"""
        SELECT count(*) AS started,
               count(*) FILTER (WHERE outcome = 'finished') AS finished,
               count(*) FILTER (WHERE outcome = 'canceled') AS canceled,
               count(*) FILTER (WHERE outcome = 'expired') AS expired,
               count(*) FILTER (WHERE status <> 'completed') AS still_going
        FROM bakes WHERE {real('user_id')}"""),

    ('step_check_offs', "Are the alerts working? (on time = within 5 minutes of the step's time)", f"""
        SELECT (SELECT count(*) FROM events WHERE type = 'step_completed' AND value <= {ON_TIME_GRACE} AND {real('user_id')}) AS on_time,
               (SELECT count(*) FROM events WHERE type = 'step_completed' AND value > {ON_TIME_GRACE} AND {real('user_id')}) AS late,
               (SELECT count(*) FROM bake_steps s JOIN bakes b ON b.id = s.bake_id
                WHERE b.status = 'completed' AND s.completed_at IS NULL AND NOT s.skipped AND {real('b.user_id')}) AS never"""),

    ('alert_modes_and_exports', "Which alert path do people pick, and do Simple users actually export?", f"""
        SELECT b.alert_mode, count(*) AS bakes,
               count(*) FILTER (WHERE EXISTS (SELECT 1 FROM events e
                                              WHERE e.type = 'ics_exported' AND e.bake_id = b.id)) AS exported
        FROM bakes b WHERE {real('b.user_id')} GROUP BY 1 ORDER BY 1"""),

    ('bakes_with_ha', "Is the integration the reason people come back? (bakes started while HA was paired)", f"""
        SELECT count(*) FILTER (WHERE EXISTS (
                   SELECT 1 FROM connections c
                   WHERE c.user_id = b.user_id AND c.created_at <= b.started_at
                     AND (c.revoked_at IS NULL OR c.revoked_at > b.started_at))) AS with_ha_paired,
               count(*) FILTER (WHERE b.alert_mode = 'fancy') AS fancy_bakes,
               count(*) AS bakes
        FROM bakes b WHERE {real('b.user_id')}"""),

    ('community', "Is the community library pulling its weight?", f"""
        SELECT (SELECT count(*) FROM recipes WHERE published_at IS NOT NULL AND {real('owner_id')}) AS published_now,
               (SELECT count(*) FROM events WHERE type = 'recipe_published' AND {real('user_id')}) AS times_published,
               (SELECT count(*) FROM events e JOIN recipes r ON r.id = e.recipe_id
                WHERE e.type = 'recipe_copied' AND r.published_at IS NOT NULL
                  AND {real('e.user_id')} AND {real('r.owner_id')}) AS community_copies,
               (SELECT count(*) FROM events e JOIN recipes r ON r.id = e.recipe_id
                WHERE e.type = 'recipe_copied' AND r.owner_id IS NULL AND {real('e.user_id')}) AS default_copies"""),

    ('agents', "Are people letting their assistant do the planning? (M4: agent tools and imports)", f"""
        SELECT (SELECT count(*) FROM bakes WHERE created_via = 'agent' AND {real('user_id')}) AS bakes_started_by_agents,
               (SELECT count(*) FROM events WHERE type = 'recipe_imported' AND {real('user_id')}) AS recipes_imported"""),

    ('detailed_recipes', "Is anyone filling in hands-on time?", f"""
        SELECT detail_level, count(*) AS recipes
        FROM recipes WHERE owner_id IS NOT NULL AND {real('owner_id')} AND archived_at IS NULL AND NOT is_draft
        GROUP BY 1 ORDER BY 1"""),

    ('most_copied', "Which recipes are worth curating?", f"""
        SELECT coalesce(r.name, '(deleted)') AS recipe,
               CASE WHEN r.id IS NULL THEN NULL WHEN r.owner_id IS NULL THEN 'default'
                    WHEN r.published_at IS NOT NULL THEN 'community' ELSE 'personal' END AS kind,
               count(*) AS copies
        FROM events e LEFT JOIN recipes r ON r.id = e.recipe_id
        WHERE e.type = 'recipe_copied' AND {real('e.user_id')}
        GROUP BY r.id, r.name, r.owner_id, r.published_at ORDER BY copies DESC, recipe LIMIT 10"""),

    ('waits_outside_range', "Are the recipe ranges realistic?", f"""
        SELECT count(*) FILTER (WHERE s.wait_chosen < s.wait_min OR s.wait_chosen > s.wait_max) AS outside,
               count(*) AS steps
        FROM bake_steps s JOIN bakes b ON b.id = s.bake_id WHERE NOT s.skipped AND {real('b.user_id')}"""),

    ('returning_bakers', "Retention: bakers who start another bake 1 to 30 days after their first", f"""
        WITH firsts AS (SELECT user_id, min(occurred_at) AS first_at FROM events
                        WHERE type = 'bake_started' AND user_id IS NOT NULL AND {real('user_id')}
                        GROUP BY user_id)
        SELECT count(*) AS bakers,
               count(*) FILTER (WHERE EXISTS (
                   SELECT 1 FROM events e
                   WHERE e.user_id = f.user_id AND e.type = 'bake_started'
                     AND e.occurred_at >= f.first_at + interval '1 day'
                     AND e.occurred_at <= f.first_at + interval '30 days')) AS returned
        FROM firsts f"""),
]


def run_metrics(session) -> dict[str, list[dict]]:
    """Every metric's rows, read in one read-only transaction."""
    session.execute(text("SET TRANSACTION READ ONLY"))
    try:
        return {name: [dict(row._mapping) for row in session.execute(text(sql))] for name, _, sql in METRICS}
    finally:
        session.rollback()


@click.command('metrics')
@with_appcontext
def metrics_command():
    """Print the usage metrics (read-only)."""
    from backend.database import db

    results = run_metrics(db.session)
    for name, question, _ in METRICS:
        click.echo(f"\n{name}: {question}")
        rows = results[name]
        if not rows:
            click.echo("  (none yet)")
        for row in rows:
            click.echo("  " + ", ".join(f"{key}={value}" for key, value in row.items()))
