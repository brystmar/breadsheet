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
Dependabot (`.github/dependabot.yml`) opens monthly grouped pip and GitHub Actions updates, waiting 7
days after a release (security fixes come right away). When merging one, update this table too.

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
| tzdata | 2026.6 (IANA zones for bakes, so they don't depend on the host's zoneinfo) |
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
│   ├── admin_recipes.py     # Export, create, update and archive default recipes with the admin key (breadsheet#28)
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
│   ├── recipe_routes_v2.py  # /api/v2/recipes: scopes, copy, lookups (breadsheet#29), publishing (breadsheet#58),
│   │                        #   detail levels, the Then Wait, drafts (breadsheet#30), categories, prerequisites (breadsheet#59)
│   ├── bake_routes.py       # /api/v2/bakes: start, read, change, cancel, check off (breadsheet#31)
│   ├── admin_routes.py      # /api/v2/admin/recipes: the admin key, create, edit and archive defaults, unpublish (breadsheet#28)
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
| `published_at` | timestamptz | Set while the recipe is in the community library; personal recipes only (check constraint) |
| `detail_level` | text | `simple` (default) or `detailed`; only changes which step fields the UI shows (breadsheet#30) |
| `is_draft` | boolean | Owner-only, can be saved incomplete, can't be published or baked. Checks: personal only, never published |
| `category` | text | `bread` (default) or `prep` (breadsheet#59). Validated by the API, not the database, so a new category needs no migration |
| `archived_at` | timestamptz | Set when the admin retires a default: hidden from every list (v1, v2, community), still opens by id or URL |

`length` (total seconds) is a computed property, the sum of the steps' `default_wait`; `length_max` uses
each step's `wait_max` instead. Neither is stored.

### `RecipeStep` (table `recipe_steps`)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid | v1's `step_id` |
| `recipe_id` | uuid | FK to `recipes`, cascade delete |
| `position` | integer | Step order from 1; v1's `number` |
| `text` | text | Step directions |
| `note` | text | Optional |
| `then_wait` | integer | The Then Wait, in seconds: the timing a bake runs on; v1's `then_wait`. Null only for a detailed step with a range and no Then Wait. Check: `≥ 0` |
| `wait_min`, `wait_max` | integer | The range around the Then Wait. Simple steps have `wait_min = wait_max = then_wait`. Check: `0 ≤ wait_min ≤ wait_max`. A Then Wait outside its range is allowed and flagged |
| `active_seconds` | integer | Hands-on time from the step's start; null = unknown (10 min, estimated). Check: `≥ 0` |
| `needs_presence` | boolean | Must be home, not just awake; null = unknown (treated as needed) |

`default_wait` (computed) is where a bake starts a step: `then_wait`, or the middle of the range rounded
to the nearest minute. `hands_on()` applies the "unknown is not zero" defaults; `warnings` lists
`then_wait_outside_range` and `hands_on_longer_than_wait`. Steps written by `m2h` have a null `then_wait`
with `wait_min = wait_max`, so their default wait is unchanged.

### `RecipePrerequisite` (table `recipe_prerequisites`, breadsheet#59)
| Column | Type | Notes |
|---|---|---|
| `recipe_id` | uuid | FK to `recipes`, cascade delete; part of the primary key |
| `prerequisite_recipe_id` | uuid | FK to `recipes`, cascade delete; part of the primary key. Check: not the recipe itself |
| `position` | integer | Order from 1. Prerequisites are alternatives: any one gets you ready |

The API enforces the rest: every prerequisite is a non-draft `prep` recipe the editor can see, `prep`
recipes have none of their own, and a default lists only defaults. A prep recipe that becomes `bread`
stops being anyone's prerequisite. Responses leave out prerequisites the viewer can't see (someone
else's draft). Migration `0006` made "Revive a Refrigerated Sourdough Starter" `prep` and the
prerequisite of the two sourdough defaults.

### `Replacement` (table `replacements`)
Convert-text substitutions. Unique on (`scope`, `old`). `old` uses `COLLATE "C"` (byte order),
which matches DynamoDB's range-key sort; convert-text applies replacements in this order, so
don't change it.

### `Bake` (table `bakes`, breadsheet#31)
A recipe being baked: a snapshot of its steps, scheduled from a `start` or `finish` anchor.
| Column | Type | Notes |
|---|---|---|
| `public_suffix` | text | `/bakes/<suffix>`, unique; owner only |
| `user_id` | uuid | FK to `users` (restrict) |
| `recipe_id` | uuid | FK to `recipes`, set null when the recipe is deleted; the bake runs from its snapshot |
| `name_snapshot` | text | The recipe's name at start |
| `anchor_type`, `anchor_time` | text, timestamptz | `start`: step 1 at the anchor. `finish`: the last step's wait ends at it |
| `time_zone` | text | IANA zone from the browser; responses give times in UTC and in this zone |
| `alert_mode` | text | `simple` (default) or `fancy` (refused with `fancy_requires_ha` until M3) |
| `status` | text | `not_started` → `in_progress` (a step checked off, or started partway through; a mid-bake skip alone doesn't start a bake) → `completed` |
| `outcome` | text | Set when completed: `finished` (every step done, or the owner completed it), `canceled` (one L), or `expired` (an hour past `projected_end`). Check: set exactly when completed |
| `created_via` | text | `web`, `ha` or `agent`; `web` until M3 |
| `idempotency_key` | text | From the `Idempotency-Key` header; unique per user |
| `started_at`, `completed_at`, `projected_end` | timestamptz | `projected_end` is the last step's time plus its wait |

`Bake.project()` recomputes the schedule: each step's time is the previous step's completion (or its
scheduled time) plus that step's `wait_chosen`; the anchor applies to the first step that isn't skipped. Skipped
steps get no time and their waits don't count.
`Bake.refresh_status()` moves the status along and expires a bake an hour (`BAKE_GRACE`) past its
projected end; every read calls it and saves the change (no scheduled job).

### `BakeStep` (table `bake_steps`)
| Column | Type | Notes |
|---|---|---|
| `bake_id`, `position` | uuid, integer | Unique together; cascade delete with the bake |
| `text_snapshot`, `note_snapshot` | text | The step's text and note at start |
| `wait_min`, `wait_max`, `wait_chosen` | integer | The range at start and the wait this bake uses (default: the step's `default_wait`). Outside the range is flagged, not refused |
| `active_seconds`, `needs_presence` | integer, boolean | Snapshotted detail; responses add `hands_on` with the "unknown is not zero" defaults |
| `skipped` | boolean | Steps before `start_at_step`, or skipped mid-bake: no time, no alerts, count as done |
| `skipped_at` | timestamptz | Client-supplied time of a mid-bake skip (breadsheet#78); null for steps skipped at start |
| `scheduled_at`, `completed_at` | timestamptz | `scheduled_at` is null for skipped steps. `completed_at` is the client-supplied check-off time; the first write wins |

### `User` (table `users`, M2)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid | UUIDv7 |
| `username` | text | Display case kept; unique on `lower(username)` |
| `key_hash` | bytea(32) | SHA-256 of the user's key, unique; the key itself is never stored |
| `created_at`, `last_seen_at` | timestamptz | `last_seen_at` is written at most once a day |

### `Event` (table `events`, M2, breadsheet#34)
| Column | Type | Notes |
|---|---|---|
| `type` | text | See `backend/events.py`: signup and sign-in, recipe create/copy/publish/unpublish/delete, bake start/complete/cancel, step check-off and skip, and browser-only `ics_exported` |
| `occurred_at` | timestamptz | Indexed with `type` |
| `user_id` | uuid | FK to `users`, `ON DELETE SET NULL` |
| `recipe_id`, `bake_id` | uuid | Plain ids, not foreign keys, so events outlive deleted recipes and bakes. A copy records the recipe that was copied |
| `value` | integer | `step_completed`: seconds after the step's scheduled time (negative when early), measured before re-projection |
| `client`, `agent_name` | text | `web`, `ha`, or `agent` (from `X-Breadsheet-Via: agent`); the agent's self-reported name, cleaned to a 40-character label |

Routes record events with `events.record()` inside their own transaction, only when something changed (a
first-write-wins repeat records nothing). No IP addresses, user agents, or free text.

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
| `GET /api/v2/recipes?q=&category=` | Defaults plus the caller's own recipes, as summaries (no steps); archived ones left out; unknown category → 400 `category_invalid` |
| `POST /api/v2/recipes` | Create a personal recipe (signed in) |
| `GET /api/v2/recipes/<id>` | One recipe with steps: defaults for anyone, personal for anyone with the link, drafts for the owner only (others get 404) |
| `PUT`/`DELETE /api/v2/recipes/<id>` | Owner only; defaults → 403 `default_read_only`, others → 403 `not_owner`. `is_draft: false` runs full validation; a published recipe can't become a draft (409 `recipe_published`) |
| `POST /api/v2/recipes/<id>/copy` | "Make it mine": an independent personal copy (signed in) |
| `GET /api/v2/recipes/by-slug/<slug>` | Resolve a default's URL, `/recipes/<slug>` |
| `GET /api/v2/recipes/by-suffix/<suffix>` | Resolve a personal URL, `/recipes/<slug>-<suffix>`, with the current slug |
| `POST /api/v2/recipes/<id>/publish` | Publish to the community library (owner only; must pass validation; drafts → 409 `recipe_is_draft`); republishing keeps the original time |
| `DELETE /api/v2/recipes/<id>/publish` | Unpublish (owner only); 204 even if it wasn't published |
| `GET /api/v2/community/recipes?q=&category=` | Published recipes for everyone, newest first, as summaries; the newest 200; archived ones left out |
| `POST /api/v2/admin/recipes` | Create a default recipe (admin key); its slug is unique among defaults |
| `PUT /api/v2/admin/recipes/<id>` | Edit a default (admin key); the slug never changes, personal recipes → 404 |
| `DELETE /api/v2/admin/recipes/<id>` | Archive a default (admin key); 204, and archiving again keeps the time. No unarchive endpoint |
| `DELETE /api/v2/admin/recipes/<id>/publish` | Unpublish anyone's recipe (admin key) |
| `POST /api/v2/bakes` | Start a bake: `recipe_id`, `anchor_type`, `anchor_time` (ISO 8601 with offset), `time_zone`, optional `alert_mode`, `waits` ([{position, wait_chosen}]) and `start_at_step` (start partway through; earlier steps are skipped). Honors `Idempotency-Key` (a repeat returns the original, 200) |
| `GET /api/v2/bakes?status=active\|completed` | The caller's active bakes (default) or newest 50 completed, with schedules |
| `GET /api/v2/bakes/<id>`, `/bakes/by-suffix/<suffix>` | One bake (owner only; others get 404) |
| `PATCH /api/v2/bakes/<id>` | Change waits or alert mode; the anchor only before the first check-off (409 `bake_in_progress`) |
| `POST /api/v2/bakes/<id>/complete` | Finish it: remaining steps are checked off at `completed_at` (default now); outcome `finished`. Repeating changes nothing |
| `POST /api/v2/bakes/<id>/cancel` | End it without finishing; unchecked steps stay unchecked; outcome `canceled`. Repeating changes nothing |
| `POST /api/v2/bakes/<id>/steps/<position>/complete` | Check off with `completed_at`: not over five minutes ahead or before the bake started (400 `completed_at_invalid`); first write wins; re-projects later steps |
| `POST /api/v2/bakes/<id>/steps/<position>/skip` | Skip a step that isn't done, with `skipped_at` (same rules; 400 `skipped_at_invalid`); first write wins; its wait drops out and later steps re-project; skipping the last steps left finishes the bake |
| `POST /api/v2/events` | Record a browser-only event from the allow-list (`ics_exported` with one of the caller's `bake_id`s); 204. Other types → 400 `event_type_invalid` |

Bake errors: drafts → 409 `recipe_is_draft`; no steps → 400 `recipe_has_no_steps`; a 4th active bake →
409 `bake_limit_reached`; a wait outside 0–30 days → 400 `wait_out_of_range`; a schedule already over →
400 `bake_already_over`; new input on a completed bake → 409 `bake_completed`; other bad fields → 400
`bake_invalid` with `fields`. Writes lock the bake row (`SELECT … FOR UPDATE`).

v2 conventions (`backend/api_v2.py`):
- Errors are `{code, message}` with a stable `code` and a message that says what to do next; raise
  `ApiError(status, code, message)`. Unknown paths and wrong methods under `/api/v2` also return JSON.
  Validation errors can add `fields`, mapping each bad field to its message (e.g. `steps[0].text`).
- Recipes are returned as `{recipe: …}` or `{recipes: […]}`, with `id`, `slug`, `path`, `scope`, `owner`,
  `is_mine`, `source_recipe_id`, `published_at`, `detail_level`, `is_draft`, `category`, `prerequisite_ids`,
  `archived_at`, the descriptive fields,
  `length_seconds`, `length_max_seconds`, timestamps, `prerequisites` (full recipes only: `id`, `name`, `path`, `category`), and steps (`id`, `position`, `text`, `note`, `then_wait`,
  `wait_min`, `wait_max`, `default_wait`, `active_seconds`, `needs_presence`, `warnings`). v1's `solve_for_start`/`start_time` aren't in v2.
  `scope` is `default` or `personal`; a published recipe is still `personal` (same owner, URL and edit
  rights) with `published_at` set.
- Recipe bodies (create, update, admin) take the same fields. A step sends `then_wait` alone (simple), a range
  around it, or a range alone; missing fields mean simple, not a draft, and unknown. A draft skips only the
  must-be-filled-in checks (name, step text). Admin bodies can't be drafts. `category` and `prerequisites`
  (an ordered list of up to 10 recipe ids) are optional; copies keep both.
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
admin request is refused. The key also unpublishes any community recipe; archiving defaults comes with
breadsheet#59. Day to day, use the script (the key comes from the password manager, set for that one
command; `BREADSHEET_API` defaults to production):

```bash
ADMIN_KEY=... python etc/admin_recipes.py export <slug-or-id> > recipe.json   # no key needed
ADMIN_KEY=... python etc/admin_recipes.py update recipe.json
ADMIN_KEY=... python etc/admin_recipes.py archive <slug-or-id>   # hide a default from every list
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
- `migrations_test.py` fails if the models and the migrated schema differ: add a migration.
- CI (`.github/workflows/tests.yml`) runs pytest against a throwaway `postgres:18.6` service on every
  PR and push to `main`, with `REQUIRE_TEST_DATABASE=1` so an unreachable database fails the run
  instead of skipping every test. No secrets, no Neon.

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
- Community recipes (breadsheet#58) live since 2026-11-05; the UI for them doesn't exist yet
- Recipe detail levels, the Then Wait, and drafts (breadsheet#30) live since 2026-11-05; no UI yet
  (breadsheet-ui#31)
- Recipe categories, prerequisites and archiving (breadsheet#59) live since 2026-11-06; the starter recipe
  is `prep` and the prerequisite of the two sourdough defaults
- Bakes (breadsheet#31) live since 2026-11-06: start (optionally partway through), check-off, complete,
  cancel, expiry an hour past the projected end; no bake UI yet (breadsheet-ui#33). Doubled-slash URLs
  return 404 (breadsheet#77)
- Skipping a step mid-bake (breadsheet#78) live since 2026-11-07; production Postgres is at migration `0008`
- Product events and metrics (breadsheet#34) built; migration `0009` adds `events`. `flask --app main metrics`
  prints the spec's usage metrics, read-only (point `DATABASE_URL` at production for one command to read it)
- App Engine version `m2l` serves all traffic; `m2k` is the rollback target (it has no skip endpoint and
  ignores `skipped_at`, so a mid-bake skip would read as a skip from the start until traffic moves back).
  `py314` (the DynamoDB version) is kept until DynamoDB is retired

## Second Rise spec
The source of truth is `./docs/second-rise.md`, in this repo. Read it before planning or executing any Second Rise work. If it needs changes, say so and stop.

The backlog is GitHub issues across breadsheet, breadsheet-ui, and breadsheet-hass; the spec's
backlog table links each one. Refer to work by issue (`breadsheet#26`), always with its title,
never by the old spec item numbers. Each repo has milestones M1–M4 with matching labels; the
`parked` and `decision` labels mark the rest.
