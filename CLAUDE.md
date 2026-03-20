# breadsheet — Claude Context

## Project Purpose
A recipe scheduling tool that calculates start/finish times for each step of a baking
recipe. Particularly designed for sourdough, which has many time-sensitive steps spread
across multiple days. Given a target finish time, it works backwards to produce a full
schedule. Lives at breadsheet.com.

## Companion Repos
- **This repo** (`brystmar/breadsheet`): Python/Flask backend
- **Frontend** (`brystmar/breadsheet-ui`): React UI (early-stage, planned migration)

## Stack
| Layer | Technology |
|---|---|
| Language | Python |
| Framework | Flask + Flask-RESTful |
| Database | DynamoDB (AWS) — **not Postgres** |
| ORM | PynamoDB |
| Current UI | WTForms + Jinja2 templates + Bootstrap (server-rendered) |
| Planned UI | React (breadsheet-ui repo, in progress) |
| Styling | SASS |
| Cloud | Google App Engine (GCP) |
| Local | Docker Compose |
| Tests | pytest (co-located *_test.py files in backend/) |
| IDE | PyCharm Professional |

> **Important:** This project uses DynamoDB + PynamoDB, not SQLAlchemy + Postgres.
> There are no Alembic migrations. Do not suggest Postgres patterns here.

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
│   ├── global_logger.py     # Logger + `local` bool (True when running in PyCharm)
│   ├── functions.py         # Utilities incl. generate_new_id()
│   ├── model_attributes.py  # Shared DynamoDB attribute definitions
│   ├── models.py            # PynamoDB models: Recipe, Step (MapAttribute), Replacement
│   ├── recipe_routes.py     # RecipeCollectionApi, RecipeApi
│   ├── replacement_routes.py
│   ├── meta_routes.py       # ReadmeApi
│   └── *_test.py            # Co-located test files for each module
├── data/                    # Data fixtures / seed files
├── templates/               # Jinja2 HTML templates (current server-rendered UI)
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
running inside PyCharm (path detection). Used throughout to switch between local
DynamoDB (`localhost:8008`) and AWS.

Key values:
- `AWS_REGION` — DynamoDB region
- `BOUND_PORT` — local port (set in `.flaskenv`)
- `DOMAIN_URL` — `breadsheet.com`

## Running Locally
```bash
# Requires local DynamoDB instance on port 8008
python main.py
```

## GCP Notes
- `app.yaml` configures App Engine runtime
- Legacy `breadsheet.appspot.com` requests 301-redirected to `breadsheet.com`
  in `handle_before_request()` in `main.py`
- `googleclouddebugger` imported with graceful `ImportError` fallback for local dev

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
- Backend stable and deployed to GCP
- Current UI is functional Jinja2/WTForms (server-rendered)
- React frontend migration planned — breadsheet-ui repo exists with detailed style
  guide, component development in early stages
- Less actively developed than greeting-cards at present
