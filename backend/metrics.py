"""
Usage metrics (breadsheet#34; spec: Usage metrics): one read-only query per question in the spec, run with
`flask --app main metrics`. Product events come from backend/events.py; the rest reads the existing tables.
Metrics for M3 and M4 features (HA pairing, agent imports) report zero until those features record anything.
"""
import click
from flask.cli import with_appcontext
from sqlalchemy import text

# A check-off up to this many seconds after its scheduled time counts as on time
ON_TIME_GRACE = 5 * 60

BAKE_ACTIVITY = "('bake_started', 'step_completed', 'step_skipped', 'bake_completed', 'bake_canceled', 'ics_exported')"

METRICS = [
    ('weekly_active_bakers', "Is anyone using it, and is it growing?", f"""
        SELECT date_trunc('week', occurred_at)::date AS week, count(DISTINCT user_id) AS bakers
        FROM events
        WHERE user_id IS NOT NULL AND type IN {BAKE_ACTIVITY} AND occurred_at >= now() - interval '12 weeks'
        GROUP BY 1 ORDER BY 1"""),

    ('bakes_started_vs_finished', "Do people finish what they start?", """
        SELECT count(*) AS started,
               count(*) FILTER (WHERE outcome = 'finished') AS finished,
               count(*) FILTER (WHERE outcome = 'canceled') AS canceled,
               count(*) FILTER (WHERE outcome = 'expired') AS expired,
               count(*) FILTER (WHERE status <> 'completed') AS still_going
        FROM bakes"""),

    ('step_check_offs', "Are the alerts working? (on time = within 5 minutes of the step's time)", f"""
        SELECT (SELECT count(*) FROM events WHERE type = 'step_completed' AND value <= {ON_TIME_GRACE}) AS on_time,
               (SELECT count(*) FROM events WHERE type = 'step_completed' AND value > {ON_TIME_GRACE}) AS late,
               (SELECT count(*) FROM bake_steps s JOIN bakes b ON b.id = s.bake_id
                WHERE b.status = 'completed' AND s.completed_at IS NULL AND NOT s.skipped) AS never"""),

    ('alert_modes_and_exports', "Which alert path do people pick, and do Simple users actually export?", """
        SELECT b.alert_mode, count(*) AS bakes,
               count(*) FILTER (WHERE EXISTS (SELECT 1 FROM events e
                                              WHERE e.type = 'ics_exported' AND e.bake_id = b.id)) AS exported
        FROM bakes b GROUP BY 1 ORDER BY 1"""),

    ('bakes_with_ha', "Is the integration the reason people come back? (M3: HA pairing)", """
        SELECT count(*) FILTER (WHERE alert_mode = 'fancy') AS fancy_bakes, count(*) AS bakes
        FROM bakes"""),

    ('community', "Is the community library pulling its weight?", """
        SELECT (SELECT count(*) FROM recipes WHERE published_at IS NOT NULL) AS published_now,
               (SELECT count(*) FROM events WHERE type = 'recipe_published') AS times_published,
               (SELECT count(*) FROM events e JOIN recipes r ON r.id = e.recipe_id
                WHERE e.type = 'recipe_copied' AND r.published_at IS NOT NULL) AS community_copies,
               (SELECT count(*) FROM events e JOIN recipes r ON r.id = e.recipe_id
                WHERE e.type = 'recipe_copied' AND r.owner_id IS NULL) AS default_copies"""),

    ('agents', "Are people letting their assistant do the planning? (M4: agent tools and imports)", """
        SELECT (SELECT count(*) FROM bakes WHERE created_via = 'agent') AS bakes_started_by_agents,
               (SELECT count(*) FROM events WHERE type = 'recipe_imported') AS recipes_imported"""),

    ('detailed_recipes', "Is anyone filling in hands-on time?", """
        SELECT detail_level, count(*) AS recipes
        FROM recipes WHERE owner_id IS NOT NULL AND archived_at IS NULL AND NOT is_draft
        GROUP BY 1 ORDER BY 1"""),

    ('most_copied', "Which recipes are worth curating?", """
        SELECT coalesce(r.name, '(deleted)') AS recipe,
               CASE WHEN r.id IS NULL THEN NULL WHEN r.owner_id IS NULL THEN 'default'
                    WHEN r.published_at IS NOT NULL THEN 'community' ELSE 'personal' END AS kind,
               count(*) AS copies
        FROM events e LEFT JOIN recipes r ON r.id = e.recipe_id
        WHERE e.type = 'recipe_copied'
        GROUP BY r.id, r.name, r.owner_id, r.published_at ORDER BY copies DESC, recipe LIMIT 10"""),

    ('waits_outside_range', "Are the recipe ranges realistic?", """
        SELECT count(*) FILTER (WHERE wait_chosen < wait_min OR wait_chosen > wait_max) AS outside,
               count(*) AS steps
        FROM bake_steps WHERE NOT skipped"""),

    ('returning_bakers', "Retention: bakers who start another bake 1 to 30 days after their first", """
        WITH firsts AS (SELECT user_id, min(occurred_at) AS first_at FROM events
                        WHERE type = 'bake_started' AND user_id IS NOT NULL GROUP BY user_id)
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
