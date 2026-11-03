# Breadsheet Second Rise: Spec & Backlog

Nov 1, 2026 · updated Nov 3, 2026 · @Thomas

## Overview

Second Rise turns breadsheet from a standalone scheduler into a tool that tracks a live bake and alerts you when each step is due. Every bake picks its alerts when it starts: Simple, the bake's steps exported as calendar events in an ICS file, or Fancy, Home Assistant notifications with Live Activities. Users keep their own recipe collections and can publish recipes to a community library. Your AI assistant (Claude or ChatGPT) can also plan a bake around your calendar, start it, check off steps, and import recipes, through a remote MCP server. It stays a public web app at breadsheet.com; HA support is an opt-in custom integration anyone can install from the Home Assistant Marketplace.

To get there, breadsheet gains lightweight no-login identity, personal and community recipes, bakes as a first-class object, optional step detail (wait ranges, hands-on time), and a move from DynamoDB to Postgres. The work ships in four milestones (see Milestones).

| Repo | Role | Changes in Second Rise |
| --- | --- | --- |
| `brystmar/breadsheet` | Flask backend + MCP service | Postgres migration, identity, community recipes, bakes, `/api/v2`, OAuth for agents, MCP server |
| `brystmar/breadsheet-ui` | React frontend | Identity flows, collections and community library, simple/detailed recipe editing, plan and bake views, bake alert options and ICS export, agent consent |
| `brystmar/breadsheet-hass` | HA custom integration (new) | Pairing, polling, calendar, actions, panel, blueprint |

**Convert-text: migrate, don't change.** The existing hidden convert-text feature (reformats recipes for pasting into Paprika 3) moves to Postgres with everything else, but its behavior does not change: same output, same `/api/v1/replacements` endpoints and response shape, same UI, still hidden. `/api/v1/replacements` stays in service indefinitely; it is not retired with the rest of v1 and gets no v2 equivalent. A rewrite is parked in the backlog.

## Milestones

Four releases, each shippable on its own. The `/api/v2` contract only grows: endpoints added in a later milestone never change ones that already shipped.

| Milestone | What ships | Done when |
| --- | --- | --- |
| M1: Database migration | Postgres on Neon, v1 reimplemented on it, `api.breadsheet.com`, backups | breadsheet.com runs on Postgres with v1 and convert-text behaving identically, and DynamoDB is kept as a fallback. Users see no change. |
| M2: Collections, community, and Simple alerts | Key-based sign-in, personal collections, copying defaults, private recipes, community publishing and copying, bakes, plan and bake views, Simple alerts with ICS export, product events | A new user can sign up, build a collection, publish a recipe or copy a community one, start a bake, and download its steps as calendar events. |
| M3: Home Assistant (Fancy alerts) | `breadsheet-hass`, pairing and connections, the Fancy option enabled at bake start, Live Activities | A user can pair HA, start a Fancy bake, and get phone notifications with a Done button. |
| M4: AI agents | OAuth server, consent screen, MCP service and tools, recipe import, schedule preview | Claude and ChatGPT can plan, start, and manage a bake, and import a recipe as a draft. |

**Schema by milestone.** Each milestone adds only its own tables and columns, through Alembic migrations.

- **M1:** `recipes` (v1 columns), `recipe_steps` (with `wait_min` and `wait_max`), `replacements`.
- **M2:** `users`, `bakes`, `bake_steps`, `events`, and the ownership, slug, suffix, community, detail, and draft columns on `recipes` and `recipe_steps`.
- **M3:** `connections` and `pairing_codes`.
- **M4:** `oauth_clients`, `oauth_codes`, and the agent columns on `connections`.

## Decisions

Every question raised during scoping is settled; these are the answers the rest of the spec builds on.

| Area | Decision |
| --- | --- |
| Milestones | M1 database migration, M2 collections, community, and Simple alerts, M3 Home Assistant, M4 AI agents. Each is shippable on its own. |
| Alerts | Chosen per bake at start, with radio options. **Simple** (default): a checkbox to export the bake's steps as an ICS file, generated in the browser. **Fancy:** Home Assistant notifications and Live Activities; shown but disabled with a "Coming soon!" tooltip until M3. In-tab browser alerts as a cheap extra. A live calendar feed and Web Push are parked. |
| Community recipes | Users can publish a personal recipe to the community library. Anyone can browse it and copy a recipe into their own collection, exactly like a default. Only the publisher edits it. The admin can unpublish any recipe. |
| AI agents | A remote MCP server, built for Claude and ChatGPT connectors. Agents use the same `/api/v2` as everyone else, through the MCP tools. |
| Agent auth | OAuth 2.1, with breadsheet as its own authorization server. A signed-in browser approves the agent on a consent page; each agent gets its own revocable, scoped token. The user's key never reaches an agent. |
| Calendars | The agent reads the user's calendar on its own side. Breadsheet never sees or stores it. |
| Recipe import | Agents import recipes (from pasted text, a photo, or a URL) through MCP. Imports are saved as drafts the owner reviews and saves before use. |
| HA integration shape | Custom integration in its own repo (`breadsheet-hass`), distributed via the Home Assistant Marketplace (built-in successor to HACS as of HA 2026.11). Not an add-on. |
| Data flow | HA polls breadsheet (outbound only). No webhooks, no remote access required. |
| Identity | Username (display handle) + generated secret key. No passwords, no recovery in v1. |
| Recipe ownership | Admin-owned defaults visible to all. Personal recipes belong to their user; published ones also appear in the community library. Users copy defaults or community recipes into independent personal recipes. |
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
| API | New `/api/v2`, growing additively by milestone. v1 is reimplemented on Postgres at cutover with identical responses; v1 recipe endpoints retire later, `/api/v1/replacements` stays. |
| API host | `api.breadsheet.com`, an App Engine custom domain with a Google-managed certificate; still App Engine standard. Being same-site with breadsheet.com keeps the session cookie first-party. |
| Cache | App Engine shared memcache (free, best-effort) for idle-poll answers and rate-limit counters. |
| CORS | Credentialed CORS for `https://breadsheet.com` and `https://www.breadsheet.com` only (plus localhost in dev); no wildcard origins. |
| HA panel auth | Integration passes a short-lived token in the panel URL; no reliance on cookies. |
| Existing recipes | Migrated from DynamoDB; Thomas curates the defaults, the rest are archived, not deleted. |
| Backlog | GitHub Projects, one board across all three repos, with a Milestone field. |
| URLs | Defaults use a pure slug (/recipes/country-sourdough). Personal recipes, published or not, append a 6-character lowercase suffix (/recipes/country-sourdough-k7qx2m); the suffix does the lookup, so renames redirect. Bakes use /bakes/\<suffix>. Old recipe URLs (breadsheet.com/\<id>, with any legacy id, timestamp or UUID) redirect to the homepage; no legacy ids are stored. These public URLs are user-facing only; the API keeps using internal ids. |
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

- **Key hashing.** Keys are 128-bit random values from Python's `secrets` module, so they don't need a slow password hash like bcrypt or Argon2 (those exist to protect weak, human-chosen passwords). Store SHA-256 of the key (`hashlib`, standard library), look users up by that hash, and compare with `hmac.compare_digest`. Device tokens (256-bit), OAuth access and refresh tokens, authorization codes, and panel tokens all use the same scheme. The same practice is used for API tokens generally.
- **OAuth (M4).** Authorization code flow with PKCE (`S256` only), exact-match redirect URIs, single-use codes that expire in 60 seconds, access tokens that last 1 hour, and refresh tokens that rotate on every use and expire after 90 days unused. Scopes: `recipes:read`, `recipes:write`, `bakes:read`, `bakes:write`.
- **Pairing codes (M3).** 8 characters from Crockford base32 (no I, L, O, or U), shown as `XXXX-XXXX`. They expire after 10 minutes, work once, and each user has at most one live code; issuing a new one voids the old one.
- **Rate limits.** Per client IP, returning HTTP 429 when exceeded: 10 failed key sign-ins per 15 minutes on `POST /session`, 5 signups per hour on `POST /users`, and (from M3) 5 failed pairing attempts per 15 minutes on `POST /devices`. Counters live in the same cache as idle polls.
- **CSRF.** `SameSite=Lax` cookies, the restricted CORS origin list, and requiring `Content-Type: application/json` on every state-changing request (which forces a CORS preflight) together cover it; no CSRF tokens needed.

**Home Assistant (M3).** Breadsheet shows a short pairing code; the integration's config flow exchanges it for a separate device token tied to the user. The master key never enters HA, and HA access can be revoked from breadsheet.

**AI agents (M4).** The user adds breadsheet's MCP URL as a connector in Claude or ChatGPT. The client starts a standard OAuth flow that lands on breadsheet's consent page (`breadsheet.com/connect`). If the browser isn't signed in, the user opens their key link first. The page names the agent and the scopes it asks for; approving it issues that agent its own token. Agents and HA devices appear together in one connections list, and each can be revoked on its own.

**Connections** is the umbrella for every non-browser client: HA devices (M3) and AI agents (M4) share one table, one list screen, and one revoke action.

**Recipe scopes**

- **Default:** owned by the admin, visible to everyone including incognito, read-only for users. Only the admin can create new default recipes.
- **Personal:** created from scratch or copied from any recipe the user can see (a default, a community recipe, or a shared personal recipe). Copies are fully independent of their source. This is the default for new recipes; there shouldn't be a visible option that indicates otherwise. Anyone with the link can view a personal recipe read-only and copy it; only the owner can edit. A copy becomes the copier's own personal recipe, with its own URL suffix, fully editable.
- **Community:** a personal recipe its owner has published. It's listed in the community library for everyone, including incognito, and anyone can copy it into their own collection, exactly like a default. Only the owner can edit it, and edits show in the community version right away. The owner can unpublish at any time; copies people already made are unaffected. Drafts can't be published, and a recipe must pass validation to be published. The admin key can unpublish any recipe.

**Admin.** Defaults are managed with a separate admin key in server config, not a user role. The same key can unpublish community recipes.

**Groundwork for later.** Store `last_seen_at` per user so abandoned-username reclamation can become a policy rather than a migration.

## Data model

Ten Postgres tables replace every DynamoDB model (`Recipe`, `Step`, and `Replacement`) and add identity, bakes, and agent auth, plus the `events` table from Usage metrics. Tables arrive by milestone (see Milestones). Times are stored in UTC; durations in seconds.

| Table | Key columns | Notes |
| --- | --- | --- |
| `users` | id, username (unique, case-insensitive), key\_hash, created\_at, last\_seen\_at | M2. Store only hashes. |
| `connections` | id, user\_id, kind (ha or agent), oauth\_client\_id (agents only), label, scopes, token\_hash, token\_expires\_at, refresh\_token\_hash, refresh\_expires\_at, created\_at, last\_used\_at, revoked\_at | M3, with the agent columns used from M4. One row per paired HA instance or authorized agent. HA tokens don't expire; agent access tokens last 1 hour and refresh. |
| `pairing_codes` | code, user\_id, expires\_at, used\_at | M3. HA pairing. Short-lived, single use. |
| `oauth_clients` | id, client\_id, name, redirect\_uris, registration\_type (metadata document or dynamic), created\_at | M4. Agent apps such as Claude and ChatGPT, registered automatically when a user first connects one. |
| `oauth_codes` | code\_hash, oauth\_client\_id, user\_id, redirect\_uri, code\_challenge, scopes, expires\_at, used\_at | M4. Authorization codes; 60-second, single use. |
| `recipes` | id, public\_suffix (null for defaults), slug, owner\_id (null = default), source\_recipe\_id, name, author, source, url, difficulty, detail\_level (simple or detailed), is\_draft, published\_at (nullable), archived\_at, timestamps | M1 with v1 columns; the rest in M2. `source_recipe_id` records where a copy came from; no live link. `is_draft` marks agent imports awaiting review. `published_at` set means the recipe is in the community library. |
| `recipe_steps` | id, recipe\_id, position, text, note, wait\_min, wait\_max, active\_seconds (nullable), needs\_presence (nullable) | M1, with the detail columns in M2. Existing steps migrate as simple: `wait_min = wait_max = then_wait`, detail fields null. |
| `bakes` | id, public\_suffix, user\_id, recipe\_id, name\_snapshot, anchor\_type (start or finish), anchor\_time, time\_zone (IANA, e.g. `America/Los_Angeles`), alert\_mode (simple or fancy), status, created\_via (web, ha, or agent), idempotency\_key (nullable, unique per user), started\_at, completed\_at, projected\_end | M2. Status: not\_started, in\_progress, completed. |
| `bake_steps` | id, bake\_id, position, text\_snapshot, wait\_min, wait\_max, wait\_chosen, active\_seconds, needs\_presence, scheduled\_at, completed\_at | M2. Snapshot of the recipe at bake start, so later recipe edits never change a running bake. |
| `replacements` | id, scope, old, new | M1. Convert-text substitutions; unique on (scope, old), matching the DynamoDB hash and range keys. Migrated as is. |

**Recipe detail levels.**

- **Simple:** each step has text, a note, and one wait. Stored as `wait_min = wait_max`, with `active_seconds` and `needs_presence` null. This is the default for new recipes and for everything migrated from DynamoDB.
- **Detailed:** each step can also have a wait range, `active_seconds` (hands-on time, counted from the step's start), and `needs_presence` (you must be home, not just awake).
- `detail_level` only controls which fields the recipe view shows. Switching from detailed back to simple hides the extra fields but doesn't erase them.
- **Unknown is not zero.** When `active_seconds` is null, scheduling assumes 10 minutes of hands-on time at the step's start and marks the schedule as estimated. When `needs_presence` is null, it assumes presence is needed for those hands-on minutes. A step with no range has a fixed wait, so only the whole bake can move.
- **Validation:** `0 ≤ wait_min ≤ wait_max` and `active_seconds ≥ 0`. Hands-on time longer than the step's wait is allowed but flagged, since it overlaps the next step. Drafts can be saved incomplete; a recipe must pass validation before it leaves draft or is published.

**Slugs and suffixes.**

- A slug is generated from the recipe name (lowercase, hyphenated). Default slugs must be unique among defaults; a collision appends `-2`, `-3`, and so on. Default slugs never change once created.
- A public suffix is 6 random characters from `a-z0-9`, checked against existing suffixes in the same table and regenerated on collision. Personal recipes and bakes each get one. Publishing a recipe doesn't change its URL.
- Renaming a personal recipe regenerates its slug and keeps its suffix, so old links still resolve and redirect.
- Copying a recipe creates a new slug from the name and a new suffix.

**Projection rule.** A step's `scheduled_at` is the previous step's completion time (or that step's scheduled time if it isn't checked off yet) plus that previous step's `wait_chosen`. Checking off a step re-projects every later step.

## Bake behavior

A bake is a snapshot of a recipe with a schedule anchored to a start or finish time; it runs until checked off or until its projected end passes.

- **Start.** Choose a recipe, set the anchor (start or finish) and time zone, adjust any step's wait within or outside its range, choose alerts (Simple or Fancy), then start. Steps are copied into `bake_steps`. Draft recipes can't be baked.
- **Alerts.** Every bake has an alert mode, chosen at start and changeable later: Simple (the default) or Fancy. Fancy needs a paired HA instance; until M3 the option is visible but disabled. Only Fancy bakes reach Home Assistant. See Alerts.
- **Idempotent start.** `POST /bakes` accepts an `Idempotency-Key` header. A repeat with the same key returns the original bake instead of creating a second one, so a retrying agent never double-books a loaf.
- **Time zones.** Every bake stores the IANA time zone it was planned in, taken from the browser by default. Responses include each step's time in UTC and in that zone, so "Thursday at 7am" means the same thing to the browser, the agent, the server, and any exported calendar events.
- **Status.** A bake is *not started* from Start until its first step is checked off, *in progress* after that, and *completed* once every step is checked off, it's cancelled, or its projected end passes. Notifications run for both not-started and in-progress bakes.
- **Cancel.** The owner can end a bake at any time; it becomes completed and all notifications stop.
- **Check-off.** Any step can be marked done at any time, including early. All later steps re-project from that moment.
- **Out-of-range waits.** Allowed; the UI flags them. No hard block.
- **Late.** If a step passes its scheduled time unchecked, one reminder fires at +5 minutes (Fancy). After that, silence. The schedule does not shift on its own.
- **Abandonment.** When the latest projected end time passes, the bake becomes completed automatically. No further notifications or input.
- **Concurrency.** Up to 3 active (not started or in progress) bakes per user (soft cap with a clear message). Every notification and calendar event names its bake.
- **Same-minute steps.** Each gets its own notification or calendar event, in step order; notifications are sent 1 to 2 seconds apart.

## API v2

All new functionality lives under `/api/v2` on `api.breadsheet.com`. Each milestone adds its endpoints without changing ones already shipped; what HA needs is frozen before `breadsheet-hass` ships, and what agents need before the MCP server ships. v1 keeps its exact request and response shapes, reimplemented on Postgres. Browser calls authenticate with the session cookie; HA calls send the device token as a bearer header; the MCP service forwards the agent's OAuth access token as a bearer header, and each endpoint checks the token's scopes. Paths use internal ids (`<id>`), never the public URL suffixes or slugs, which exist only for user-facing URLs. "All" in the Caller column means browser, HA, and agents, as each arrives.

| Method and path | Purpose | Caller | Milestone |
| --- | --- | --- | --- |
| `POST /api/v2/users` | Create user; returns key once | Browser | M2 |
| `POST /api/v2/session` | Exchange key for session cookie | Browser | M2 |
| `GET /api/v2/session` | Who am I: the signed-in user, or 401 | Browser | M2 |
| `DELETE /api/v2/session` | Sign out this browser (clears the cookie) | Browser | M2 |
| `GET /api/v2/recipes?q=<text>` | Defaults plus the caller's personal recipes, optionally filtered by name; drafts only for their owner | All | M2 |
| `POST /api/v2/recipes` | Create a personal recipe from scratch | Browser | M2 |
| `POST /api/v2/recipes/<id>/copy` | Copy a recipe (default, community, or shared personal) into a new personal recipe | Browser | M2 |
| `GET /api/v2/recipes/<id>` | Read a recipe: defaults and community recipes for anyone, personal for anyone with the link, drafts for the owner only | All | M2 |
| `PUT/DELETE /api/v2/recipes/<id>` | Edit or delete a personal recipe (owner only); saving with `is_draft: false` takes a draft live | Browser | M2 |
| `POST /api/v2/recipes/<id>/publish` | Publish a personal recipe to the community library (owner only; must pass validation) | Browser | M2 |
| `DELETE /api/v2/recipes/<id>/publish` | Unpublish a recipe (owner only) | Browser | M2 |
| `GET /api/v2/community/recipes?q=<text>` | Browse the community library, optionally filtered by name | All | M2 |
| `GET /api/v2/recipes/by-slug/<slug>` | Resolve a default recipe URL; returns the recipe with its internal id | Browser | M2 |
| `GET /api/v2/recipes/by-suffix/<suffix>` | Resolve a personal recipe URL (anyone with the link, read-only); returns the recipe with its internal id and current slug, so the UI can redirect renamed URLs | Browser | M2 |
| `GET /api/v2/bakes?status=active` | Active (not started or in progress) bakes with full step schedule; `alert=fancy` limits to Fancy bakes | All | M2 (`alert` filter M3) |
| `GET /api/v2/bakes/<id>` | One bake with its full step schedule | All | M2 |
| `GET /api/v2/bakes/by-suffix/<suffix>` | Resolve a bake URL (owner only); returns the bake with its internal id | Browser | M2 |
| `POST /api/v2/bakes` | Start a bake, including its alert mode; honors `Idempotency-Key` | Browser, Agent | M2 |
| `PATCH /api/v2/bakes/<id>` | Change anchor, chosen waits, or alert mode | Browser, Agent | M2 |
| `POST /api/v2/bakes/<id>/cancel` | End a bake early; marks it completed | Browser, Agent | M2 |
| `POST /api/v2/bakes/<id>/steps/<pos>/complete` | Check off a step | All | M2 |
| `POST /api/v2/admin/recipes` | Create a default recipe (admin key) | Admin | M2 |
| `PUT/DELETE /api/v2/admin/recipes/<id>` | Edit or archive a default recipe (admin key); slug never changes | Admin | M2 |
| `DELETE /api/v2/admin/recipes/<id>/publish` | Unpublish any community recipe (admin key) | Admin | M2 |
| `POST /api/v2/pairing-codes` | Issue a short-lived HA pairing code | Browser | M3 |
| `POST /api/v2/devices` | Exchange pairing code for device token | HA | M3 |
| `GET /api/v2/connections` | List the user's HA devices and authorized agents | Browser | M3 |
| `DELETE /api/v2/connections/<id>` | Revoke an HA device or agent | Browser | M3 |
| `POST /api/v2/panel-tokens` | Short-lived token for the HA panel URL | HA | M3 |
| `POST /api/v2/recipes/import` | Create a draft personal recipe from structured input; returns the draft and a review link | Agent | M4 |
| `POST /api/v2/schedules/preview` | Project a recipe's full schedule for an anchor, time zone, and chosen waits, without saving anything. Returns each step's time, hands-on window, and whether it's estimated | Browser, Agent | M4 |

**OAuth endpoints (M4)** (on `api.breadsheet.com`, outside `/api/v2` because their paths are set by the OAuth standards):

| Path | Purpose |
| --- | --- |
| `GET /.well-known/oauth-authorization-server` | Authorization server metadata (endpoints, scopes, PKCE support) |
| `POST /oauth/register` | Dynamic client registration, for clients that don't use a client metadata document |
| `GET /oauth/authorize` | Starts the flow; redirects to the consent page at `breadsheet.com/connect` |
| `POST /oauth/token` | Exchanges a code (with PKCE verifier) for tokens; refreshes tokens |
| `POST /oauth/revoke` | Revokes a token; the connections list calls the same logic |

**Errors.** Every v2 error returns a JSON body with a stable `code` (such as `bake_limit_reached`, `wait_out_of_range`, `recipe_is_draft`, `fancy_requires_ha`, `scope_missing`) and a plain-language `message` that says what to do next, so a client or agent can recover without guessing.

**Polling support (M3).** `GET /api/v2/bakes?status=active&alert=fancy` returns an ETag and a suggested next poll interval. When the user has no active Fancy bakes, the server answers from a cache without querying Postgres, so idle polls never wake the Neon database.

**Cache.** App Engine's shared memcache, the free tier of the bundled memcache service (dedicated memcache is billed per GB-hour and not needed). Capacity is best-effort with no guarantees, which is fine: the cache only holds data that can be rebuilt. It stores the rate-limit counters (from M2) and each user's "no active Fancy bakes" flag (from M3, cleared when a Fancy bake starts or a bake switches to Fancy). A missing entry costs at most one Postgres wake-up or a reset rate-limit count. It requires the `appengine-python-standard` SDK, which pins `urllib3<2`, plus the bundled-services setting in `app.yaml`. Google's docs show both `app_engine_apis: true` and `app_engine_bundled_services: [memcache]`, so confirm which one applies to `python314` when setting it up in item 6.

## Alerts

Each bake picks its alerts when it starts, with two radio options on the Start bake screen. A bake uses one mode at a time; the mode can be changed from the bake view.

**Simple (M2, the default).** Selected by default, with a checkbox beside it: "Export calendar events as ICS". When checked, starting the bake downloads an `.ics` file, built in the browser from the schedule it already has. No server endpoint is involved.

- One event per step, titled with the bake and step (for example "Country Sourdough · Fold #2"), starting at the step's scheduled time, with a reminder at the start.
- Each event lasts for the step's hands-on time (10 minutes when unknown), so a busy calendar shows when you're actually tied up.
- Times are written as UTC instants and the bake records the browser's IANA time zone (`Intl.DateTimeFormat().resolvedOptions().timeZone`). Calendar apps show them in the user's local time, including across a daylight-saving change mid-bake, which a fixed UTC offset would get wrong.
- Each event has a stable `UID` (the bake's suffix plus the step position) and an increasing `SEQUENCE`, so re-importing an updated file can replace events rather than duplicate them in calendar apps that honor UIDs on import.
- Exported events don't update on their own after a check-off or re-projection. The bake view has an "Export again" button that downloads the current schedule for any bake, Simple or Fancy, and the UI says plainly that the export is a snapshot.

**Fancy (M3).** From M2 it appears as a second radio option, disabled, with a "Coming soon!" tooltip on hover (and on focus or tap, for keyboard and touch users). In M3 it becomes selectable: choosing it with a paired HA instance starts a Fancy bake; choosing it without one prompts the user to pair first. It's the full `breadsheet-hass` experience below: phone notifications with a Done button, the late nag, and Live Activities.

**Agents (M4).** An agent with calendar access can also create calendar events itself, which show up instantly. The MCP tools return everything it needs for that.

## HA integration (breadsheet-hass)

Arrives in M3. The integration pulls active Fancy bakes from breadsheet and exposes them as HA entities; a bundled blueprint turns those into notifications and Live Activities. Simple bakes never appear in HA. Nothing ever connects inbound to the user's HA.

**Distribution.** Starting with HA 2026.11, HACS is built into Home Assistant as the Marketplace (Settings → Marketplace). Implications for breadsheet-hass:

- New community repos are still submitted through the `hacs/default` repository.
- The Marketplace installs from GitHub release assets rather than arbitrary scripts, so every version ships as a tagged release with a packaged asset.
- Users accept a one-time warning that Marketplace content is independent and not tested or supported by Home Assistant; only admins can install.
- Check the Marketplace contributor docs (contributors.home-assistant.io/marketplace) for manifest requirements before the first release.

**Setup.** A config flow asks for the pairing code from breadsheet, exchanges it for a device token, and stores the token in the config entry.

**Polling.** Every 60 seconds while a Fancy bake is active; every 15 to 30 minutes otherwise, honoring the server's suggested interval and ETag.

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

## AI agents (MCP)

Arrives in M4. Agents connect through a remote MCP server, built and tested for Claude and ChatGPT connectors. It's a thin layer over `/api/v2`; it holds no data and enforces nothing the API doesn't.

**Hosting.**

- A second App Engine service, `mcp`, in the `breadsheet` repo, using the official MCP Python SDK over Streamable HTTP. It runs in stateless mode, so any instance can answer any request and App Engine can scale it to zero.
- Served at `mcp.breadsheet.com/mcp`, routed to the `mcp` service by `dispatch.yaml`, with a Google-managed certificate like the API. It shares the app's free-tier instance hours with the API.
- It advertises protected-resource metadata (`/.well-known/oauth-protected-resource`) pointing at `api.breadsheet.com` as the authorization server. It validates each access token with the API, then calls `/api/v2` with it.

**Connecting.** The user pastes `https://mcp.breadsheet.com/mcp` into Claude's or ChatGPT's connector settings. The client registers itself (a client metadata document, or dynamic registration as the fallback), sends the user to the consent page, and receives tokens. Each client's current connector requirements get verified against its docs when this is built, since both are still evolving.

**Tools.**

| Tool | What it does | Scope |
| --- | --- | --- |
| `search_recipes` | Find recipes by name, including the community library; returns ids, detail level, and total time | `recipes:read` |
| `get_recipe` | Full recipe with steps, waits, ranges, and hands-on time, with unknowns marked | `recipes:read` |
| `import_recipe` | Turn a recipe the agent has parsed into a draft personal recipe; returns validation results and a review link | `recipes:write` |
| `preview_schedule` | Projected timeline for a recipe, anchor, time zone, and chosen waits; nothing is saved | `recipes:read` |
| `start_bake` | Start a bake from a preview's inputs, with an alert mode and an idempotency key | `bakes:write` |
| `list_active_bakes` | Active bakes with their schedules | `bakes:read` |
| `get_bake` | One bake with its schedule and what's next | `bakes:read` |
| `update_bake` | Change a bake's anchor, chosen waits, or alert mode | `bakes:write` |
| `complete_step` | Check off a step ("I just did the second fold") | `bakes:write` |
| `cancel_bake` | End a bake early | `bakes:write` |

Read-only tools carry MCP's read-only hint, and `cancel_bake` carries the destructive hint, so clients can ask before calling it. Tool descriptions spell out the units (seconds), the time zone handling, and the "unknown is not zero" rule.

**Planning a bake with an agent.** The user says "I want a sourdough loaf on Thursday." The agent finds the recipe, reads the user's calendar on its own side, tries a few anchors and waits with `preview_schedule`, and picks the one that keeps hands-on steps out of meetings and sleep. It confirms with the user, calls `start_bake`, and then either creates calendar events itself or points the user to their alerts.

**Importing a recipe.** The user gives the agent pasted text, a photo of a cookbook page, or a URL. The agent maps it onto the import schema (name, author, source, steps with waits, and optionally ranges and hands-on time), and `import_recipe` saves a draft. The user opens the review link, fixes anything, and saves. Drafts never appear in recipe lists for anyone else, can't be published, and can't be baked until saved.

## UI (breadsheet-ui)

The current schedule table stays nearly untouched; new information goes into separate views so the mobile layout isn't crowded.

- **My recipes (M2):** the signed-in user's collection: personal recipes, plus the defaults to browse and copy. Incognito shows the defaults only.
- **Community library (M2):** browse and search published recipes, each showing its name, publisher's username, and detail level, with a "Make it mine" copy button. Visible to everyone, including incognito.
- **Recipe view (M2):** edit the template. Visited rarely, so it can carry more density. Defaults, community recipes, and other users' shared recipes show a "Make it mine" copy button instead of edit controls.
  - A **Simple / Detailed** toggle per recipe. Simple (the default) shows one Then Wait per step, as today. Detailed reveals each step's wait range (min and max), hands-on time, and a "needs you home" checkbox.
  - A **Publish to community** control on the user's own recipes, with Unpublish once published. Publishing is blocked, with the validation messages shown, until the recipe passes validation.
  - Imported drafts (M4) open here with a banner ("Imported by your assistant. Review and save.") and inline validation; Save takes the draft live.
- **Plan view (M2):** today's screen. The Then Wait input stays as is, with the range as a small caption beneath it (for example "60–90"), turning amber when the chosen value is outside the range. Adds a Start bake button.
- **Start bake (M2):** anchor and time zone confirmation, then the alert options as two radio buttons.
  - **Simple** is selected by default and deliberately plain-jane: default system font, thin gray border, no color, no icon. Beside it, the "Export calendar events as ICS" checkbox.
  - **Fancy** gets a little sparkle: a ✨ next to the title and a soft gradient border with a slow shimmer, a few twinkles on hover. In M2 it's disabled, shown dimmed and without animation, with a "Coming soon!" tooltip on hover, focus, or tap. In M3 it's enabled, and choosing it without a paired HA instance leads to the pairing flow. All animation stops under `prefers-reduced-motion`.
- **Bake view (M2):** the mid-bake phone screen. Current step, next step with countdown, a large Done button, and the remaining timeline. No edit fields. An "Export again" button for the current schedule as ICS, and the alert mode with a way to change it. In-tab browser notifications while it's open.
- **Identity flows:** pick username, save-your-key screen (copy, QR, link), and link-another-device (M2); pair Home Assistant (pairing code) and a connections list with revoke (M3, with agents added to the same list in M4).
- **Agent consent (`/connect`, M4):** "Claude wants to read your recipes and manage your bakes." Lists the requested scopes in plain words, with Approve and Deny. Not signed in: prompt for the key link first, then come back.
- **Active bakes list (M2):** up to three, each linking to its bake view.

Mock-ups of the plan, start bake, and bake views come before implementation, so layout can be judged on real screens.

## Infrastructure and migration

The app stays on App Engine's free tier; the database moves from DynamoDB to a free Neon Postgres project in a US West region. Steps 1 through 8 are M1; step 9 is M4.

1. Create the Neon project and a dev branch; add the connection string as an App Engine secret.
2. Map `api.breadsheet.com` to the App Engine app (CNAME in Cloudflare, Google-managed certificate). Turn off Cloudflare's "Always Use HTTPS" for that hostname, or keep the record DNS-only, so certificate validation and renewal can reach App Engine. Point `VITE_BACKEND_URL` at it, switch CORS to the credentialed allow-list, and send `credentials: 'include'` on UI fetches.
3. Replace PynamoDB with SQLAlchemy and Alembic for every model, replacements included, matching the greeting-cards stack. Create only the M1 tables (see Milestones); later milestones add theirs as Alembic migrations. Reimplement the v1 endpoints on Postgres with identical responses and cover them with tests before cutover. Remove PynamoDB, boto3, and moto from requirements.
4. Write a one-time migration script: export DynamoDB recipes and replacements, load into Postgres, set `wait_min = wait_max = then_wait`.
5. Thomas reviews migrated recipes and marks which become defaults; the rest get `archived_at`, not deleted.
6. Verify row counts and spot-check recipes against DynamoDB before cutting over. For replacements, confirm `/api/v1/replacements` responses and convert-text output are identical before and after. Keep the DynamoDB tables until v2 has run cleanly for a while, then delete them and remove the AWS credentials from config.
7. Back up Postgres weekly: a scheduled GitHub Action runs `pg_dump` and uploads the dump to a private Cloud Storage bucket (inside the free tier), keeping the last 12. Not GitHub artifacts, since they're visible to anyone with access to the repo. Test a restore into a Neon branch once.
8. Update `CLAUDE.md`: React is the only frontend (Jinja/WTForms long retired), Postgres replaces DynamoDB, the three-repo layout, and the milestone plan.
9. Add the `mcp` App Engine service: its own `app.yaml` in an `mcp/` directory of the `breadsheet` repo, a `dispatch.yaml` rule sending `mcp.breadsheet.com/*` to it, and the `mcp.breadsheet.com` custom domain (same Cloudflare caveat as step 2).

Neon's free compute suspends when idle, so the adaptive polling and cached idle responses in the API section are what keep it free once HA arrives in M3.

## Usage metrics

Two layers, neither invasive: cookieless traffic analytics for visits, and first-party product events in breadsheet's own Postgres for what people actually do.

**Traffic.** Hosted GoatCounter (goatcounter.com), with periodic CSV exports so history is never at the mercy of retention limits: visits, pages, referrers, countries, devices. No cookies, no consent banner, no cross-site tracking. Added to the current site early, so there's a baseline before Second Rise launches.

GoatCounter site: `brystmar.goatcounter.com`. Add this to `index.html` in breadsheet-ui (item 1c):

```html
<script data-goatcounter="https://brystmar.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
```

The script counts the initial page load only. Because React route changes don't reload the page, the router must also call `window.goatcounter.count()` on each navigation, guarded in case the script is blocked or hasn't loaded.

**Product events (M2).** An `events` table: event type, timestamp, pseudonymous user id, and related recipe or bake id, plus client (web, HA, or agent, with the agent's client name). No IP addresses, user agents, or free text. Much of it can also be derived from existing tables.

| Metric | Question it answers |
| --- | --- |
| Weekly active bakers | Is anyone using it, and is it growing? |
| Bakes started vs. finished (every step checked off) | Do people finish what they start? Derived from `bake_steps`, since cancelled and expired bakes are also `completed`. |
| Steps checked off on time, late, or never | Are the alerts working? |
| Simple vs. Fancy bakes, and ICS exports | Which alert path do people pick, and do Simple users actually export? |
| Share of bakes with HA paired | Is the integration the reason people come back? |
| Recipes published, and copies of community recipes | Is the community library pulling its weight? |
| Bakes started by agents, and recipes imported | Are people actually letting their assistant do the planning? |
| Share of recipes in detailed mode | Is anyone filling in hands-on time? |
| Most-copied default and community recipes | Which recipes are worth curating? |
| Chosen waits outside the step range | Are the recipe ranges realistic? |
| Bakers returning within 30 days | Retention |

A short privacy page states exactly what's collected and what isn't.

## Backlog

Second Rise breaks into seven epics across four milestones, roughly in build order; each row below becomes one GitHub issue on the shared Projects board.

| # | Issue | Repo | Epic | Milestone |
| --- | --- | --- | --- | --- |
| 1a | Upgrade Python (latest App Engine-supported runtime) and backend dependencies; update CLAUDE.md for React frontend and planned Postgres move | breadsheet | Foundation | M1 |
| 1b | Upgrade React, Vite, and frontend dependencies to current stable; update UI docs | breadsheet-ui | Foundation | M1 |
| 1c | Add hosted GoatCounter to the current site for a pre-launch baseline, including SPA route tracking | breadsheet-ui | Foundation | M1 |
| 1d | Serve the API at `api.breadsheet.com` (App Engine custom domain, managed cert); credentialed CORS allow-list; point the UI at it | breadsheet, breadsheet-ui | Foundation | M1 |
| 2 | Create Neon project, dev branch, App Engine secret | breadsheet | Foundation | M1 |
| 3 | Replace PynamoDB with SQLAlchemy + Alembic for all models (incl. replacements); initial schema with the M1 tables only; v1 endpoints on Postgres with identical responses; remove PynamoDB and boto3 | breadsheet | Foundation | M1 |
| 4 | DynamoDB to Postgres migration script (recipes and replacements) with verification; convert-text behavior unchanged | breadsheet | Foundation | M1 |
| 5 | Curate default recipes; archive the rest | breadsheet | Foundation | M1 |
| 5b | Weekly `pg_dump` backups to a private Cloud Storage bucket; one test restore | breadsheet | Foundation | M1 |
| 6 | Users, key hashing, session cookie, key-link sign-in, sign-in and signup rate limits; set up shared memcache here, since the rate limits need it first | breadsheet | Identity | M2 |
| 8 | Admin key for managing defaults and unpublishing community recipes | breadsheet | Identity | M2 |
| 9 | Signup, save-your-key, link-device screens | breadsheet-ui | Identity | M2 |
| 11 | Recipe scopes, copy-to-personal, slugs and suffixes, URL lookup endpoints | breadsheet | Recipes and bakes | M2 |
| 11b | Community recipes: publish and unpublish, community library endpoint, copy from community, admin unpublish | breadsheet | Recipes and bakes | M2 |
| 12 | Recipe detail levels in the API: wait ranges, hands-on time, needs-presence, validation, the "unknown is not zero" defaults, drafts | breadsheet | Recipes and bakes | M2 |
| 13 | Bakes: start, snapshot, projection, check-off, cancel, auto-complete, time zones, alert mode, idempotent start | breadsheet | Recipes and bakes | M2 |
| 13c | ICS export built in the browser: at bake start (Simple checkbox) and "Export again" from the bake view; UTC times, stable UIDs, increasing SEQUENCE | breadsheet-ui | Recipes and bakes | M2 |
| 14 | Freeze the M2 `/api/v2` contract (including error codes) and document it; later milestones only add endpoints | breadsheet | Recipes and bakes | M2 |
| 16 | Mock up plan, start bake, and bake views | breadsheet-ui | UI | M2 |
| 17 | Recipe view with the Simple/Detailed toggle, range and hands-on editing, "Make it mine", publish/unpublish, and the draft review banner | breadsheet-ui | UI | M2 |
| 17b | My recipes and community library screens: browse, search, copy | breadsheet-ui | UI | M2 |
| 18 | Plan view range caption and Start bake | breadsheet-ui | UI | M2 |
| 19 | Bake view and active bakes list | breadsheet-ui | UI | M2 |
| 20 | In-tab browser notifications | breadsheet-ui | UI | M2 |
| 20b | Start bake alert options: plain Simple radio (default) with the ICS checkbox; sparkly Fancy radio, disabled with a "Coming soon!" tooltip | breadsheet-ui | UI | M2 |
| 29 | Product events table, metrics queries, and privacy page | breadsheet | Metrics | M2 |
| 7 | Pairing codes, connections table (HA device tokens), connections list, revoke, pairing rate limits | breadsheet | Identity | M3 |
| 10 | Pair HA and connections list screens (HA now, agents in M4) | breadsheet-ui | Identity | M3 |
| 15 | Idle-poll cache (using the memcache from item 6), suggested poll interval, and the `alert=fancy` filter | breadsheet | Recipes and bakes | M3 |
| 21 | Repo scaffold, Marketplace manifest, release-asset packaging, config flow with pairing | breadsheet-hass | HA integration | M3 |
| 22 | Adaptive polling coordinator | breadsheet-hass | HA integration | M3 |
| 23 | Calendar entity and bake sensors | breadsheet-hass | HA integration | M3 |
| 24 | `complete_step` action | breadsheet-hass | HA integration | M3 |
| 25 | Sidebar panel with panel tokens | breadsheet-hass | HA integration | M3 |
| 26 | Notification blueprint (lead time, Done action, late nag) | breadsheet-hass | HA integration | M3 |
| 27 | Live Activities in blueprint (opt-in) | breadsheet-hass | HA integration | M3 |
| 28 | README and Marketplace submission | breadsheet-hass | HA integration | M3 |
| 28b | Enable the Fancy option at bake start; route to HA pairing when no HA is paired | breadsheet-ui | UI | M3 |
| 13b | Schedule preview endpoint (no save), with hands-on windows and estimated flags | breadsheet | Recipes and bakes | M4 |
| 30 | OAuth authorization server: metadata, client metadata documents and dynamic registration, authorize, token with PKCE, refresh rotation, revoke, scopes | breadsheet | AI agents | M4 |
| 31 | Consent screen at `/connect` | breadsheet-ui | AI agents | M4 |
| 32 | `mcp` App Engine service: Streamable HTTP (stateless), protected-resource metadata, token validation, `dispatch.yaml`, `mcp.breadsheet.com` | breadsheet | AI agents | M4 |
| 33 | MCP tools: search, get, preview, start, list, get bake, update, complete, cancel, with hints and agent-friendly descriptions | breadsheet | AI agents | M4 |
| 34 | `import_recipe`: import schema, validation, draft creation, review link | breadsheet | AI agents | M4 |
| 35 | End-to-end tests with Claude and ChatGPT connectors (plan a bake from a calendar, import a recipe from a photo); connector setup guide | breadsheet | AI agents | M4 |

**Parked for later**

- Live calendar feed: a private per-user ICS subscription URL that updates as bakes change, with rotate and revoke. Deferred when Simple alerts became a per-bake export.
- Community moderation beyond admin unpublish: a report button and a review queue, if the library sees abuse.
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