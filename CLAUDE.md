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
| Framework | Flask 3.1 + Flask-RESTful (JSON API only, no server-rendered UI) |
| Database | Postgres 18 on Neon |
| ORM | SQLAlchemy 2.1 via Flask-SQLAlchemy |
| Migrations | Alembic via Flask-Migrate (`migrations/`) |
| Frontend | React (breadsheet-ui repo) |
| Cloud | Google App Engine standard (GCP) |
| Local | Docker Compose (Postgres 18 for tests) |
| Tests | pytest against local Postgres (co-located *_test.py files in backend/) |
| IDE | PyCharm Professional |

> **DynamoDB is legacy.** The API ran on DynamoDB + PynamoDB until Second Rise item 3. The
> DynamoDB tables (`Recipe`, `Replacement` in `us-west-1`) stay as a fallback until v2 has run
> cleanly for a while (spec item 6); no code in this repo reads them except the one-time
> migration script (item 4). Local `.env` points at a copy in `us-east-2`; production is `us-west-1`.
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
| Flask-RESTful | 0.3.10 (unmaintained since 2023; candidate for removal with `/api/v2`) |
| Flask-Cors | 6.0.5 |
| Flask-SQLAlchemy | 3.1.1 (last release 2023; verified with SQLAlchemy 2.1) |
| Flask-Migrate | 4.1.0 |
| SQLAlchemy | 2.1.6 |
| alembic | 1.20.1 |
| psycopg[binary] | 3.3.7 |
| python-dotenv | 1.2.4 |
| Markdown | 3.11.2 |
| pytest (dev) | 9.2.0 |
| testfixtures (dev) | 12.4.0 |

## Repo Structure
```
breadsheet/
├── main.py                  # Entrypoint: creates the app, GCP redirect handler
├── requirements.txt         # Production dependencies (App Engine installs only this)
├── requirements-dev.txt     # Adds pytest and testfixtures
├── app.yaml                 # GCP App Engine config
├── deploy.sh                # No-promote deploy (see Deploys)
├── docker-compose.yaml      # Local Postgres for tests
├── conftest.py              # Pytest fixtures (app, test database, client)
├── migrations/              # Alembic (Flask-Migrate) env and versions
├── etc/
│   └── migrate_dynamodb.py  # One-time DynamoDB → Postgres load and verification (item 4)
├── backend/
│   ├── __init__.py          # create_app() factory: db, migrations, CORS, endpoints
│   ├── config.py            # Config: database URLs, ports, domain, env detection
│   ├── database.py          # SQLAlchemy `db`, Flask-Migrate, Neon engine settings
│   ├── global_logger.py     # Logger + `local` bool (True when APP_ENV=local)
│   ├── functions.py         # Utilities incl. replace_text()
│   ├── models.py            # SQLAlchemy models: Recipe, RecipeStep, Replacement
│   ├── recipe_routes.py     # RecipeCollectionApi, RecipeApi
│   ├── replacement_routes.py
│   ├── meta_routes.py       # ReadmeApi
│   └── *_test.py            # Co-located test files for each module
├── data/                    # Data fixtures / seed files
├── docs/second-rise.md      # Second Rise spec (source of truth)
└── templates/               # Static App Engine error pages only (referenced in app.yaml)
```

## Data Models (`backend/models.py`)
M1 schema (Second Rise item 3). Every table has a UUIDv7 `id` primary key, assigned when the
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

## API Endpoints
All routes use `/api/v1/` prefix. Responses are `{'message': ..., 'data': ...}`, exactly as
they were on DynamoDB.

| Endpoint | Resource |
|---|---|
| `GET/POST /api/v1/recipes` | RecipeCollectionApi |
| `GET/PUT/DELETE /api/v1/recipe/<recipe_id>` | RecipeApi |
| `GET /api/v1/replacements/<scope>` | ReplacementCollectionApi (`all`, `ingredients`, `directions`) |
| `PUT/DELETE /api/v1/replacements/<scope>/<old_value>` | ReplacementCollectionApi |
| `GET /api/v1/readme` | ReadmeApi |

v1 quirks kept on purpose, for identical responses:
- POST returns ISO date strings; every other recipe response returns epoch milliseconds (floats).
- Request bodies are parsed with `get_json(force=True)`: the UI sends JSON without a `Content-Type`.
- PUT replaces the whole recipe: omitted fields reset to defaults. Steps whose `step_id` matches
  an existing step keep their id; the rest get new ids.
- `GET /api/v1/replacements/<scope>/<old_value>` returns 500 (the handler takes no `old_value`).

Changes from the DynamoDB version: the server assigns recipe and step ids (it ignores the UI's
client-generated `id` on POST), PUT to an unknown id returns 404 instead of creating the recipe,
and GET requests never write.

## Config & Environment
`backend/config.py` + `backend/global_logger.py`. The `local` boolean is `True` when
`APP_ENV=local` is set in the environment; locally, `Config` loads `.env`.

Set `APP_ENV=local` in `.env` for local development (already present). Do NOT set it
in `env_variables.yaml` — GCP must not see this value.

Key values:
- `APP_ENV` — `local` for local dev; absent/unset for GCP
- `DATABASE_URL` — Neon pooled connection string (locally the `dev` branch)
- `DATABASE_URL_UNPOOLED` — Neon direct connection string, for Alembic
- `BOUND_PORT` — local port (set in `.flaskenv`)
- `DOMAIN_URL` — `breadsheet.com`

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
- `env_variables.yaml` (git-ignored) holds production config, including the production branch's
  pooled `DATABASE_URL` (added at the M1 cutover).

## Deploys
No maintenance windows or maintenance mode.
1. Run new Alembic migrations against production first (`DATABASE_URL_UNPOOLED` for the
   `production` branch, set only for that command, never saved in `.env`). They must be
   expand-then-contract (see Migrations).
2. `./deploy.sh [version]` deploys with `--no-promote`, so the new version gets no traffic.
3. Smoke-test it at `https://<version>-dot-breadsheet.wl.r.appspot.com`.
4. Move traffic: `gcloud app services set-traffic default --splits <version>=1`.
5. Roll back by moving traffic to the previous version. Keep the last few versions deployed;
   delete older ones to stay within App Engine's version limit.

## Testing
```bash
docker compose up -d breadsheet-db   # local Postgres 18 on port 5433 (data in tmpfs)
.venv/bin/python -m pytest
```
- Co-located `*_test.py` files alongside each module in `backend/`; `conftest.py` at root.
- The `database` fixture rebuilds the test schema from the Alembic migrations (downgrade to base,
  then upgrade), so tests cover the migrations too. The `client` fixture truncates every table.
- Tests that need the database skip when the container isn't running. Tests never touch Neon,
  except the live round trip in `database_test.py`. Override the target with `TEST_DATABASE_URL`.

## Coding Conventions
- `local` bool controls local vs. cloud behavior throughout the codebase
- Datetimes stored as UTC; v1 `to_dict()` returns ISO strings by default, or epoch ms
  with `dates_as_epoch=True`
- Ids are UUIDv7, assigned by the server; never accept client-supplied ids
- CORS enabled for all `/api/*` routes

## Current Status
- Backend stable and deployed to GCP; React (breadsheet-ui) is the only frontend
- Runtime and dependencies upgraded to current stable (Python 3.14, Nov 2026)
- Second Rise item 3 done in code: v1 runs on Postgres via SQLAlchemy + Alembic. Production
  still serves the DynamoDB version until the M1 cutover (items 4 to 6: migrate data, curate
  defaults, verify, then deploy)

## Second Rise spec
The source of truth is `./docs/second-rise.md`, in this repo. Read it before planning or executing any Second Rise work. If it needs changes, say so and stop.
