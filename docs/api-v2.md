# breadsheet API v2

The frozen contract for `/api/v2` on `api.breadsheet.com`, as shipped in M2 ([breadsheet#32](https://github.com/brystmar/breadsheet/issues/32)). The [Second Rise spec](second-rise.md) explains why things work this way; this page is what clients can rely on.

`backend/contract_test.py` holds the code to this page: every route, every error code, and every object's fields must match what's written here.

## Stability

The contract only grows. Later milestones may add:

- new endpoints
- new optional request fields, and new query parameters
- new fields in responses
- new error codes, and new values in fields documented as open lists

Nothing that has shipped is renamed, removed, or changes meaning. Clients must ignore response fields they don't know. What Home Assistant needs (M3) and what agent tools need (M4) are added here before each ships.

## Conventions

- **Base URL.** `https://api.breadsheet.com/api/v2`. Every path below includes the `/api/v2` prefix.
- **Ids.** Paths use internal ids (UUIDs). Slugs and suffixes exist only for user-facing URLs, so the only paths that take them are the two recipe lookups and the bake lookup.
- **Times.** Requests send ISO 8601 with a UTC offset (`2026-11-14T10:00:00-08:00` or `…Z`). Responses send ISO 8601 in UTC; `*_local` fields repeat a time in the bake's own time zone. Durations are whole seconds.
- **Bodies.** Requests and responses are JSON objects. State-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) must send `Content-Type: application/json`, even with no body (send `{}`); this forces a CORS preflight, which is the CSRF protection. Bodies over 1 MB are refused.
- **Caching.** Every response has `Cache-Control: no-store`.
- **Authentication.**
  - *Session:* browsers send the `breadsheet_session` cookie, set by signing up or signing in (credentialed CORS from `breadsheet.com` origins only).
  - *Admin* (breadsheet#86): a session for a user with `is_admin`, or the admin key (`Authorization: Bearer <admin key>`) for scripts. Admin endpoints say **Auth:** admin. A signed-in non-admin gets 403 `admin_required`; a device token gets 403 `scope_missing`, even an admin's own; a wrong key gets 401 `admin_key_invalid`.
  - *None:* readable by anyone; a session, if present, adds the caller's own recipes and `is_mine`.
  - *Device token* (M3, breadsheet#27): Home Assistant sends `Authorization: Bearer <device token>`, from pairing. A token acts as its user and carries scopes (`recipes:read`, `recipes:write`, `bakes:read`, `bakes:write`; pairing grants all four). Each endpoint's **Auth** names the scope a token needs; endpoints whose Auth is a session alone are browser-only, and a token there gets 403 `scope_missing`. A revoked or unknown token gets 401 `token_invalid`. A token wins over any session cookie.
- **Agent attribution.** Calls made for an agent send `X-Breadsheet-Via: agent`, plus `X-Breadsheet-Agent: <name>` when known. Used only for metrics.
- **Idempotency.** `POST /api/v2/bakes` honors `Idempotency-Key` (1 to 200 characters, unique per user): a repeat returns the original bake with 200 instead of 201.
- **Check-offs and skips.** The client sends the moment it happened (`completed_at`, `skipped_at`): no more than five minutes in the future, and not before the bake started. Repeating one, or acting on a step that's already done, returns the bake unchanged: the first write wins. So clients can queue taps while offline and retry them with backoff, and a late retry lands exactly as an on-time one would have.
- **Rate limits.** Sign-up (5 an hour), username checks (60 a minute), failed sign-ins (10 per 15 minutes), and failed admin keys (10 per 15 minutes) are limited per network. Over the limit: 429 `rate_limited` with `Retry-After` (seconds).
- **Outages.** If breadsheet can't reach its database: 503 `service_unavailable` with `Retry-After` (seconds). Clients keep using what they last fetched and retry after that long. Anything unexpected is 500 `internal_error`. Responses from App Engine itself (before breadsheet runs) may not be JSON; treat any 5xx or network failure as worth retrying.

## Errors

Every error is JSON with a stable `code` and a plain-language `message` that says what to do next. Form-style errors add `fields`, which maps request fields (such as `name` or `steps[2].text`) to what's wrong with each.

| Field | Type | Notes |
| --- | --- | --- |
| `code` | string | Stable; listed under Error codes |
| `message` | string | For people; wording may change |
| `fields` | object | Optional; field path → message |

### Error codes

| Code | Status | When |
| --- | --- | --- |
| `admin_key_invalid` | 401 | Missing or wrong admin key |
| `admin_required` | 403 | Signed in, but not an admin |
| `bake_already_over` | 400 | The schedule would already be over |
| `bake_completed` | 409 | The bake has ended, so it can't change |
| `bake_id_invalid` | 400 | An event needs a `bake_id` |
| `bake_in_progress` | 409 | A bake's anchor can't change after a check-off |
| `bake_invalid` | 400 | Bad bake fields; see `fields` |
| `bake_limit_reached` | 409 | Already three active bakes |
| `body_invalid` | 400 | The body isn't a JSON object, or has nothing to change |
| `body_too_large` | 413 | The body is over 1 MB |
| `category_invalid` | 400 | Unknown `category` filter |
| `completed_at_invalid` | 400 | `completed_at` is missing, malformed, in the future, or before the bake started |
| `default_read_only` | 403 | Default recipes can't be changed by users |
| `event_type_invalid` | 400 | The event type isn't on the allow-list |
| `fancy_requires_ha` | 409 | Fancy alerts need Home Assistant (M3) |
| `http_error` | varies | Any other HTTP error |
| `idempotency_key_invalid` | 400 | `Idempotency-Key` is empty or too long |
| `internal_error` | 500 | Something unexpected went wrong |
| `json_required` | 415 | A state-changing request without `Content-Type: application/json` |
| `key_invalid` | 401 | No account has that key |
| `method_not_allowed` | 405 | The path doesn't take that method; see `Allow` |
| `not_found` | 404 | No such path, recipe, bake, or step (or not visible to the caller) |
| `not_owner` | 403 | Only the recipe's owner can change it |
| `own_key_reset` | 403 | Admins can't reset their own key from the admin endpoints |
| `not_signed_in` | 401 | The request needs a session |
| `pairing_code_invalid` | 400 | The pairing code is wrong, expired, or already used |
| `rate_limited` | 429 | Too many attempts; see `Retry-After` |
| `recipe_has_no_steps` | 400 | A recipe needs steps to bake |
| `recipe_invalid` | 400 | Bad recipe fields; see `fields` |
| `recipe_is_draft` | 409 | Drafts can't be baked or published |
| `recipe_published` | 409 | A published recipe can't go back to draft |
| `scope_missing` | 403 | The device token lacks the scope, or the endpoint is browser-only |
| `service_unavailable` | 503 | The database is unreachable; see `Retry-After` |
| `skipped_at_invalid` | 400 | `skipped_at` is missing, malformed, in the future, or before the bake started |
| `status_invalid` | 400 | Unknown `status` filter |
| `token_invalid` | 401 | The device token is unknown or revoked |
| `username_invalid` | 400 | Usernames are 3 to 30 letters, digits, `_` or `-`, starting with a letter, not reserved, and not refused by the word filter |
| `username_taken` | 409 | Someone has that username, ignoring case and treating `-` and `_` as the same |
| `wait_out_of_range` | 400 | A wait isn't 0 seconds to 30 days |

## Objects

### `user`

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `username` | string | As typed; unique regardless of case |
| `created_at` | time | |
| `is_admin` | boolean | Admins see admin tools (M3, breadsheet#86) |

### `recipe summary`

What recipe lists return.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `slug` | string | From the name; a rename changes it |
| `path` | string | The user-facing URL: `/recipes/<slug>`, or `/recipes/<slug>-<suffix>` for personal recipes |
| `scope` | string | `default` or `personal` |
| `owner` | string or null | The owner's username; null for defaults |
| `is_mine` | boolean | The caller owns it |
| `source_recipe_id` | uuid or null | What it was copied from |
| `published_at` | time or null | Set while it's in the community library |
| `detail_level` | string | `simple` or `detailed` |
| `is_draft` | boolean | Drafts are visible to their owner only |
| `category` | string | `bread` or `prep` |
| `prerequisite_ids` | uuid[] | Prep recipes, any one of which gets you ready; in order |
| `archived_at` | time or null | Archived defaults leave every list but still open |
| `name` | string | |
| `author`, `source`, `url` | string or null | |
| `difficulty` | string | `Beginner`, `Intermediate`, `Advanced`, or `Expert` |
| `length_seconds` | integer | Total of the default waits |
| `length_max_seconds` | integer | Total of the longest waits |
| `step_count` | integer | |
| `created_at`, `updated_at` | time | |

### `recipe`

A `recipe summary` plus:

| Field | Type | Notes |
| --- | --- | --- |
| `prerequisites` | prerequisite[] | The prerequisites the caller can see, in order |
| `steps` | recipe step[] | In order |

### `prerequisite`

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `name` | string | |
| `path` | string | |
| `category` | string | Always `prep` |

### `recipe step`

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | Send it back on update to keep the step |
| `position` | integer | From 1 |
| `text` | string | |
| `note` | string or null | |
| `then_wait` | integer or null | The Then Wait; null when only a range is known |
| `wait_min`, `wait_max` | integer | The range; equal for a simple step |
| `default_wait` | integer | What a bake uses: the Then Wait, or the middle of the range |
| `active_seconds` | integer or null | Hands-on time; null is unknown, not zero |
| `needs_presence` | boolean or null | Null is unknown |
| `warnings` | string[] | Open list: `then_wait_outside_range`, `hands_on_longer_than_wait` |

### `bake`

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `suffix` | string | For the user-facing URL |
| `path` | string | `/bakes/<suffix>` |
| `name` | string | The recipe's name when the bake started |
| `recipe_id` | uuid or null | Null once the recipe is deleted |
| `recipe_path` | string or null | Null when the recipe is deleted or a draft |
| `recipe_deleted` | boolean | |
| `anchor_type` | string | `start` or `finish` |
| `anchor_time` | time | Applies to the first step that isn't skipped |
| `time_zone` | string | IANA, e.g. `America/Los_Angeles` |
| `alert_mode` | string | `simple` or `fancy` |
| `status` | string | `not_started`, `in_progress`, or `completed` |
| `outcome` | string or null | Once completed: `finished`, `canceled`, or `expired` |
| `created_via` | string | `web`, `ha`, or `agent` |
| `started_at`, `completed_at` | time, time or null | |
| `projected_end`, `projected_end_local` | time | |
| `steps` | bake step[] | In order |

A bake is `completed` once every step is checked off or skipped, its owner completes or cancels it, or an hour passes after its projected end (outcome `expired`).

### `bake step`

| Field | Type | Notes |
| --- | --- | --- |
| `position` | integer | From 1 |
| `text`, `note` | string, string or null | Snapshots from the recipe |
| `wait_min`, `wait_max` | integer | The range at start |
| `wait_chosen` | integer | The wait this bake uses |
| `wait_outside_range` | boolean | Allowed, but flagged |
| `active_seconds`, `needs_presence` | integer or null, boolean or null | Snapshots |
| `hands_on` | object | `seconds`, `estimated`, and `needs_presence`, with unknowns filled in (10 minutes, presence needed) and `estimated` true |
| `skipped` | boolean | Skipped at the start or mid-bake |
| `skipped_at`, `skipped_at_local` | time or null | When a mid-bake skip happened; null for steps skipped at the start |
| `scheduled_at`, `scheduled_at_local` | time or null | Null for skipped steps |
| `completed_at`, `completed_at_local` | time or null | When it was checked off |

Each step that isn't skipped is due when the step before it was checked off (or was due) plus that step's `wait_chosen`. Checking off or skipping a step re-projects every later step.

### `admin user`

A user as admins see them (M3, breadsheet#87): every `user` field, plus:

| Field | Type | Notes |
| --- | --- | --- |
| `last_seen_at` | time | Updated at most daily |
| `is_active` | boolean | Seen in the last 30 days |
| `is_test` | boolean | A `test-` user, made by the `test-users` command |
| `recipe_count`, `published_count` | integer | Personal recipes they own, and how many are published |
| `bake_count`, `active_bake_count` | integer | Every bake, and those not yet completed or expired |

### `connection`

A paired Home Assistant instance (M3).

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `label` | string | What HA called itself when pairing, or `Home Assistant` |
| `scopes` | string[] | Open list; pairing grants `recipes:read`, `recipes:write`, `bakes:read`, `bakes:write` |
| `created_at` | time | When it was paired |
| `last_used_at` | time or null | Updated at most daily |

## Endpoints

### `POST /api/v2/users`
Sign up and sign this browser in. **Auth:** none. **Body:** `{"username"}`. **201:** `{"user", "key"}`; the key is shown this once and never again. **Errors:** `username_invalid`, `username_taken`, `rate_limited`, `body_invalid`.

### `GET /api/v2/usernames/<username>`
Whether signup would accept this username right now: the same format, reserved-name, word-filter, and taken checks, one name at a time. **Auth:** none. **200:** `{"username", "available": true}`, or `{"username", "available": false, "code", "message"}` where `code` and `message` are what signup would return (`username_invalid` or `username_taken`). A name can still be taken between the check and signup. **Errors:** `rate_limited` (60 checks a minute per IP).

### `POST /api/v2/session`
Sign in with a key. **Auth:** none. **Body:** `{"key"}`. **200:** `{"user"}` and the session cookie. **Errors:** `key_invalid`, `rate_limited`, `body_invalid`.

### `GET /api/v2/session`
Who's signed in. **Auth:** session. **200:** `{"user"}`. **Errors:** `not_signed_in`.

### `DELETE /api/v2/session`
Sign out this browser only. **Auth:** none. **204.**

### `GET /api/v2/recipes`
Defaults, plus the caller's own recipes (drafts included); defaults first. Archived recipes are left out. **Auth:** none (a session or device token adds your own; a token needs `recipes:read`). **Query:** `q` (name contains, up to 100 characters), `category` (`bread` or `prep`). **200:** `{"recipes": [recipe summary]}`. **Errors:** `category_invalid`.

### `POST /api/v2/recipes`
Create a personal recipe. **Auth:** session, or device token with `recipes:write`. **Body:** a recipe body (below). **201:** `{"recipe"}`. **Errors:** `recipe_invalid`, `wait_out_of_range`, `not_signed_in`.

### `GET /api/v2/recipes/<recipe_id>`
One recipe. Defaults and personal recipes are readable by anyone with the id; drafts only by their owner. **Auth:** none (a device token needs `recipes:read`). **200:** `{"recipe"}`. **Errors:** `not_found`.

### `PUT /api/v2/recipes/<recipe_id>`
Replace one of your recipes. Renaming changes the slug; the suffix stays. Saving with `is_draft: false` takes a draft live. **Auth:** session or device token with `recipes:write`; owner. **Body:** a recipe body. **200:** `{"recipe"}`. **Errors:** `recipe_invalid`, `wait_out_of_range`, `recipe_published`, `default_read_only`, `not_owner`, `not_found`, `not_signed_in`.

### `DELETE /api/v2/recipes/<recipe_id>`
Delete one of your recipes. Copies and bakes from it keep working. **Auth:** session or device token with `recipes:write`; owner. **204.** **Errors:** `default_read_only`, `not_owner`, `not_found`, `not_signed_in`.

### `POST /api/v2/recipes/<recipe_id>/copy`
"Make it mine": copy any recipe you can see into a new personal recipe. **Auth:** session, or device token with `recipes:write`. **201:** `{"recipe"}`. **Errors:** `not_found`, `not_signed_in`.

### `POST /api/v2/recipes/<recipe_id>/publish`
Put one of your recipes in the community library. It must pass validation and not be a draft. Repeating changes nothing. **Auth:** session or device token with `recipes:write`; owner. **200:** `{"recipe"}`. **Errors:** `recipe_invalid`, `recipe_is_draft`, `default_read_only`, `not_owner`, `not_found`, `not_signed_in`.

### `DELETE /api/v2/recipes/<recipe_id>/publish`
Take one of your recipes out of the community library; copies are unaffected. **Auth:** session or device token with `recipes:write`; owner. **204.** **Errors:** `default_read_only`, `not_owner`, `not_found`, `not_signed_in`.

### `GET /api/v2/recipes/by-slug/<slug>`
Resolve a default recipe's URL. **Auth:** none (a device token needs `recipes:read`). **200:** `{"recipe"}`. **Errors:** `not_found`.

### `GET /api/v2/recipes/by-suffix/<suffix>`
Resolve a personal recipe's URL, for anyone with the link (drafts: owner only). The response's `path` is current, so a renamed recipe's old URL can redirect. **Auth:** none (a device token needs `recipes:read`). **200:** `{"recipe"}`. **Errors:** `not_found`.

### `GET /api/v2/community/recipes`
Published recipes, newest first, up to 200. **Auth:** none (a device token needs `recipes:read`). **Query:** `q`, `category`. **200:** `{"recipes": [recipe summary]}`. **Errors:** `category_invalid`.

**Recipe body** (create and update): `name` (required unless a draft, up to 200 characters), `author`, `source` (up to 200), `url` (http or https, up to 2000), `difficulty`, `detail_level`, `is_draft`, `category`, `prerequisites` (recipe ids: prep recipes you can see, up to 10, only on bread recipes), and `steps` (up to 100), each with `id` (to keep an existing step), `text` (required unless a draft, up to 1000), `note` (up to 5000), `then_wait`, `wait_min`, `wait_max` (seconds, 0 to 30 days; min ≤ max), `active_seconds`, and `needs_presence`. Missing fields mean simple, not a draft, and unknown.

### `GET /api/v2/bakes`
Your active bakes (default), or your 50 most recently completed (`status=completed`). **Auth:** session, or device token with `bakes:read`. **Query:** `status` (`active` or `completed`). **200:** `{"bakes": [bake]}`. **Errors:** `status_invalid`, `not_signed_in`.

### `POST /api/v2/bakes`
Start a bake from any recipe you can see. Up to three active at once. **Auth:** session, or device token with `bakes:write` (the bake records `created_via: ha`). **Headers:** optional `Idempotency-Key`. **Body:** `recipe_id`, `anchor_type`, `anchor_time`, `time_zone` (required); `alert_mode` (default `simple`), `waits` (`[{"position", "wait_chosen"}]`, overrides), `start_at_step` (a position; earlier steps are skipped and the bake starts in progress). **201:** `{"bake"}` (200 for a repeated `Idempotency-Key`). **Errors:** `bake_invalid`, `wait_out_of_range`, `bake_already_over`, `bake_limit_reached`, `recipe_is_draft`, `recipe_has_no_steps`, `fancy_requires_ha`, `idempotency_key_invalid`, `not_found`, `not_signed_in`.

### `GET /api/v2/bakes/<bake_id>`
One of your bakes. **Auth:** session or device token with `bakes:read`; owner. **200:** `{"bake"}`. **Errors:** `not_found`, `not_signed_in`.

### `PATCH /api/v2/bakes/<bake_id>`
Change the anchor (before the first check-off), chosen waits, or alert mode; re-projects the schedule. **Auth:** session or device token with `bakes:write`; owner. **Body:** any of `anchor_type` with `anchor_time`, `waits`, `alert_mode`. **200:** `{"bake"}`. **Errors:** `body_invalid`, `bake_invalid`, `wait_out_of_range`, `bake_in_progress`, `bake_already_over`, `bake_completed`, `fancy_requires_ha`, `not_found`, `not_signed_in`.

### `GET /api/v2/bakes/by-suffix/<suffix>`
Resolve one of your bake URLs. **Auth:** session or device token with `bakes:read`; owner. **200:** `{"bake"}`. **Errors:** `not_found`, `not_signed_in`.

### `POST /api/v2/bakes/<bake_id>/complete`
Finish it now: steps left are checked off at `completed_at` (default now). Outcome `finished`. Repeating changes nothing. **Auth:** session or device token with `bakes:write`; owner. **Body:** optional `completed_at`. **200:** `{"bake"}`. **Errors:** `completed_at_invalid`, `bake_completed` (canceled or expired), `not_found`, `not_signed_in`.

### `POST /api/v2/bakes/<bake_id>/cancel`
End it without finishing; steps not done stay unchecked. Outcome `canceled`. Repeating, or canceling a completed bake, changes nothing. **Auth:** session or device token with `bakes:write`; owner. **200:** `{"bake"}`. **Errors:** `not_found`, `not_signed_in`.

### `POST /api/v2/bakes/<bake_id>/steps/<position>/complete`
Check off a step at `completed_at`. First write wins. **Auth:** session or device token with `bakes:write`; owner. **Body:** `completed_at`. **200:** `{"bake"}`. **Errors:** `completed_at_invalid`, `bake_completed`, `not_found`, `not_signed_in`.

### `POST /api/v2/bakes/<bake_id>/steps/<position>/skip`
Skip a step that isn't done, at `skipped_at`. Its wait drops out and later steps re-project; skipping alone doesn't start a bake. First write wins. **Auth:** session or device token with `bakes:write`; owner. **Body:** `skipped_at`. **200:** `{"bake"}`. **Errors:** `skipped_at_invalid`, `bake_completed`, `not_found`, `not_signed_in`.

### `POST /api/v2/events`
Record a product event that only the browser sees. **Auth:** session. **Body:** `type` (allow-list: `ics_exported`) and `bake_id` (one of your bakes). **204.** **Errors:** `event_type_invalid`, `bake_id_invalid`, `not_found`, `not_signed_in`.

### `POST /api/v2/pairing-codes`
Get a code for pairing Home Assistant: 8 Crockford base32 characters, shown as `XXXX-XXXX`. It works once, within ten minutes; issuing another voids the last. Only its hash is stored. **Auth:** session. **201:** `{"code", "expires_at"}`. **Errors:** `not_signed_in`.

### `POST /api/v2/devices`
Home Assistant exchanges a pairing code for a device token, shown this once and never again. Codes are read forgivingly: any case, with or without the dash, and I, L, O as 1, 1, 0. Five failed attempts per network in 15 minutes, then 429. **Auth:** none. **Body:** `code`; optional `label` (up to 60 characters). **201:** `{"token", "connection"}`. **Errors:** `pairing_code_invalid`, `rate_limited`, `body_invalid`.

### `GET /api/v2/connections`
Your paired Home Assistant instances, newest first; revoked ones are left out. **Auth:** session. **200:** `{"connections": [connection]}`. **Errors:** `not_signed_in`.

### `DELETE /api/v2/connections/<connection_id>`
Revoke a connection: its token stops working at once, along with every agent calling through it. **Auth:** session; owner. **204.** **Errors:** `not_found` (including one already revoked), `not_signed_in`.

### `GET /api/v2/admin/recipes`
Every default recipe for curation, archived ones included (last), by name. **Auth:** admin. **200:** `{"recipes": [recipe summary]}`. **Errors:** `admin_key_invalid`, `admin_required`, `not_signed_in`, `scope_missing`, `rate_limited`.

### `POST /api/v2/admin/recipes`
Create a default recipe. **Auth:** admin. **Body:** a recipe body (no drafts; prerequisites must be defaults). **201:** `{"recipe"}`. **Errors:** `admin_key_invalid`, `admin_required`, `not_signed_in`, `scope_missing`, `rate_limited`, `recipe_invalid`, `wait_out_of_range`.

### `PUT /api/v2/admin/recipes/<recipe_id>`
Replace a default recipe; its slug never changes. **Auth:** admin. **Body:** a recipe body. **200:** `{"recipe"}`. **Errors:** `admin_key_invalid`, `admin_required`, `not_signed_in`, `scope_missing`, `rate_limited`, `recipe_invalid`, `wait_out_of_range`, `not_found`.

### `DELETE /api/v2/admin/recipes/<recipe_id>`
Archive a default: it leaves every list but still opens by id or URL. **Auth:** admin. **204.** **Errors:** `admin_key_invalid`, `admin_required`, `not_signed_in`, `scope_missing`, `rate_limited`, `not_found`.

### `DELETE /api/v2/admin/recipes/<recipe_id>/publish`
Unpublish any community recipe. **Auth:** admin. **204.** **Errors:** `admin_key_invalid`, `admin_required`, `not_signed_in`, `scope_missing`, `rate_limited`, `not_found`.

### `GET /api/v2/admin/users`
Users, newest first, up to 500. **Auth:** admin. **Query:** `q` (name contains, ignoring case, `-` and `_`), `active=1` (seen in the last 30 days), `tests=0` (leave out test users). **200:** `{"users": [admin user]}`. **Errors:** `admin_key_invalid`, `admin_required`, `not_signed_in`, `scope_missing`, `rate_limited`.

### `POST /api/v2/admin/users/<user_id>/key`
Reset a user's key, for someone the admin can verify personally. The new key is returned this once; the old key stops working and every session for that user ends. Records a `key_reset` event. Admins can't reset their own key here. **Auth:** admin. **200:** `{"user", "key"}`. **Errors:** `own_key_reset`, `not_found`, `admin_key_invalid`, `admin_required`, `not_signed_in`, `scope_missing`, `rate_limited`.

### `PATCH /api/v2/admin/users/<user_id>`
Rename a user. Signup's rules apply, except reserved names are allowed. **Auth:** admin. **Body:** `{"username"}`. **200:** `{"user"}`. **Errors:** `username_invalid`, `username_taken`, `body_invalid`, `not_found`, `admin_key_invalid`, `admin_required`, `not_signed_in`, `scope_missing`, `rate_limited`.

### `GET /api/v2/admin/metrics`
The usage metrics, as `flask --app main metrics` prints them: read-only, with test users left out. **Auth:** admin. **200:** `{"metrics": [{"name", "question", "columns", "rows": [object]}]}`; each row's fields depend on the metric and are listed in order in `columns` (empty when there are no rows), and dates are ISO 8601. **Errors:** `admin_key_invalid`, `admin_required`, `not_signed_in`, `scope_missing`, `rate_limited`.
