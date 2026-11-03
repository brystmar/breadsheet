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
| Database | DynamoDB (AWS) — Postgres migration planned, see below |
| ORM | PynamoDB 6.1 |
| Frontend | React (breadsheet-ui repo) |
| Cloud | Google App Engine standard (GCP) |
| Local | Docker Compose (DynamoDB Local) |
| Tests | pytest + moto (co-located *_test.py files in backend/) |
| IDE | PyCharm Professional |

> **Important:** Today this project uses DynamoDB + PynamoDB. There is no SQLAlchemy and
> no Alembic yet. A move to Postgres (Neon) with SQLAlchemy + Alembic is planned as part of
> Second Rise (see `./docs/second-rise-feature.md`). Until that task begins, keep
> new code on PynamoDB and don't add Postgres patterns.

### Neon Postgres (set up, not yet used by the API)
- Neon project `winter-sky-40837772` (`breadsheet`), region `aws-us-west-2`, Postgres 18.
  Branches: `production` (default) and `dev` (local development).
- The repo is linked via the git-ignored `.neon` file; `neon checkout <branch>` switches
  branches and pulls that branch's `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED` into `.env`.
- `backend/database.py` `get_connection()` opens a psycopg connection from `Config.DATABASE_URL`.
- The pooled URL goes through PgBouncer in transaction mode, so session state (temp tables,
  `SET`, advisory locks) can leak between requests. Keep it inside a single transaction.
  Use `DATABASE_URL_UNPOOLED` for migrations.
- `backend/database_test.py` runs a live round trip against the branch in `.env`; it is
  skipped when `DATABASE_URL` is unset.

## Dependency Versions
Pinned in `requirements.txt` (last upgraded Nov 2026):

| Package | Version |
|---|---|
| Flask | 3.1.3 |
| Flask-RESTful | 0.3.10 (unmaintained since 2023; candidate for removal with `/api/v2`) |
| Flask-Cors | 6.0.5 |
| pynamodb | 6.1.0 |
| boto3 | 1.43.123 |
| python-dotenv | 1.2.4 |
| shortuuid | 1.0.13 |
| Markdown | 3.11.2 |
| psycopg[binary] | 3.3.6 |
| pytest | 9.2.0 |
| moto[dynamodb] | 5.2.5 |
| testfixtures | 12.4.0 |

## Repo Structure
```
breadsheet/
├── main.py                  # Entrypoint: app init, routes, GCP redirect handler
├── requirements.txt
├── app.yaml                 # GCP App Engine config
├── docker-compose.yaml
├── conftest.py              # Pytest fixtures
├── backend/
│   ├── __init__.py          # create_app() factory
│   ├── config.py            # Config: AWS region, ports, domain, env detection
│   ├── global_logger.py     # Logger + `local` bool (True when APP_ENV=local)
│   ├── functions.py         # Utilities incl. generate_new_id()
│   ├── model_attributes.py  # Shared DynamoDB attribute definitions
│   ├── models.py            # PynamoDB models: Recipe, Step (MapAttribute), Replacement
│   ├── recipe_routes.py     # RecipeCollectionApi, RecipeApi
│   ├── replacement_routes.py
│   ├── meta_routes.py       # ReadmeApi
│   └── *_test.py            # Co-located test files for each module
├── data/                    # Data fixtures / seed files
├── templates/               # Static App Engine error pages only (referenced in app.yaml)
└── etc/                     # Miscellaneous config/scripts
```

## Data Models (`backend/models.py`)

### `Recipe` (PynamoDB Model, DynamoDB table: `Recipe`)
Hash key: `id` (auto-generated short UUID)

| Attribute | Type | Notes |
|---|---|---|
| `id` | UnicodeAttribute | Hash key, auto-generated |
| `name` | UnicodeAttribute | Recipe title |
| `author` | UnicodeAttribute | Optional |
| `source` | UnicodeAttribute | Optional |
| `url` | UnicodeAttribute | Optional |
| `difficulty` | UnicodeAttribute | Beginner / Intermediate / Advanced / Expert |
| `solve_for_start` | BooleanAttribute | Controls UI timing direction |
| `length` | NumberAttribute | Total duration in **seconds** |
| `steps` | ListAttribute(of=Step) | Ordered list of Step objects |
| `date_added` | UTCDateTimeAttribute | UTC |
| `start_time` | UTCDateTimeAttribute | UTC |
| `last_modified` | UTCDateTimeAttribute | UTC |

### `Step` (PynamoDB MapAttribute — nested inside Recipe.steps)
| Attribute | Type | Notes |
|---|---|---|
| `step_id` | UnicodeAttribute | Auto-generated short UUID |
| `number` | NumberAttribute | Step order |
| `text` | UnicodeAttribute | Step directions |
| `then_wait` | NumberAttribute | Duration in **seconds** |
| `note` | UnicodeAttribute | Optional longer notes |

### `Replacement` (PynamoDB Model, table: `Replacement`)
Composite key: `scope` (hash) + `old` (range). Stores ingredient substitution text.

| Attribute | Type |
|---|---|
| `scope` | UnicodeAttribute (hash key) |
| `old` | UnicodeAttribute (range key) |
| `new` | UnicodeAttribute |

## API Endpoints
All routes use `/api/v1/` prefix.

| Endpoint | Resource |
|---|---|
| `GET/POST /api/v1/recipes` | RecipeCollectionApi |
| `GET/PUT/DELETE /api/v1/recipe/<recipe_id>` | RecipeApi |
| `GET /api/v1/replacements/<scope>` | ReplacementCollectionApi |
| `GET /api/v1/replacements/<scope>/<old_value>` | ReplacementCollectionApi |
| `GET /api/v1/readme` | ReadmeApi |

## Config & Environment
`backend/config.py` + `backend/global_logger.py`. The `local` boolean is `True` when
`APP_ENV=local` is set in the environment. Used throughout to switch between local
DynamoDB (`localhost:8008`) and AWS.

Set `APP_ENV=local` in `.env` for local development (already present). Do NOT set it
in `env_variables.yaml` — GCP must not see this value.

Key values:
- `APP_ENV` — `local` for local dev; absent/unset for GCP
- `AWS_REGION` — DynamoDB region
- `BOUND_PORT` — local port (set in `.flaskenv`)
- `DOMAIN_URL` — `breadsheet.com`

## Running Locally
```bash
# Requires local DynamoDB instance on port 8008 (docker compose up breadsheet-db)
.venv/bin/python main.py
```
The `.venv` is built on Python 3.14 to match App Engine.

## GCP Notes
- `app.yaml` sets `runtime: python314` (newest App Engine standard Python runtime;
  end of support 2030-10-10). App Engine applies patch releases automatically.
- Deploy with `./deploy.sh` (`gcloud app deploy`)
- Legacy `breadsheet.appspot.com` requests 301-redirected to `breadsheet.com`
  in `handle_before_request()` in `main.py`

## Testing
```bash
pytest
```
Co-located `*_test.py` files alongside each module in `backend/`.
`conftest.py` at root provides shared fixtures.

## Coding Conventions
- `local` bool controls local vs. cloud behavior throughout the codebase
- Datetimes stored as UTC; `to_dict()` exports as millisecond epoch by default
- `generate_new_id(short=True)` produces short UUIDs for DynamoDB keys
- CORS enabled for all `/api/*` routes

## Current Status
- Backend stable and deployed to GCP; React (breadsheet-ui) is the only frontend
- Runtime and dependencies upgraded to current stable (Python 3.14, Nov 2026)
- Next up: Second Rise (`./docs/second-rise-feature.md`): Postgres on Neon
  via SQLAlchemy + Alembic, no-login identity, bakes, `/api/v2`, Home Assistant integration

## Second Rise spec
The source of truth is `./docs/second-rise-feature.md`, in this repo. Read it before planning or executing any Second Rise work. If it needs changes, say so and stop.
