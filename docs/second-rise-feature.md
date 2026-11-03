# Breadsheet Second Rise: Spec & Backlog

Nov 1, 2026 · @Thomas

## Overview

Second Rise turns breadsheet from a standalone scheduler into a tool that tracks a live bake and alerts you when each step is due. Alerts come in two flavors: Simple, a calendar feed any calendar app can subscribe to, or Fancy, Home Assistant with Live Activities. Your AI assistant (Claude or ChatGPT) can also plan a bake around your calendar, start it, check off steps, and import recipes, through a remote MCP server. It stays a public web app at breadsheet.com; HA support is an opt-in custom integration anyone can install from the Home Assistant Marketplace.

To get there, breadsheet gains lightweight no-login identity, per-user recipes, bakes as a first-class object, optional step detail (wait ranges, hands-on time), and a move from DynamoDB to Postgres.

| Repo | Role | Changes in Second Rise |
| --- | --- | --- |
| `brystmar/breadsheet` | Flask backend + MCP service | Postgres migration, identity, bakes, `/api/v2`, OAuth for agents, MCP server, calendar feed |
| `brystmar/breadsheet-ui` | React frontend | Plan and bake views, identity flows, simple/detailed recipe editing, agent consent, alert settings |
| `brystmar/breadsheet-hass` | HA custom integration (new) | Pairing, polling, calendar, actions, panel, blueprint |

**Convert-text: migrate, don't change.** The existing hidden convert-text feature (reformats recipes for pasting into Paprika 3) moves to Postgres with everything else, but its behavior does not change: same output, same `/api/v1/replacements` endpoints and response shape, same UI, still hidden. `/api/v1/replacements` stays in service indefinitely; it is not retired with the rest of v1 and gets no v2 equivalent. A rewrite is parked in the backlog.

## Decisions

Every question raised during scoping is settled; these are the answers the rest of the spec builds on.

| Area | Decision |
| --- | --- |
| Alerts | Two options, Simple or Fancy, and a user can turn on either or both. **Simple:** a per-user calendar feed (ICS) any calendar app can subscribe to. **Fancy:** Home Assistant with Live Activities. In-tab browser alerts as a cheap extra; real Web Push deferred. |
| AI agents | A remote MCP server, built for Claude and ChatGPT connectors. Agents use the same `/api/v2` as everyone else, through the MCP tools. |
| Agent auth | OAuth 2.1, with breadsheet as its own authorization server. A signed-in browser approves the agent on a consent page; each agent gets its own revocable, scoped token. The user's key never reaches an agent. |
| Calendars | The agent reads the user's calendar on its own side. Breadsheet never sees or stores it. |
| Recipe import | Agents import recipes (from pasted text, a photo, or a URL) through MCP. Imports are saved as drafts the owner reviews and saves before use. |
| HA integration shape | Custom integration in its own repo (`breadsheet-hass`), distributed via the Home Assistant Marketplace (built-in successor to HACS as of HA 2026.11). Not an add-on. |
| Data flow | HA polls breadsheet (outbound only). No webhooks, no remote access required. |
| Identity | Username (display handle) + generated secret key. No passwords, no recovery in v1. |
| Recipe ownership | Admin-owned defaults visible to all; users copy them into independent personal recipes. |
| Step timing | Each step stores a min and max wait; bakes store the chosen value. Out-of-range allowed, flagged. |
| Recipe detail | Optional, in one schema. **Simple** (the default): one wait per step, as today. **Detailed:** adds wait ranges, hands-on time, and a "needs you home" flag. A recipe can switch at any time. Missing detail means *unknown*, never zero. |
| Same-minute steps | Never grouped. Separate notifications, 1 to 2 seconds apart. Zero-wait steps get no Live Activity. |
| Late steps | One nag at +5 min, then silence. Schedule shifts only on check-off. |
| Early check-off | Allowed; downstream steps re-project from the actual time. |
| Bake status | Three values only: not started, in progress, completed. Cancelling and passing the projected end both mark a bake completed. |
| Abandonment | A bake auto-completes at its latest projected end time. |
| Concurrent bakes | Allowed, soft cap of 3 active (not started or in progress) per user. |
| Quiet hours | Out of scope. Phone-level Do Not Disturb and companion app settings already handle muting. |
| Live Activities | Opt-in, step level. One activity updated across consecutive steps; ended for waits over 4 hours. |
| Database | Postgres on Neon free tier, US West region. Replaces DynamoDB entirely, including replacements; PynamoDB and boto3 are removed. |
| API | New `/api/v2`, frozen before the integration ships. v1 is reimplemented on Postgres at cutover with identical responses; v1 recipe endpoints retire later, `/api/v1/replacements` stays. |
| API host | `api.breadsheet.com`, an App Engine custom domain with a Google-managed certificate; still App Engine standard. Being same-site with breadsheet.com keeps the session cookie first-party. |
| Cache | App Engine shared memcache (free, best-effort) for idle-poll answers and rate-limit counters. |
| CORS | Credentialed CORS for `https://breadsheet.com` and `https://www.breadsheet.com` only (plus localhost in dev); no wildcard origins. |
| HA panel auth | Integration passes a short-lived token in the panel URL; no reliance on cookies. |
| Existing recipes | Migrated from DynamoDB; Thomas curates the defaults, the rest are archived, not deleted. |
| Backlog | GitHub Projects, one board across all three repos. |
| URLs | Defaults use a pure slug (/recipes/country-sourdough). Personal recipes append a 6-character lowercase suffix (/recipes/country-sourdough-k7qx2m); the suffix does the lookup, so renames redirect. Bakes use /bakes/\<suffix>. Old recipe URLs (breadsheet.com/\<id>, with any legacy id, timestamp or UUID) redirect to the homepage; no legacy ids are stored. These public URLs are user-facing only; the API keeps using internal ids. |
| Link sharing | Anyone with a personal recipe's URL can view it read-only and copy it. Only the owner can edit. |

## Identity and ownership

A user is a username plus a secret key; whoever holds the key is that user. There are no passwords and, in v1, no recovery.

**Signup**

1. The user picks a username: unique, case-insensitive, display only.
2. Breadsheet generates a 128-bit random key and shows it once as a copyable string, a QR code, and a link (`breadsheet.com/k/<key>`).
3. The user must copy, download, or scan it before continuing. Copy states plainly that the key is the only way back in.
4. The server sets a first-party session cookie so the browser stays signed in: `HttpOnly`, `Secure`, `SameSite=Lax`, one-year lifetime refreshed on use. Losing the cookie costs nothing if the key was saved.

**Other devices.** Opening the key link on any other browser signs that browser in and sets the same session cookie, exactly as signup does. The key never needs to be retyped.

**Security**

- **Key hashing.** Keys are 128-bit random values from Python's `secrets` module, so they don't need a slow password hash like bcrypt or Argon2 (those exist to protect weak, human-chosen passwords). Store SHA-256 of the key (`hashlib`, standard library), look users up by that hash, and compare with `hmac.compare_digest`. Device tokens (256-bit), OAuth access and refresh tokens, authorization codes, calendar feed tokens, and panel tokens all use the same scheme. The same practice is used for API tokens generally.
- **OAuth.** Authorization code flow with PKCE (`S256` only), exact-match redirect URIs, single-use codes that expire in 60 seconds, access tokens that last 1 hour, and refresh tokens that rotate on every use and expire after 90 days unused. Scopes: `recipes:read`, `recipes:write`, `bakes:read`, `bakes:write`.
- **Pairing codes.** 8 characters from Crockford base32 (no I, L, O, or U), shown as `XXXX-XXXX`. They expire after 10 minutes, work once, and each user has at most one live code; issuing a new one voids the old one.
- **Rate limits.** Per client IP, returning HTTP 429 when exceeded: 10 failed key sign-ins per 15 minutes on `POST /session`, 5 failed pairing attempts per 15 minutes on `POST /devices`, 5 signups per hour on `POST /users`. Counters live in the same cache as idle polls.
- **CSRF.** `SameSite=Lax` cookies, the restricted CORS origin list, and requiring `Content-Type: application/json` on every state-changing request (which forces a CORS preflight) together cover it; no CSRF tokens needed.

**Home Assistant.** Breadsheet shows a short pairing code; the integration's config flow exchanges it for a separate device token tied to the user. The master key never enters HA, and HA access can be revoked from breadsheet.

**AI agents.** The user adds breadsheet's MCP URL as a connector in Claude or ChatGPT. The client starts a standard OAuth flow that lands on breadsheet's consent page (`breadsheet.com/connect`). If the browser isn't signed in, the user opens their key link first. The page names the agent and the scopes it asks for; approving it issues that agent its own token. Agents and HA devices appear together in one connections list, and each can be revoked on its own.

**Connections** is the umbrella for every non-browser client: HA devices and AI agents share one table, one list screen, and one revoke action.

**Recipe scopes**

- **Default:** owned by the admin, visible to everyone including incognito, read-only for users. Only the admin can create new default recipes.
- **Personal:** created from scratch or copied from any recipe the user can see (a default or a shared personal recipe). Copies are fully independent of their source. This is the default for new recipes; there shouldn’t be a visible option that indicates otherwise. Anyone with the link can view a personal recipe read-only and copy it; only the owner can edit. A copy becomes the copier's own personal recipe, with its own URL suffix, fully editable.

**Admin.** Defaults are managed with a separate admin key in server config, not a user role.

**Groundwork for later.** Store `last_seen_at` per user so abandoned-username reclamation can become a policy rather than a migration.

## Data model

Ten Postgres tables replace every DynamoDB model (`Recipe`, `Step`, and `Replacement`) and add identity, bakes, and agent auth; the `events` table from Usage metrics comes later. Times are stored in UTC; durations in seconds.

| Table | Key columns | Notes |
| --- | --- | --- |
| `users` | id, username (unique, case-insensitive), key\_hash, calendar\_token\_hash (nullable), alert\_simple, alert\_fancy, created\_at, last\_seen\_at | Store only hashes. `calendar_token_hash` backs the Simple alert feed; rotating it kills the old feed URL. |
| `connections` | id, user\_id, kind (ha or agent), oauth\_client\_id (agents only), label, scopes, token\_hash, token\_expires\_at, refresh\_token\_hash, refresh\_expires\_at, created\_at, last\_used\_at, revoked\_at | Replaces `device_tokens`. One row per paired HA instance or authorized agent. HA tokens don't expire; agent access tokens last 1 hour and refresh. |
| `pairing_codes` | code, user\_id, expires\_at, used\_at | HA pairing. Short-lived, single use. |
| `oauth_clients` | id, client\_id, name, redirect\_uris, registration\_type (metadata document or dynamic), created\_at | Agent apps such as Claude and ChatGPT, registered automatically when a user first connects one. |
| `oauth_codes` | code\_hash, oauth\_client\_id, user\_id, redirect\_uri, code\_challenge, scopes, expires\_at, used\_at | Authorization codes; 60-second, single use. |
| `recipes` | id, public\_suffix (null for defaults), slug, owner\_id (null = default), source\_recipe\_id, name, author, source, url, difficulty, detail\_level (simple or detailed), is\_draft, archived\_at, timestamps | `source_recipe_id` records where a copy came from; no live link. `is_draft` marks agent imports awaiting review. |
| `recipe_steps` | id, recipe\_id, position, text, note, wait\_min, wait\_max, active\_seconds (nullable), needs\_presence (nullable) | Existing steps migrate as simple: `wait_min = wait_max = then_wait`, detail fields null. |
| `bakes` | id, public\_suffix, user\_id, recipe\_id, name\_snapshot, anchor\_type (start or finish), anchor\_time, time\_zone (IANA, e.g. `America/Los_Angeles`), status, created\_via (web, ha, or agent), idempotency\_key (nullable, unique per user), started\_at, completed\_at, projected\_end | Status: not\_started, in\_progress, completed. |
| `bake_steps` | id, bake\_id, position, text\_snapshot, wait\_min, wait\_max, wait\_chosen, active\_seconds, needs\_presence, scheduled\_at, completed\_at | Snapshot of the recipe at bake start, so later recipe edits never change a running bake. |
| `replacements` | id, scope, old, new | Convert-text substitutions; unique on (scope, old), matching the DynamoDB hash and range keys. Migrated as is. |

**Recipe detail levels.**

- **Simple:** each step has text, a note, and one wait. Stored as `wait_min = wait_max`, with `active_seconds` and `needs_presence` null. This is the default for new recipes and for everything migrated from DynamoDB.
- **Detailed:** each step can also have a wait range, `active_seconds` (hands-on time, counted from the step's start), and `needs_presence` (you must be home, not just awake).
- `detail_level` only controls which fields the recipe view shows. Switching from detailed back to simple hides the extra fields but doesn't erase them.
- **Unknown is not zero.** When `active_seconds` is null, scheduling assumes 10 minutes of hands-on time at the step's start and marks the schedule as estimated. When `needs_presence` is null, it assumes presence is needed for those hands-on minutes. A step with no range has a fixed wait, so only the whole bake can move.
- **Validation:** `0 ≤ wait_min ≤ wait_max` and `active_seconds ≥ 0`. Hands-on time longer than the step's wait is allowed but flagged, since it overlaps the next step. Drafts can be saved incomplete; a recipe must pass validation before it leaves draft.

**Slugs and suffixes.**

- A slug is generated from the recipe name (lowercase, hyphenated). Default slugs must be unique among defaults; a collision appends `-2`, `-3`, and so on. Default slugs never change once created.
- A public suffix is 6 random characters from `a-z0-9`, checked against existing suffixes in the same table and regenerated on collision. Personal recipes and bakes each get one.
- Renaming a personal recipe regenerates its slug and keeps its suffix, so old links still resolve and redirect.
- Copying a recipe creates a new slug from the name and a new suffix.

**Projection rule.** A step's `scheduled_at` is the previous step's completion time (or that step's scheduled time if it isn't checked off yet) plus that previous step's `wait_chosen`. Checking off a step re-projects every later step.

## Bake behavior

A bake is a snapshot of a recipe with a schedule anchored to a start or finish time; it runs until checked off or until its projected end passes.

- **Start.** Choose a recipe, set the anchor (start or finish) and time zone, adjust any step's wait within or outside its range, then start. Steps are copied into `bake_steps`. Draft recipes can't be baked.
- **Idempotent start.** `POST /bakes` accepts an `Idempotency-Key` header. A repeat with the same key returns the original bake instead of creating a second one, so a retrying agent never double-books a loaf.
- **Time zones.** Every bake stores the IANA time zone it was planned in. Responses include each step's time in UTC and in that zone, so "Thursday at 7am" means the same thing to the agent, the server, and the calendar feed.
- **Status.** A bake is *not started* from Start until its first step is checked off, *in progress* after that, and *completed* once every step is checked off, it's cancelled, or its projected end passes. Notifications run for both not-started and in-progress bakes.
- **Cancel.** The owner can end a bake at any time; it becomes completed and all notifications stop.
- **Check-off.** Any step can be marked done at any time, including early. All later steps re-project from that moment.
- **Out-of-range waits.** Allowed; the UI flags them. No hard block.
- **Late.** If a step passes its scheduled time unchecked, one reminder fires at +5 minutes. After that, silence. The schedule does not shift on its own.
- **Abandonment.** When the latest projected end time passes, the bake becomes completed automatically. No further notifications or input.
- **Concurrency.** Up to 3 active (not started or in progress) bakes per user (soft cap with a clear message). Every notification names its bake.
- **Same-minute steps.** Each gets its own notification, sent 1 to 2 seconds apart, in step order.

## API v2

All new functionality lives under `/api/v2` on `api.breadsheet.com`; the contract is frozen before `breadsheet-hass` or the MCP server ships. v1 keeps its exact request and response shapes, reimplemented on Postgres. Browser calls authenticate with the session cookie; HA calls send the device token as a bearer header; the MCP service forwards the agent's OAuth access token as a bearer header, and each endpoint checks the token's scopes. Paths use internal ids (`<id>`), never the public URL suffixes or slugs, which exist only for user-facing URLs. "All" in the Caller column means browser, HA, and agents.

| Method and path | Purpose | Caller |
| --- | --- | --- |
| `POST /api/v2/users` | Create user; returns key once | Browser |
| `POST /api/v2/session` | Exchange key for session cookie | Browser |
| `GET /api/v2/session` | Who am I: the signed-in user, or 401 | Browser |
| `DELETE /api/v2/session` | Sign out this browser (clears the cookie) | Browser |
| `POST /api/v2/pairing-codes` | Issue a short-lived HA pairing code | Browser |
| `POST /api/v2/devices` | Exchange pairing code for device token | HA |
| `GET /api/v2/connections` | List the user's HA devices and authorized agents | Browser |
| `DELETE /api/v2/connections/<id>` | Revoke an HA device or agent | Browser |
| `GET /api/v2/recipes?q=<text>` | Defaults plus the caller's personal recipes, optionally filtered by name; drafts only for their owner | All |
| `POST /api/v2/recipes` | Create a personal recipe from scratch | Browser |
| `POST /api/v2/recipes/import` | Create a draft personal recipe from structured input; returns the draft and a review link | Agent |
| `POST /api/v2/recipes/<id>/copy` | Copy a recipe (default or shared personal) into a new personal recipe | Browser |
| `GET /api/v2/recipes/<id>` | Read a recipe: defaults for anyone, personal for anyone with the link, drafts for the owner only | All |
| `PUT/DELETE /api/v2/recipes/<id>` | Edit or delete a personal recipe (owner only); saving with `is_draft: false` takes a draft live | Browser |
| `GET /api/v2/recipes/by-slug/<slug>` | Resolve a default recipe URL; returns the recipe with its internal id | Browser |
| `GET /api/v2/recipes/by-suffix/<suffix>` | Resolve a personal recipe URL (anyone with the link, read-only); returns the recipe with its internal id and current slug, so the UI can redirect renamed URLs | Browser |
| `POST /api/v2/schedules/preview` | Project a recipe's full schedule for an anchor, time zone, and chosen waits, without saving anything. Returns each step's time, hands-on window, and whether it's estimated | Browser, Agent |
| `GET /api/v2/bakes?status=active` | Active (not started or in progress) bakes with full step schedule | All |
| `GET /api/v2/bakes/<id>` | One bake with its full step schedule | All |
| `GET /api/v2/bakes/by-suffix/<suffix>` | Resolve a bake URL (owner only); returns the bake with its internal id | Browser |
| `POST /api/v2/bakes` | Start a bake; honors `Idempotency-Key` | Browser, Agent |
| `PATCH /api/v2/bakes/<id>` | Change anchor or chosen waits | Browser, Agent |
| `POST /api/v2/bakes/<id>/cancel` | End a bake early; marks it completed | Browser, Agent |
| `POST /api/v2/bakes/<id>/steps/<pos>/complete` | Check off a step | All |
| `POST /api/v2/calendar-feed` | Create or rotate the user's Simple alerts feed; returns the private feed URL once | Browser |
| `DELETE /api/v2/calendar-feed` | Turn off the feed; the old URL stops working | Browser |
| `GET /api/v2/calendar/<token>.ics` | The feed itself, authenticated by the token in the URL (calendar apps can't send cookies or headers) | Calendar apps |
| `GET /api/v2/bakes/<id>.ics` | One-time download of a single bake's steps, for importing into a calendar | Browser |
| `POST /api/v2/panel-tokens` | Short-lived token for the HA panel URL | HA |
| `POST /api/v2/admin/recipes` | Create a default recipe (admin key) | Admin |
| `PUT/DELETE /api/v2/admin/recipes/<id>` | Edit or archive a default recipe (admin key); slug never changes | Admin |

**OAuth endpoints** (on `api.breadsheet.com`, outside `/api/v2` because their paths are set by the OAuth standards):

| Path | Purpose |
| --- | --- |
| `GET /.well-known/oauth-authorization-server` | Authorization server metadata (endpoints, scopes, PKCE support) |
| `POST /oauth/register` | Dynamic client registration, for clients that don't use a client metadata document |
| `GET /oauth/authorize` | Starts the flow; redirects to the consent page at `breadsheet.com/connect` |
| `POST /oauth/token` | Exchanges a code (with PKCE verifier) for tokens; refreshes tokens |
| `POST /oauth/revoke` | Revokes a token; the connections list calls the same logic |

**Errors.** Every v2 error returns a JSON body with a stable `code` (such as `bake_limit_reached`, `wait_out_of_range`, `recipe_is_draft`, `scope_missing`) and a plain-language `message` that says what to do next, so an agent can recover without guessing.

**Polling support.** `GET /api/v2/bakes?status=active` returns an ETag and a suggested next poll interval. When the user has no active bakes, the server answers from a cache without querying Postgres, so idle polls never wake the Neon database.

**Cache.** App Engine's shared memcache, the free tier of the bundled memcache service (dedicated memcache is billed per GB-hour and not needed). Capacity is best-effort with no guarantees, which is fine: the cache only holds data that can be rebuilt. It stores each user's "no active bakes" flag (cleared when a bake starts) and the rate-limit counters. A missing entry costs at most one Postgres wake-up or a reset rate-limit count. It requires the `appengine-python-standard` SDK, which pins `urllib3<2`, plus the bundled-services setting in `app.yaml`. Google's docs show both `app_engine_apis: true` and `app_engine_bundled_services: [memcache]`, so confirm which one applies to `python314` when setting it up in item 6.

## HA integration (breadsheet-hass)

The integration pulls active bakes from breadsheet and exposes them as HA entities; a bundled blueprint turns those into notifications and Live Activities. Nothing ever connects inbound to the user's HA.

**Distribution.** Starting with HA 2026.11, HACS is built into Home Assistant as the Marketplace (Settings → Marketplace). Implications for breadsheet-hass:

- New community repos are still submitted through the `hacs/default` repository.
- The Marketplace installs from GitHub release assets rather than arbitrary scripts, so every version ships as a tagged release with a packaged asset.
- Users accept a one-time warning that Marketplace content is independent and not tested or supported by Home Assistant; only admins can install.
- Check the Marketplace contributor docs (contributors.home-assistant.io/marketplace) for manifest requirements before the first release.

**Setup.** A config flow asks for the pairing code from breadsheet, exchanges it for a device token, and stores the token in the config entry.

**Polling.** Every 60 seconds while a bake is active; every 15 to 30 minutes otherwise, honoring the server's suggested interval and ETag.

**Entities**

- **Calendar:** one event per bake step at its scheduled time. Built-in calendar triggers with offsets handle "2 minutes before" and "now".
- **Sensors:** per active bake, the current step, next step, next step time, and progress.
- **Action:** `breadsheet.complete_step` (bake id, step position), calling the API and refreshing immediately.

**Sidebar panel.** Registered at `/breadsheet`. It embeds the breadsheet bake view using a short-lived panel token in the URL. Live Activity taps open `/breadsheet/<bake_id>`.

**Blueprint.** Inputs: notify targets, lead time (default 2 min), Live Activities on or off.

- Sends a notification before and at each step, with a "Done" action that calls `breadsheet.complete_step`.
- Sends one late reminder at +5 minutes, then nothing.
- Sends same-minute steps as separate notifications, 1 to 2 seconds apart.

**Live Activities (working name: Proof of Life; opt-in).** Driven by the blueprint through the companion app's `live_update` payload.

- **`tag`:** the bake id, so concurrent bakes each get their own card.
- **`title`:** the recipe name (fixed for the life of the activity).
- **`message`:** the next step. **`chronometer` + `when`:** absolute countdown to it. **`progress`:** steps done of total.
- **`url`:** `/breadsheet/<bake_id>`.
- One activity is updated across consecutive steps. It ends before any wait longer than 4 hours and restarts before the next step, keeping starts to two or three per bake (the 8-hour Apple limit and the push-to-start budget).
- Zero-wait steps get no Live Activity update; the card skips to the next step with a real wait.
- README note: Live Activities need HA reachable from the phone for the token handshake, and the companion app's current requirements (iOS 17.2+, HA Core 2026.7+).

## Alerts

Users choose how they hear about steps in an alerts settings screen: Simple, Fancy, or both. Either works with or without an AI agent.

**Simple: calendar feed.**

- One private ICS feed per user at `api.breadsheet.com/api/v2/calendar/<token>.ics`, shown once with copy and "Add to Apple Calendar / Google Calendar" buttons. Rotating it issues a new URL and kills the old one.
- Every step of every active bake is an event at its scheduled time, titled with the bake and step (for example "Country Sourdough · Fold #2"), with a reminder at the step's start. Hands-on time becomes the event's duration, so a busy calendar shows when you're actually tied up.
- Each step event has a stable `UID` and an increasing `SEQUENCE`, so check-offs and re-projections update events in place instead of duplicating them. Completed and cancelled bakes drop out of the feed.
- Limits to state plainly in the UI: calendar apps refresh subscribed feeds on their own schedule (Google can take hours), and some ignore reminders in subscribed calendars. The one-time `.ics` download per bake is the workaround: imported events keep their reminders, but don't update after a check-off.
- An AI agent with calendar access can also create the events itself, which shows up instantly. The MCP tools return everything it needs for that.

**Fancy: Home Assistant.** The full `breadsheet-hass` experience above: phone notifications with a Done button, the late nag, and Live Activities.

## AI agents (MCP)

Agents connect through a remote MCP server, built and tested for Claude and ChatGPT connectors. It's a thin layer over `/api/v2`; it holds no data and enforces nothing the API doesn't.

**Hosting.**

- A second App Engine service, `mcp`, in the `breadsheet` repo, using the official MCP Python SDK over Streamable HTTP. It runs in stateless mode, so any instance can answer any request and App Engine can scale it to zero.
- Served at `mcp.breadsheet.com/mcp`, routed to the `mcp` service by `dispatch.yaml`, with a Google-managed certificate like the API. It shares the app's free-tier instance hours with the API.
- It advertises protected-resource metadata (`/.well-known/oauth-protected-resource`) pointing at `api.breadsheet.com` as the authorization server. It validates each access token with the API, then calls `/api/v2` with it.

**Connecting.** The user pastes `https://mcp.breadsheet.com/mcp` into Claude's or ChatGPT's connector settings. The client registers itself (a client metadata document, or dynamic registration as the fallback), sends the user to the consent page, and receives tokens. Each client's current connector requirements get verified against its docs when this is built, since both are still evolving.

**Tools.**

| Tool | What it does | Scope |
| --- | --- | --- |
| `search_recipes` | Find recipes by name; returns ids, detail level, and total time | `recipes:read` |
| `get_recipe` | Full recipe with steps, waits, ranges, and hands-on time, with unknowns marked | `recipes:read` |
| `import_recipe` | Turn a recipe the agent has parsed into a draft personal recipe; returns validation results and a review link | `recipes:write` |
| `preview_schedule` | Projected timeline for a recipe, anchor, time zone, and chosen waits; nothing is saved | `recipes:read` |
| `start_bake` | Start a bake from a preview's inputs, with an idempotency key | `bakes:write` |
| `list_active_bakes` | Active bakes with their schedules | `bakes:read` |
| `get_bake` | One bake with its schedule and what's next | `bakes:read` |
| `update_bake` | Change a bake's anchor or chosen waits | `bakes:write` |
| `complete_step` | Check off a step ("I just did the second fold") | `bakes:write` |
| `cancel_bake` | End a bake early | `bakes:write` |

Read-only tools carry MCP's read-only hint, and `cancel_bake` carries the destructive hint, so clients can ask before calling it. Tool descriptions spell out the units (seconds), the time zone handling, and the "unknown is not zero" rule.

**Planning a bake with an agent.** The user says "I want a sourdough loaf on Thursday." The agent finds the recipe, reads the user's calendar on its own side, tries a few anchors and waits with `preview_schedule`, and picks the one that keeps hands-on steps out of meetings and sleep. It confirms with the user, calls `start_bake`, and then either creates calendar events itself or points the user to their alerts.

**Importing a recipe.** The user gives the agent pasted text, a photo of a cookbook page, or a URL. The agent maps it onto the import schema (name, author, source, steps with waits, and optionally ranges and hands-on time), and `import_recipe` saves a draft. The user opens the review link, fixes anything, and saves. Drafts never appear in recipe lists for anyone else and can't be baked until saved.

## UI (breadsheet-ui)

The current schedule table stays nearly untouched; new information goes into separate views so the mobile layout isn't crowded.

- **Recipe view:** edit the template. Visited rarely, so it can carry more density. Defaults show a "Make it mine" copy button instead of edit controls.
  - A **Simple / Detailed** toggle per recipe. Simple (the default) shows one Then Wait per step, as today. Detailed reveals each step's wait range (min and max), hands-on time, and a "needs you home" checkbox.
  - Imported drafts open here with a banner ("Imported by your assistant. Review and save.") and inline validation; Save takes the draft live.
- **Plan view:** today's screen. The Then Wait input stays as is, with the range as a small caption beneath it (for example "60–90"), turning amber when the chosen value is outside the range. Adds a Start bake button.
- **Bake view:** the mid-bake phone screen. Current step, next step with countdown, a large Done button, and the remaining timeline. No edit fields. In-tab browser notifications while it's open.
- **Identity flows:** pick username, save-your-key screen (copy, QR, link), link-another-device, pair Home Assistant (pairing code), and a connections list (HA devices and AI agents together) with revoke.
- **Agent consent (`/connect`):** "Claude wants to read your recipes and manage your bakes." Lists the requested scopes in plain words, with Approve and Deny. Not signed in: prompt for the key link first, then come back.
- **Alerts settings:** two cards side by side.
  - **Simple** is deliberately plain-jane: default system font, thin gray border, no color, no icon. Turning it on reveals the feed URL, copy button, and calendar buttons.
  - **Fancy** gets a little sparkle: a ✨ next to the title, a soft gradient border with a slow shimmer, and a few twinkles on hover. The animation stops under `prefers-reduced-motion`. Turning it on leads to the HA pairing flow.
- **Active bakes list:** up to three, each linking to its bake view.

Mock-ups of the plan and bake views come before implementation, so layout can be judged on real screens.

## Infrastructure and migration

The app stays on App Engine's free tier; the database moves from DynamoDB to a free Neon Postgres project in a US West region.

1. Create the Neon project and a dev branch; add the connection string as an App Engine secret.
2. Map `api.breadsheet.com` to the App Engine app (CNAME in Cloudflare, Google-managed certificate). Turn off Cloudflare's "Always Use HTTPS" for that hostname, or keep the record DNS-only, so certificate validation and renewal can reach App Engine. Point `VITE_BACKEND_URL` at it, switch CORS to the credentialed allow-list, and send `credentials: 'include'` on UI fetches.
3. Replace PynamoDB with SQLAlchemy and Alembic for every model, replacements included, matching the greeting-cards stack. Reimplement the v1 endpoints on Postgres with identical responses and cover them with tests before cutover. Remove PynamoDB, boto3, and moto from requirements.
4. Write a one-time migration script: export DynamoDB recipes and replacements, load into Postgres, set `wait_min = wait_max = then_wait`.
5. Thomas reviews migrated recipes and marks which become defaults; the rest get `archived_at`, not deleted.
6. Verify row counts and spot-check recipes against DynamoDB before cutting over. For replacements, confirm `/api/v1/replacements` responses and convert-text output are identical before and after. Keep the DynamoDB tables until v2 has run cleanly for a while, then delete them and remove the AWS credentials from config.
7. Back up Postgres weekly: a scheduled GitHub Action runs `pg_dump` and uploads the dump to a private Cloud Storage bucket (inside the free tier), keeping the last 12. Not GitHub artifacts, since they're visible to anyone with access to the repo. Test a restore into a Neon branch once.
8. Update `CLAUDE.md`: React is the only frontend (Jinja/WTForms long retired), Postgres replaces DynamoDB, and the three-repo layout.
9. Add the `mcp` App Engine service: its own `app.yaml` in an `mcp/` directory of the `breadsheet` repo, a `dispatch.yaml` rule sending `mcp.breadsheet.com/*` to it, and the `mcp.breadsheet.com` custom domain (same Cloudflare caveat as step 2).

Neon's free compute suspends when idle, so the adaptive polling and cached idle responses in the API section are what keep it free.

## Usage metrics

Two layers, neither invasive: cookieless traffic analytics for visits, and first-party product events in breadsheet's own Postgres for what people actually do.

**Traffic.** Hosted GoatCounter (goatcounter.com), with periodic CSV exports so history is never at the mercy of retention limits: visits, pages, referrers, countries, devices. No cookies, no consent banner, no cross-site tracking. Added to the current site early, so there's a baseline before Second Rise launches.

GoatCounter site: `brystmar.goatcounter.com`. Add this to `index.html` in breadsheet-ui (item 1c):

```html
<script data-goatcounter="https://brystmar.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
```

The script counts the initial page load only. Because React route changes don't reload the page, the router must also call `window.goatcounter.count()` on each navigation, guarded in case the script is blocked or hasn't loaded.

**Product events.** An `events` table: event type, timestamp, pseudonymous user id, and related recipe or bake id, plus client (web, HA, or agent, with the agent's client name). No IP addresses, user agents, or free text. Much of it can also be derived from existing tables.

| Metric | Question it answers |
| --- | --- |
| Weekly active bakers | Is anyone using it, and is it growing? |
| Bakes started vs. finished (every step checked off) | Do people finish what they start? Derived from `bake_steps`, since cancelled and expired bakes are also `completed`. |
| Steps checked off on time, late, or never | Are the notifications working? |
| Share of bakes with HA paired | Is the integration the reason people come back? |
| Bakes started by agents, and recipes imported | Are people actually letting their assistant do the planning? |
| Simple vs. Fancy alerts turned on | Which alert path do people pick? |
| Share of recipes in detailed mode | Is anyone filling in hands-on time? |
| Most-copied default recipes | Which recipes are worth curating? |
| Chosen waits outside the step range | Are the recipe ranges realistic? |
| Bakers returning within 30 days | Retention |

A short privacy page states exactly what's collected and what isn't.

## Backlog

Second Rise breaks into seven epics, roughly in build order; each row below becomes one GitHub issue on the shared Projects board.

| # | Issue | Repo | Epic |
| --- | --- | --- | --- |
| 1a | Upgrade Python (latest App Engine-supported runtime) and backend dependencies; update CLAUDE.md for React frontend and planned Postgres move | breadsheet | Foundation |
| 1b | Upgrade React, Vite, and frontend dependencies to current stable; update UI docs | breadsheet-ui | Foundation |
| 1c | Add hosted GoatCounter to the current site for a pre-launch baseline, including SPA route tracking | breadsheet-ui | Foundation |
| 1d | Serve the API at `api.breadsheet.com` (App Engine custom domain, managed cert); credentialed CORS allow-list; point the UI at it | breadsheet, breadsheet-ui | Foundation |
| 2 | Create Neon project, dev branch, App Engine secret | breadsheet | Foundation |
| 3 | Replace PynamoDB with SQLAlchemy + Alembic for all models (incl. replacements); initial schema with every table and column in the Data model section, including the detail, time zone, idempotency, and OAuth fields; v1 endpoints on Postgres with identical responses; remove PynamoDB and boto3 | breadsheet | Foundation |
| 4 | DynamoDB to Postgres migration script (recipes and replacements) with verification; convert-text behavior unchanged | breadsheet | Foundation |
| 5 | Curate default recipes; archive the rest | breadsheet | Foundation |
| 5b | Weekly `pg_dump` backups to a private Cloud Storage bucket; one test restore | breadsheet | Foundation |
| 6 | Users, key hashing, session cookie, key-link sign-in, sign-in and signup rate limits; set up shared memcache here, since the rate limits need it first | breadsheet | Identity |
| 7 | Pairing codes, connections table (HA device tokens), connections list, revoke, pairing rate limits | breadsheet | Identity |
| 8 | Admin key for managing defaults | breadsheet | Identity |
| 9 | Signup, save-your-key, link-device screens | breadsheet-ui | Identity |
| 10 | Pair HA and connections list screens (HA and agents) | breadsheet-ui | Identity |
| 11 | Recipe scopes, copy-to-personal, slugs and suffixes, URL lookup endpoints | breadsheet | Recipes and bakes |
| 12 | Recipe detail levels in the API: wait ranges, hands-on time, needs-presence, validation, the "unknown is not zero" defaults, drafts | breadsheet | Recipes and bakes |
| 13 | Bakes: start, snapshot, projection, check-off, cancel, auto-complete, time zones, idempotent start | breadsheet | Recipes and bakes |
| 13b | Schedule preview endpoint (no save), with hands-on windows and estimated flags | breadsheet | Recipes and bakes |
| 13c | Simple alerts: per-user ICS feed with rotate/revoke, stable UIDs, and the per-bake `.ics` download | breadsheet | Recipes and bakes |
| 14 | Freeze `/api/v2` contract (including error codes and the MCP tool set) and document it | breadsheet | Recipes and bakes |
| 15 | Idle-poll cache (using the memcache from item 6) and suggested poll interval | breadsheet | Recipes and bakes |
| 16 | Mock up plan and bake views | breadsheet-ui | UI |
| 17 | Recipe view with the Simple/Detailed toggle, range and hands-on editing, "Make it mine", and the draft review banner | breadsheet-ui | UI |
| 18 | Plan view range caption and Start bake | breadsheet-ui | UI |
| 19 | Bake view and active bakes list | breadsheet-ui | UI |
| 20 | In-tab browser notifications | breadsheet-ui | UI |
| 20b | Alerts settings: plain Simple card (feed URL, calendar buttons) and sparkly Fancy card (leads to HA pairing) | breadsheet-ui | UI |
| 21 | Repo scaffold, Marketplace manifest, release-asset packaging, config flow with pairing | breadsheet-hass | HA integration |
| 22 | Adaptive polling coordinator | breadsheet-hass | HA integration |
| 23 | Calendar entity and bake sensors | breadsheet-hass | HA integration |
| 24 | `complete_step` action | breadsheet-hass | HA integration |
| 25 | Sidebar panel with panel tokens | breadsheet-hass | HA integration |
| 26 | Notification blueprint (lead time, Done action, late nag) | breadsheet-hass | HA integration |
| 27 | Live Activities in blueprint (opt-in) | breadsheet-hass | HA integration |
| 28 | README and Marketplace submission | breadsheet-hass | HA integration |
| 29 | Product events table, metrics queries, and privacy page | breadsheet | Metrics |
| 30 | OAuth authorization server: metadata, client metadata documents and dynamic registration, authorize, token with PKCE, refresh rotation, revoke, scopes | breadsheet | AI agents |
| 31 | Consent screen at `/connect` | breadsheet-ui | AI agents |
| 32 | `mcp` App Engine service: Streamable HTTP (stateless), protected-resource metadata, token validation, `dispatch.yaml`, `mcp.breadsheet.com` | breadsheet | AI agents |
| 33 | MCP tools: search, get, preview, start, list, get bake, update, complete, cancel, with hints and agent-friendly descriptions | breadsheet | AI agents |
| 34 | `import_recipe`: import schema, validation, draft creation, review link | breadsheet | AI agents |
| 35 | End-to-end tests with Claude and ChatGPT connectors (plan a bake from a calendar, import a recipe from a photo); connector setup guide | breadsheet | AI agents |

**Parked for later**

- Community recipe emporium: publish personal recipes; others copy them; publishers edit only their own.
- Username recovery.
- Abandoned username reclamation using `last_seen_at`.
- Dough Not Disturb (reserved name): a plan-view warning when a step lands in a user-defined sleep window. Muting stays with the phone.
- Check-off directly from a Live Activity, once the companion app supports actions on activities.
- Web Push notifications for non-HA users.
- Server-side schedule fitting: `preview_schedule` accepts busy windows and picks the waits itself, instead of the agent trying options.
- MCP support for other assistants (Gemini, Copilot, and so on) once Claude and ChatGPT work well.
- Official HA core integration, if adoption warrants it.
- Convert-text rewrite: a fuller Paprika 3 formatter to replace the find-and-replace version.
- Deleting a recipe that has bakes: decide whether to block it, archive instead, or keep the bakes with `recipe_id` set to null. Bakes keep their own step snapshot either way. Needs an interim rule before item 13 ships.
