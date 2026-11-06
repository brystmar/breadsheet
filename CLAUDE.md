# breadsheet — Claude Context

## Project Purpose
A recipe scheduling tool that calculates start/finish times for each step of a baking
recipe. Particularly designed for sourdough, which has many time-sensitive steps spread
across multiple days. Given a target finish time, it works backwards to produce a full
schedule. Lives at breadsheet.com.

## Companion Repos
- **This repo** (`brystmar/breadsheet`): Python/Flask backend
- **Frontend** (`brystmar/breadsheet-ui`): React + Vite UI — frontend. It calls
  this backend's `/api/v1` JSON endpoints. (The old Jinja2/WTForms UI was retired years ago.)
- **Planned** (`brystmar/breadsheet-hass`): Home Assistant integration (Second Rise project)

## Stack
| Layer | Technology |
|---|---|
| Language | Python 3.14 (App Engine runtime `python314`) |
| Framework | Flask 3.1, JSON API only (no server-rendered UI): v1 on Flask-RESTful, v2 as a plain Flask blueprint |
| Database | Postgres 18 on Neon |
| ORM | SQLAlchemy 2.1 via Flask-SQLAlchemy |
| Migrations | Alembic via Flask-Migrate (`migrations/`) |
| Frontend | React (breadsheet-ui repo) |
| Cloud | Google App Engine standard (GCP) |
| Local | Docker Compose (Postgres 18 for tests) |
| Tests | pytest against local Postgres (co-located *_test.py files in backend/) |
| IDE | PyCharm Professional |

> **DynamoDB is legacy.** The API ran on DynamoDB + PynamoDB until Second Rise M1 (breadsheet#22). The
> DynamoDB tables (`Recipe`, `Replacement` in `us-west-1`) stay as a fallback until v2 has run
> cleanly for a while (spec: Infrastructure and migration, step 6); no code in this repo reads them
> except the one-time migration script (breadsheet#23). Local `.env` points at a copy in `us-east-2`; production is `us-west-1`.
>
> `etc/migrate_dynamodb.py` loads and verifies in one transaction, comparing the new v1 responses
> with the live production API; it's a dry run unless given `--commit`. See its docstring for usage.
> The Neon `dev` branch is loaded. Production gets loaded at the M1 cutover, right before traffic moves.

### Neon Postgres
- Neon project `winter-sky-40837772` (`breadsheet`), region `aws-us-west-2`, Postgres 18.
  Branches: `production` (default) and `dev` (local development).
- The repo is linked via the git-ignored `.neon` file; `neon checkout <branch>` switches
  branches and pulls that branch's `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED` into `.env`.
  Never put production credentials in local `.env`.
- The app uses the pooled `DATABASE_URL`, which goes through PgBouncer in transaction mode, so
  session state (temp tables, `SET`, advisory locks) can leak between requests. Keep it inside a
  single transaction. `backend/database.py` turns off psycopg's prepared statements and pings
  connections before use, since Neon drops them when it suspends.
- Alembic always uses `DATABASE_URL_UNPOOLED` (`Config.MIGRATIONS_DATABASE_URI`).
- `backend/database_test.py` runs a live round trip against the branch in `.env`; it is
  skipped when `DATABASE_URL` is unset.

## Dependency Versions
Pinned in `requirements.txt` (production) and `requirements-dev.txt` (adds test tools):

| Package | Version |
|---|---|
| Flask | 3.1.3 |
| gunicorn | 26.2.0 (App Engine entrypoint) |
| Flask-RESTful | 0.3.10 (unmaintained since 2023; v1 only, and `/api/v2` doesn't use it) |
| Flask-Cors | 6.0.5 |
| Flask-SQLAlchemy | 3.1.1 (last release 2023; verified with SQLAlchemy 2.1) |
| Flask-Migrate | 4.1.0 |
| SQLAlchemy | 2.1.6 |
| alembic | 1.20.1 |
| psycopg[binary] | 3.3.7 |
| python-dotenv | 1.2.4 |
| Markdown | 3.11.2 |
| appengine-python-standard | 3.1.0 (App Engine shared memcache; pins `urllib3<2`) |
| pytest (dev) | 9.2.0 |

## Repo Structure
```
breadsheet/
├── main.py                  # Entrypoint: creates the app, GCP redirect handler
├── requirements.txt         # Production dependencies (App Engine installs only this)
├── requirements-dev.txt     # Adds pytest
├── app.yaml                 # GCP App Engine config
├── deploy.sh                # No-promote deploy (see Deploys)
├── docker-compose.yaml      # Local Postgres for tests
├── conftest.py              # Pytest fixtures (app, test database, client)
├── migrations/              # Alembic (Flask-Migrate) env and versions
├── etc/
│   ├── migrate_dynamodb.py  # One-time DynamoDB → Postgres load and verification (breadsheet#23)
│   ├── admin_recipes.py     # Export, create and update default recipes with the admin key (breadsheet#28)
│   └── backup_postgres.sh   # Weekly pg_dump to the NAS (breadsheet#25; see Backups)
├── backend/
│   ├── __init__.py          # create_app() factory: db, migrations, CORS, v1 and v2 endpoints
│   ├── config.py            # Config: database URLs, ports, domain, env detection
│   ├── database.py          # SQLAlchemy `db`, Flask-Migrate, Neon engine settings
│   ├── environment.py       # `local`, `ON_APP_ENGINE`, `GCP_PROJECT`; loads `.env`
│   ├── logging_setup.py     # configure_logging(): console locally, JSON on App Engine
│   ├── functions.py         # Utilities incl. replace_text()
│   ├── models.py            # SQLAlchemy models: Recipe, RecipeStep, Replacement, User
│   ├── api_v2.py            # /api/v2 blueprint: error bodies, JSON-only writes, no-store, 503s
│   ├── identity.py          # Keys, usernames, session cookie helpers, current_user()
│   ├── identity_routes.py   # /api/v2/users and /api/v2/session
│   ├── recipe_routes_v2.py  # /api/v2/recipes: scopes, copy, lookups (breadsheet#29)
│   ├── admin_routes.py      # /api/v2/admin/recipes: the admin key, create and edit defaults (breadsheet#28)
│   ├── slugs.py             # Recipe slugs and public suffixes for user-facing URLs
│   ├── cache.py             # Shared memcache on App Engine, in-process dict locally
│   ├── rate_limits.py       # Per-IP fixed-window limits (sign-in and admin failures, signups)
│   ├── recipe_routes.py     # RecipeCollectionApi, RecipeApi (read-only)
│   ├── replacement_routes.py
│   ├── meta_routes.py       # ReadmeApi
│   └── *_test.py            # Co-located test files for each module
├── data/                    # Data fixtures / seed files
├── docs/second-rise.md      # Second Rise spec (source of truth)
└── templates/               # Static App Engine error pages only (referenced in app.yaml)
```

## Data Models (`backend/models.py`)
M1 schema (breadsheet#22), plus `users` (M2, breadsheet#26) and recipe scopes (M2, breadsheet#29). Every table has a UUIDv7 `id` primary key, assigned when the
object is created (Python's `uuid.uuid7()`), with Postgres's `uuidv7()` as the server default.
Times are `timestamptz` in UTC; durations are in seconds. Later milestones add their columns
through new migrations (see the spec's "Schema by milestone").

### `Recipe` (table `recipes`)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid | UUIDv7 |
| `name` | text | Recipe title |
| `author`, `source`, `url` | text | Optional |
| `difficulty` | text | Beginner / Intermediate / Advanced / Expert |
| `solve_for_start` | boolean | Controls UI timing direction |
| `date_added` | timestamptz | Sets the order of the v1 recipe list (the homepage order) |
| `start_time` | timestamptz | |
| `last_modified` | timestamptz | Set on POST and PUT only; reads never write |
| `owner_id` | uuid | FK to `users`; null = a default recipe (admin-owned, read-only for users) |
| `slug` | text | URL slug. Defaults: unique among defaults, never changes. Personal: follows the name. Nullable only until a later contract migration |
| `public_suffix` | text | 6 chars `a-z0-9`, personal recipes only (check constraint), unique |
| `source_recipe_id` | uuid | Where a copy came from; set null if the source is deleted |

`length` (total seconds) is a computed property, the sum of the steps' `wait_min`; it isn't stored.

### `RecipeStep` (table `recipe_steps`)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid | v1's `step_id` |
| `recipe_id` | uuid | FK to `recipes`, cascade delete |
| `position` | integer | Step order from 1; v1's `number` |
| `text` | text | Step directions |
| `note` | text | Optional |
| `wait_min`, `wait_max` | integer | Seconds. Simple steps have `wait_min = wait_max` = v1's `then_wait`. Check: `0 ≤ wait_min ≤ wait_max` |

### `Replacement` (table `replacements`)
Convert-text substitutions. Unique on (`scope`, `old`). `old` uses `COLLATE "C"` (byte order),
which matches DynamoDB's range-key sort; convert-text applies replacements in this order, so
don't change it.

### `User` (table `users`, M2)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid | UUIDv7 |
| `username` | text | Display case kept; unique on `lower(username)` |
| `key_hash` | bytea(32) | SHA-256 of the user's key, unique; the key itself is never stored |
| `created_at`, `last_seen_at` | timestamptz | `last_seen_at` is written at most once a day |

## API Endpoints
### v1
**v1 only ever sees default recipes** (`owner_id IS NULL`): personal recipes never appear in the list and 404 by id. **v1 recipes are read-only** (breadsheet#28): `POST`/`PUT`/`DELETE` return 405, and defaults are managed with the admin key.

All routes use `/api/v1/` prefix. Responses are `{'message': ..., 'data': ...}`, exactly as
they were on DynamoDB.

| Endpoint | Resource |
|---|---|
| `GET /api/v1/recipes` | RecipeCollectionApi |
| `GET /api/v1/recipe/<recipe_id>` | RecipeApi |
| `GET /api/v1/replacements/<scope>` | ReplacementCollectionApi (`all`, `ingredients`, `directions`) |
| `PUT/DELETE /api/v1/replacements/<scope>/<old_value>` | ReplacementCollectionApi |
| `GET /api/v1/readme` | ReadmeApi |

v1 quirks kept on purpose, for identical responses:
- Recipe responses return dates as epoch milliseconds (floats).
- `GET /api/v1/replacements/<scope>/<old_value>` returns 500 (the handler takes no `old_value`).

Changes from the DynamoDB version: GET requests never write, and recipe writes are gone (above).

### v2 (growing by milestone; see the spec's API v2 table)
| Endpoint | Purpose |
|---|---|
| `POST /api/v2/users` | Sign up with `{username}`; returns `{user, key}` (the only time the key is shown) and signs in |
| `POST /api/v2/session` | Sign in with `{key}` |
| `GET /api/v2/session` | The signed-in user, or 401 `not_signed_in` |
| `DELETE /api/v2/session` | Sign out this browser only |
| `GET /api/v2/recipes?q=` | Defaults plus the caller's own recipes, as summaries (no steps) |
| `POST /api/v2/recipes` | Create a personal recipe (signed in) |
| `GET /api/v2/recipes/<id>` | One recipe with steps: defaults for anyone, personal for anyone with the link |
| `PUT`/`DELETE /api/v2/recipes/<id>` | Owner only; defaults → 403 `default_read_only`, others → 403 `not_owner` |
| `POST /api/v2/recipes/<id>/copy` | "Make it mine": an independent personal copy (signed in) |
| `GET /api/v2/recipes/by-slug/<slug>` | Resolve a default's URL, `/recipes/<slug>` |
| `GET /api/v2/recipes/by-suffix/<suffix>` | Resolve a personal URL, `/recipes/<slug>-<suffix>`, with the current slug |
| `POST /api/v2/admin/recipes` | Create a default recipe (admin key); its slug is unique among defaults |
| `PUT /api/v2/admin/recipes/<id>` | Edit a default (admin key); the slug never changes, personal recipes → 404 |

v2 conventions (`backend/api_v2.py`):
- Errors are `{code, message}` with a stable `code` and a message that says what to do next; raise
  `ApiError(status, code, message)`. Unknown paths and wrong methods under `/api/v2` also return JSON.
  Validation errors can add `fields`, mapping each bad field to its message (e.g. `steps[0].text`).
- Recipes are returned as `{recipe: …}` or `{recipes: […]}`, with `id`, `slug`, `path`, `scope`, `owner`,
  `is_mine`, `source_recipe_id`, the descriptive fields, `length_seconds`, timestamps, and steps
  (`id`, `position`, `text`, `note`, `wait_min`, `wait_max`). v1's `solve_for_start`/`start_time` aren't in v2.
- `POST`/`PUT`/`PATCH`/`DELETE` require `Content-Type: application/json` (415 `json_required`).
  Together with `SameSite=Lax` and the CORS allow-list, that's the CSRF protection.
- Every response is `Cache-Control: no-store`. A database `OperationalError` becomes 503
  `service_unavailable` with `Retry-After`.

**Identity** (`backend/identity.py`): keys are 128-bit (`secrets.token_urlsafe(16)`), stored as
SHA-256 and compared with `hmac.compare_digest`. The session is Flask's signed cookie
(`breadsheet_session`: `HttpOnly`, `Secure` except locally, `SameSite=Lax`, one year, refreshed
on use) holding the user id and a fingerprint of the key hash; there's no sessions table. Username
rules: 3–30 ASCII letters, digits, `_` or `-`, starting with a letter, unique ignoring
case, with a reserved list. Key links are `breadsheet.com/k#<key>` (the fragment never reaches a server).

**Admin key** (`backend/admin_routes.py`): a separate secret, not a user role. Callers send
`Authorization: Bearer <admin key>`; the server has only its SHA-256 (`ADMIN_KEY_HASH`) and compares
in constant time. Wrong or missing keys get 401 `admin_key_invalid`; with no hash configured, every
admin request is refused. Archiving defaults comes with breadsheet#59 and admin unpublish with
breadsheet#58. Day to day, use the script (the key comes from the password manager, set for that one
command; `BREADSHEET_API` defaults to production):

```bash
ADMIN_KEY=... python etc/admin_recipes.py export <slug-or-id> > recipe.json   # no key needed
ADMIN_KEY=... python etc/admin_recipes.py update recipe.json
```

`python etc/admin_recipes.py new-key` prints a new key and its hash. A full update re-validates the
recipe, which trims whitespace and turns blank notes into null, so the first save of an old default
can show small diffs.

**Rate limits** (`backend/rate_limits.py`): per IP, 10 failed sign-ins and 10 failed admin requests
per 15 minutes and 5 signups per hour, returning 429 `rate_limited` with `Retry-After`. The IP is App Engine's
`X-Appengine-User-Ip` (`api.breadsheet.com` is DNS-only in Cloudflare). Counters live in
`backend/cache.py`; if the cache fails, requests go through.

## Config & Environment
`backend/environment.py` decides where the app is running, once: `local` is `True` when
`APP_ENV=local`, and `ON_APP_ENGINE` when App Engine sets `GAE_ENV=standard`. It loads `.env` on
import (a no-op on App Engine, where `.env` isn't deployed). `backend/config.py` reads the values.

Set `APP_ENV=local` in `.env` for local development (already present). Do NOT set it
in `env_variables.yaml` — GCP must not see this value.

Key values:
- `APP_ENV` — `local` for local dev; absent/unset for GCP
- `DATABASE_URL` — Neon pooled connection string (locally the `dev` branch)
- `DATABASE_URL_UNPOOLED` — Neon direct connection string, for Alembic
- `BOUND_PORT` — local port (set in `.flaskenv`)
- `DOMAIN_URL` — `breadsheet.com`
- `SECRET_KEY` — signs session cookies, so anyone who has it can sign in as any user. Different in
  every environment (`.env` locally, `env_variables.yaml` in production); never log or commit it.
  `create_app()` refuses to start without one. Rotating it signs every browser out.
- `ADMIN_KEY_HASH` — hex SHA-256 of the admin key (`etc/admin_recipes.py new-key`). Different in
  every environment; the production key itself lives only in the password manager, never in `.env`.
- `LOG_LEVEL` — `DEBUG` locally and `INFO` on App Engine by default
- `LOG_FILE` — optional, local only: also write logs to this file (e.g. `logs/breadsheet.log`)

## Logging
`create_app()` calls `configure_logging()` (`backend/logging_setup.py`) once. Every module just does
`logger = logging.getLogger(__name__)`; never call `basicConfig()` or add handlers elsewhere.
- Locally: readable lines on stderr. On App Engine: one JSON object per line on stdout, which Cloud
  Logging reads for `severity` and groups by request (via `X-Cloud-Trace-Context`). Filter on
  `severity>=ERROR` in the Logs Explorer to find failures.
- In `except` blocks for server-side failures, use `logger.exception(...)` so the traceback is kept
  at ERROR. Bad client input is a WARNING; routine detail is DEBUG.
- Use `%s` arguments (`logger.info("Created recipe %s", recipe.id)`), not f-strings.
- **Never log** request bodies, keys, cookies, `SECRET_KEY`, database URLs, or users' recipe text.
  Log ids instead.

## Running Locally
```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/flask db upgrade      # apply migrations to the Neon dev branch in .env
.venv/bin/python main.py
```
The `.venv` is built on Python 3.14 to match App Engine.

## Migrations
Alembic via Flask-Migrate; `FLASK_APP=main.py` comes from `.flaskenv`.
```bash
.venv/bin/flask db migrate -m "describe the change"   # autogenerate, then review the file
.venv/bin/flask db upgrade                            # apply to the branch in .env
.venv/bin/flask db check                              # confirm models and migrations agree
```
**Expand-then-contract.** The previous app version must always work against the current schema,
because migrations run before the new code takes traffic, and rollback is just moving traffic back.
- Expand: add tables, or add columns as nullable or with defaults. Backfill in the same or a later release.
- Contract: drop or tighten columns (NOT NULL, renames, removals) only in a later release, once no
  deployed version that might take traffic still uses the old shape.
- Never rename a column in one step; add the new one, dual-write, backfill, then drop the old one later.
- Test each migration on the Neon `dev` branch (or a fresh branch from production) first.

## GCP Notes
- `app.yaml` sets `runtime: python314` (newest App Engine standard Python runtime;
  end of support 2030-10-10). App Engine applies patch releases automatically.
- Legacy `breadsheet.appspot.com` requests 301-redirected to `breadsheet.com`
  in `handle_before_request()` in `main.py`
- Instances are F1 (384 MiB). `app.yaml` sets the entrypoint to 2 gunicorn workers × 4 threads
  (about 300 MiB with the App Engine SDK); App Engine's default of 4 workers runs out of memory.
  Check memory before adding heavy dependencies, and look for "Exceeded hard memory limit" in the
  version's logs if a smoke test returns intermittent 503s.
- `app.yaml` enables the shared memcache bundled service with `app_engine_apis: true`. Not
  `app_engine_bundled_services`, which only gcloud's beta schema knows: plain `gcloud app deploy`
  drops it silently. The SDK returns `None` instead of raising when memcache is off, so
  `backend/cache.py` logs a warning when that happens. Confirm the rate limit trips after a deploy.
  `main.py` wraps the app with the SDK's `wrap_wsgi_app` when running on App Engine (`GAE_ENV`).
- `env_variables.yaml` (git-ignored) holds production config, including the production branch's
  pooled `DATABASE_URL` (added at the M1 cutover).

## Deploys
No maintenance windows or maintenance mode.
1. Run new Alembic migrations against production first (`DATABASE_URL_UNPOOLED` for the
   `production` branch, set only for that command, never saved in `.env`). They must be
   expand-then-contract (see Migrations).
2. `./deploy.sh [version]` deploys with `--no-promote`, so the new version gets no traffic.
3. Smoke-test it at `https://<version>-dot-breadsheet.wl.r.appspot.com`. The new version shares the
   production database with the version that still has traffic, so **don't create data the live version
   would show publicly** (e.g. personal recipes, which pre-`m2f` versions list on the homepage) until
   traffic has moved; test those after step 4, then delete the test data.
4. Move traffic: `gcloud app services set-traffic default --splits <version>=1`.
5. Roll back by moving traffic to the previous version. Keep the last few versions deployed;
   delete older ones to stay within App Engine's version limit.

## How Second Rise ships
Trunk-based: `main` is the only long-lived branch, in all three repos. There's no milestone branch.
- **One short-lived branch per issue,** named for it (e.g. `26-users-sessions`), merged into `main`
  by PR with a merge commit. Fixes to the live app follow the same path.
- **Backend work ships to production as it merges** (or in small batches), using the deploy steps
  above. `/api/v2` only adds endpoints, so new ones sit unused until the UI calls them.
- **The UI hides unfinished work behind a milestone toggle** in the footer (breadsheet-ui#41):
  `m1` (today's app, the default) or `m2`, with later milestones added as levels. It's stored in
  the browser only. Releasing a milestone means changing the default level, not merging a branch;
  rolling back means changing it back.
- **v1 must not change.** Any change to a v1 response is a red flag in review. In particular, once
  M2 adds personal and draft recipes to `recipes`, v1 endpoints return defaults only.
- **Migrations are expand-then-contract** (see Migrations), so every deployed version works with
  the current schema whichever way traffic points.

## Backups
Weekly `pg_dump` of the production branch to Thomas's TrueNAS NAS, keeping the newest 12
(`etc/backup_postgres.sh`). The NAS only connects out to Neon. Neon's own point-in-time restore
covers recent mistakes; these dumps cover anything older or a lost Neon project.

**Read-only role.** Backups connect as `breadsheet_backup`, a member of `pg_read_all_data` only
(it covers tables added later, too). Create it with SQL, in the Neon SQL Editor on the target
branch, never on the console's Roles page, which adds roles to `neon_superuser`:
```sql
CREATE ROLE breadsheet_backup LOGIN PASSWORD '<strong random password>';
GRANT pg_read_all_data TO breadsheet_backup;
```

**NAS setup** (TrueNAS SCALE; Docker must be available to root, which on SCALE means Apps has a
pool assigned, under Apps → Configuration → Choose Pool):
- Copy `etc/backup_postgres.sh` to a dataset on the NAS, e.g. `/mnt/<pool>/scripts/`, and `chmod 700` it.
- Create the credentials file, readable only by root (`chmod 600`; the script refuses anything looser):
  ```
  PGHOST=<production direct host, without -pooler>
  PGDATABASE=neondb
  PGUSER=breadsheet_backup
  PGPASSWORD=<password>
  PGSSLMODE=require
  ```
- System → Advanced Settings → Cron Jobs → Add: run as `root`, weekly (Sundays 03:00), command
  `/mnt/<pool>/scripts/backup_postgres.sh /mnt/<pool>/backups/breadsheet /mnt/<pool>/backups/breadsheet-backup.env`.
  Hide standard output but not standard error, so failures reach TrueNAS's alert email.
- The script dumps to a `.partial` file, checks it's a readable archive containing `recipes`, and
  only then renames it and prunes, so failures never delete good backups. `PG_IMAGE` must stay at or
  above the server's major version (Postgres 18).
- Exit codes (TrueNAS's "Run Now" shows only the code): 2 bad arguments or credentials-file
  permissions, 3 `pg_dump` failed (Docker, connection, or login), 4 unreadable dump, 5 no `recipes`
  table (expected before the M1 cutover, while production is empty).

**Restore** (into an empty database, e.g. on a new Neon branch or the local test Postgres):
```bash
docker run --rm -i postgres:18.6 pg_restore --no-owner --no-acl --exit-on-error \
    --dbname="<target URL>" < breadsheet-<timestamp>.dump
```
Then check it with `.venv/bin/python -m etc.migrate_dynamodb --database-url "<target URL>" --verify-only`
(while DynamoDB is still around), or by spot-checking `GET /api/v1/recipes` against the restored data.

## Testing
```bash
docker compose up -d breadsheet-db   # local Postgres 18 on port 5433 (data in tmpfs)
.venv/bin/python -m pytest
```
- Co-located `*_test.py` files alongside each module in `backend/`; `conftest.py` at root.
- Check log output with pytest's built-in `caplog` fixture.
- The `database` fixture rebuilds the test schema from the Alembic migrations (downgrade to base,
  then upgrade), so tests cover the migrations too. The `client` fixture truncates every table.
- Tests that need the database skip when the container isn't running. Tests never touch Neon,
  except the live round trip in `database_test.py`. Override the target with `TEST_DATABASE_URL`.

## Coding Conventions
- `local` and `ON_APP_ENGINE` (from `backend/environment.py`) control local vs. cloud behavior
- Datetimes stored as UTC; v1 `to_dict()` returns ISO strings by default, or epoch ms
  with `dates_as_epoch=True`
- Ids are UUIDv7, assigned by the server; never accept client-supplied ids
- Credentialed CORS on `/api/*` for `Config.CORS_ORIGINS` only: `https://breadsheet.com` and `https://www.breadsheet.com`, plus the Vite dev server when `local`. Never use wildcard origins or set `Access-Control-Allow-Origin` by hand

## Current Status
- Backend stable and deployed to GCP; React (breadsheet-ui) is the only frontend
- Runtime and dependencies upgraded to current stable (Python 3.14, Nov 2026)
- Second Rise M1 complete (2026-11-04): production runs v1 on Neon Postgres
- M2 in progress. Live since 2026-11-05: users, key sign-in, sessions, and rate limits
  (breadsheet#26)
- Backend logging refactor (breadsheet#67) live since 2026-11-05: structured logs on App Engine,
  production `LOG_LEVEL` is `INFO`
- Usernames must start with a letter (breadsheet#69, 2026-11-05)
- Recipe scopes, copy-to-personal, slugs and suffixes (breadsheet#29) live since 2026-11-05
- The reserved usernames `brystmar`, `breadsheet` and `tberg` are registered in production (inserted
  directly, since signup refuses reserved names); their keys are with Thomas
- Admin key and read-only v1 (breadsheet#28) live since 2026-11-05; the UI's v1 edit controls were
  removed first (breadsheet-ui#45)
- App Engine version `m2g` serves all traffic; `m2f` is the rollback target (it only reopens v1
  recipe writes). `py314` (the DynamoDB version) is kept until DynamoDB is retired

## Second Rise spec
The source of truth is `./docs/second-rise.md`, in this repo. Read it before planning or executing any Second Rise work. If it needs changes, say so and stop.

The backlog is GitHub issues across breadsheet, breadsheet-ui, and breadsheet-hass; the spec's
backlog table links each one. Refer to work by issue (`breadsheet#26`), always with its title,
never by the old spec item numbers. Each repo has milestones M1–M4 with matching labels; the
`parked` and `decision` labels mark the rest.
