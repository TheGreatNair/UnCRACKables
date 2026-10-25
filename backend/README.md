# TurtleWay API

FastAPI backend for authenticated turtle-conservation reporting. The existing `turtleway.db` is a preserved import source; local development uses the separate `turtleway-dev.db` unless `DATABASE_URL` points elsewhere.

## Local development

From this directory, create/activate the virtual environment only if needed, install dependencies, and start the compatibility entry point:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

`app/config.py` loads `.env` relative to the process working directory. Start commands from `backend` so `backend/.env` is selected. The API still permits local SQLite development, but protected report routes require a valid Supabase Auth access token. Without `SUPABASE_URL`, token verification fails closed with HTTP 503. Health remains public for platform probes.

The root `.env.example` contains placeholders only. Copy it to `backend/.env` only when setting up a new local environment; do not overwrite an existing `.env` or either SQLite file.

## Supabase Auth token verification

The API verifies Supabase Auth access tokens using the project's public JWKS endpoint. It verifies the signature, a fixed asymmetric algorithm allowlist (`ES256`, `RS256`), issuer (`SUPABASE_URL/auth/v1`), audience (`SUPABASE_JWT_AUDIENCE`, normally `authenticated`), required `exp`, `iss`, `sub`, and `aud` claims, and UUID subject format. JWKS responses are cached briefly. Legacy HS256 tokens are not accepted; configure an asymmetric signing key in Supabase Auth before using this verifier. The backend does not use a service-role key, JWT signing secret, or unverified role claims.

Authenticated users receive only the `reporter` capability by default. Reviewer and administrator roles live in PostgreSQL and are looked up for every request. The API does not trust role, reporter identity, reviewer identity, review status, or review timestamps supplied by the client.

### First administrator bootstrap

There is deliberately no API endpoint that can create an administrator. After the schema migration is approved and applied, an authorized project owner should identify the intended user's UUID in Supabase Auth, then add the initial role and its audit event together in the Supabase SQL Editor. Replace placeholders locally; do not paste credentials or tokens into SQL.

```sql
BEGIN;

INSERT INTO public.user_roles (subject, role, granted_by)
VALUES ('<AUTH_USER_UUID>', 'administrator', 'bootstrap:operator');

INSERT INTO public.audit_events
    (id, actor_subject, action, resource_type, resource_id, metadata)
VALUES
    ('<UNIQUE_EVENT_UUID>', 'bootstrap:operator', 'administrator.bootstrap',
     'user_role', '<AUTH_USER_UUID>', '{"role":"administrator"}'::json);

COMMIT;
```

Use a fresh UUID for `<UNIQUE_EVENT_UUID>`. The bootstrap operator should be recorded in the organization's own access/change process. This initial role insertion is a manual DBA action; later reviewer-scope changes are audited by the API. No administrator role can be granted or revoked through the API.

## API authorization

All report operations except `/health` and the public, read-only `/risk/fishing-activity` regional indicator require `Authorization: Bearer <Supabase access token>`.

| Endpoint | Reporter | Reviewer | Administrator |
|---|---|---|---|
| `GET /health` | Public database readiness result; no configuration details | Same | Same |
| `GET /risk/fishing-activity` | Public read-only regional risk summary from bundled GFW snapshots | Same | Same |
| `POST /reports` | Create for authenticated owner; retries are idempotent by report ID, payload, and owner | Same | Same |
| `GET /reports` | Own reports only | Own reports plus assigned sectors | All reports |
| `GET /reports/{id}` | Own report only | Own or assigned-sector report | Any report |
| `PATCH /reports/{id}/review` | Denied | Assigned-sector reports only | Any report |
| `GET /admin/reviewers` | Denied | Denied | List reviewer scopes; access is audited |
| `PUT /admin/reviewers/{subject}/sectors/{sector}` | Denied | Denied | Grant a reviewer sector scope; cannot grant administrator |
| `DELETE /admin/reviewers/{subject}/sectors/{sector}` | Denied | Denied | Revoke scope; last scope removes reviewer role |
| `GET /admin/audit` | Denied | Denied | Paginated audit events; access is itself audited |

Newly authenticated users have reporter access without a database role row. Reports with no `reporter_subject` (for example, pre-ownership legacy imports) are not visible to reporters; reviewers see only reports in assigned sectors, while administrators can access all reports. There is no report deletion endpoint.

Review transitions are `not_reviewed -> in_review|rejected` and `in_review -> verified|rejected`. Terminal states cannot be changed through this API. Review notes are visible only to reviewers and administrators. A verified token's `sub` is recorded as reviewer identity; review status, notes, timestamp, and reviewer cannot be set by report creation clients.

Successful review changes, reviewer scope grants/revocations, reviewer-scope listing, audit-log reads, and authenticated role denials create audit rows. Authentication failures are logged with safe fixed messages and never include bearer tokens. Audit rows have no mutation endpoint and the documented application database role receives no `UPDATE`/`DELETE` permission on `audit_events`; this is not tamper-proof against a database owner or privileged operator.

Errors use JSON `detail` objects with stable `code` and non-sensitive `message` fields. Missing/expired/invalid tokens return 401; missing verifier configuration or unavailable JWKS returns 503; authenticated role denials return 403; inaccessible or unknown reports return 404. Report ID conflicts and invalid review transitions return 409. Invalid payloads return 422 and bodies over `MAX_REQUEST_BYTES` return 413.

## Database and migration procedure

The current database revision is `0002_report_location`. Revision `0003_authz_audit` adds nullable `reports.review_notes`, role and sector-scope tables, audit events, and indexes. It does not rewrite or delete existing reports; existing report ownership remains `NULL`. Downgrade refuses to drop role/scope/audit data or non-empty review notes.

Migrations are never applied at application startup or by the Render blueprint. Back up Supabase first, review the migration, and apply it manually from `backend` only after approval:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe current
```

Use a migration-owner connection for Alembic. For runtime, provision a separate least-privilege Supabase database role and use its Session Pooler connection URL. Production configuration rejects SQLite and the `postgres` administrator role. The runtime role needs `SELECT` on `alembic_version`, `SELECT/INSERT/UPDATE` on `reports`, `SELECT/INSERT/DELETE` on `user_roles` and `reviewer_scopes`, and `SELECT/INSERT` on `audit_events`; it must not own the tables or have `UPDATE/DELETE` on audit events. Grant only schema `USAGE` plus these table privileges. Do not put SQL credentials in commands, logs, the Expo bundle, or source control.

The previous SQLite importer remains a separate manual operation and is not run by this API, migrations, or deployment configuration. No import is required for this security migration.

**Supabase Data API protection:** migration `0003_authz_audit` revokes all `anon` and `authenticated` table privileges from reports, roles, scopes, and audit tables. The app accesses data only through FastAPI, using a separate PostgreSQL login role. RLS is not enabled; if direct Data API access is later needed, add and test explicit policies before granting privileges. Review the project's effective grants before applying. Supabase documents that grants and RLS govern Data API access and existing projects may grant new public tables by default: [Data API security](https://supabase.com/docs/guides/api/securing-your-api), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).

## Configuration

Set the following in `backend/.env` for local development or in the hosting provider's secret environment configuration:

- `DATABASE_URL`: PostgreSQL Session Pooler URL for Supabase. Use the dedicated runtime database role, not `postgres`; URL-encode reserved characters in the password.
- `SUPABASE_URL`: project base URL, not the database host.
- `SUPABASE_JWT_AUDIENCE`: normally `authenticated`.
- `APP_ENV`: `production` in the hosted service; production requires PostgreSQL, HTTPS Supabase URL, and explicit HTTPS `CORS_ORIGINS`.
- `CORS_ORIGINS`: JSON array of exact dashboard web origins. Do not use `*` in production.
- `MAX_PAGE_SIZE`, `MAX_REQUEST_BYTES`, and `LOG_LEVEL`: bounded request settings.

Environment files, databases, logs, private keys, and virtual environments are ignored by Git. Keep actual credentials out of `.env.example` and all tracked files.

## Tests

From `backend`:

```powershell
python -m pytest -q
.\.venv\Scripts\ruff.exe check app tests alembic
```

Tests use isolated temporary SQLite databases and locally generated/mock JWT signing keys. They do not connect to Supabase, alter its schema, or use either preserved SQLite database. A successful test run proves the verifier's local behavior, not that the configured Supabase project currently serves an asymmetric JWKS key; verify that separately with a real user access token before deployment.

## Deployment preparation

`../render.yaml` describes a Python web service but has auto-deploy turned off and declares secrets as dashboard-supplied values. It creates nothing until someone explicitly imports/applies the blueprint. Production startup refuses SQLite, missing Supabase Auth configuration, insecure CORS, and the `postgres` administrator database role. Render must provide HTTPS; set the `/health` check and configure secret values in the service dashboard.

Before deploying:

1. Review and apply the `0003_authz_audit` migration after approval; verify the resulting revision.
2. Provision and test the least-privilege database role, asymmetric Supabase Auth signing key, `SUPABASE_URL`, HTTPS CORS origins, and the first audited administrator bootstrap.
3. Run backend tests and obtain an actual Supabase Auth user token to verify JWKS token acceptance, expiry rejection, and role behavior.
4. Deploy the API over HTTPS only after authentication and access-control checks pass. Back up Supabase before migrations and retain a tested restore path.
5. Only then set Expo's `EXPO_PUBLIC_API_URL` to the deployed HTTPS API origin.

### Expo client integration

The Expo app already uses Supabase Auth, stores native sessions in SecureStore, and submits queued reports with bearer access tokens. It retries once after token refresh and leaves unsent reports on-device after API failures. On each successful sync pass it also reads the authenticated user's server reports so authority review statuses appear in mobile history. Do not place the database URL, service-role key, GFW token, or signing secret in Expo; only the Supabase project URL and publishable key belong in the mobile auth client.

The authority dashboard is in `../dashboard` and calls the protected reviewer/admin endpoints using the signed-in user's Supabase access token. The mobile app and dashboard also read the public `/risk/fishing-activity` summary. Its inputs are the demonstration snapshots under `app/data`; the route calculates the summary at request time and includes its source date and limitations. Do not treat the bundled snapshot as live data. The legacy GFW fetch scripts remain in `../UnCRACKables-main/backend`; execute them only on the backend host with its private `GFW_TOKEN`, then replace the bundled snapshots after reviewing the downloaded files.

## Remaining security gaps

- No distributed request-rate limiter is bundled; configure rate limits at the HTTPS hosting edge before public access. The app enforces a body-size limit and bounded pagination.
- Role and audit records are protected by application access rules and the least-privilege runtime role, but a database owner can still alter them. The audit log is not tamper-proof.
- Supabase access tokens remain usable until expiry if a session is revoked; immediate revocation/session introspection is not implemented.
- Real Supabase JWKS verification and deployment have not been performed by the automated suite.
