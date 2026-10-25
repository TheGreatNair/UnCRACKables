# TurtleWay demo quick start

Expo field reporting app and separate authority dashboard backed by the shared FastAPI API. Field reports remain on-device until a signed-in user syncs them; the API assigns ownership and enforces reviewer roles and sector scopes. The same API serves the regional TurtleGuard fishing-activity assessment to mobile and web clients.

## One-time setup

1. If root `.env` does not exist, copy `.env.example` to `.env`; otherwise add only missing `EXPO_PUBLIC_` entries without overwriting existing values. Set the Supabase **project URL** and **publishable key**. These are public client configuration values; never put a database password, service-role key, or signing secret in the Expo app.
2. If `dashboard/.env` does not exist, copy `dashboard/.env.example` to it; otherwise add only missing `VITE_` entries without overwriting existing values. Use the same Supabase URL and publishable key. The default dashboard API URL `/api` is proxied to `http://127.0.0.1:8000` in development.
3. Reuse the existing Python virtual environment. From `backend` run:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements-dev.txt
   ```

   Do not copy example files over an existing `.env` or point at the saved SQLite files.
4. Configure the API for a local/test database and `SUPABASE_URL` in `backend/.env`. Protected API calls require schema revision `0003_authz_audit`; this project setup does **not** apply it. Until that migration is separately approved/applied to the intended database, cloud API requests may fail.

The regional risk card reads `GET /risk/fishing-activity`, which calculates its result from bundled current/reference Global Fishing Watch (GFW) JSON snapshots. It is public and read-only. The snapshot is for demonstration; refresh the files on the backend with the original fetch scripts and a private `GFW_TOKEN` before operational use. Keep that token on the backend. The indicator uses AIS-derived apparent fishing effort, applies to the shared offshore zone rather than a specific beach, and does not prove illegal activity.

## Start the components

Open three PowerShell terminals at the repository root.

**Backend** (from `backend`, so `backend/.env` loads):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Check `http://127.0.0.1:8000/health`. Startup does not run migrations. Use an isolated local database for demos; do not point the app at production unless its schema, runtime role, and Auth verifier are ready.

**Authority dashboard** (from repository root):

```powershell
npm --prefix dashboard install
npm run dashboard
```

Open `http://localhost:5173`. Sign in with a provisioned Supabase account to use the API. If Auth/API setup is unavailable, choose **Open local sample demo**; those fictional reports and review edits stay in browser memory and are never sent to the API.

**Mobile app** (from repository root):

```powershell
npm install
npx expo start
```

For a physical phone, set `EXPO_PUBLIC_API_URL` in the root `.env` to the computer's LAN address, such as `http://192.168.x.x:8000`, then restart Expo. `127.0.0.1` from a phone points to the phone itself. Sign in or create a field account; reports made offline stay pending and sync when connectivity and authentication return. GPS permission is requested only after the user chooses the GPS option.

## Judge walkthrough

1. Open the dashboard sample mode to show report listing, sector/status filters, GPS coordinates, details, summary counts, and the mock review transition. The banner marks sample data as fictional and edits as local.
2. Open the Expo app, sign in when Supabase Auth is configured, create a coastal-sector or GPS report, and inspect it in History. The app saves locally before attempting sync.
3. With a valid Supabase user and current API schema, the dashboard lists reports visible under that account's server-side role/scope. Review succeeds only for an authorized reviewer/admin; a reporter account is denied by the server.
4. The mobile and authority dashboard risk cards load the same regional assessment from the API and display its source date and snapshot limitations.
5. If Auth, migration, or hosting is unavailable, use the dashboard sample mode and demonstrate offline save/history on mobile. Do not describe local sample content as cloud-synced.

## Security and migration boundary

The mobile app uses Supabase Auth email/password sign-in, session restoration, auto-refresh, and chunked Expo SecureStore persistence on native devices. It sends only the signed access token to protected API endpoints. Pending reports are bound locally to the first authenticated account that attempts delivery; another account on that device will not sync them. Server idempotency and ownership checks remain authoritative. No database credential, service-role key, or JWT signing secret is bundled.

Migration `0003_authz_audit` is additive: nullable review notes, role and reviewer-scope tables, audit events, and indexes. It preserves report rows, but legacy rows with no owner remain invisible to reporters. Its downgrade refuses to remove non-empty security or review data. **Recommendation:** take and verify a Supabase backup, review the exact migration and runtime-role grants, then apply only after explicit approval. It remains unapplied by this work.

**Supabase-specific migration hardening:** migration 0003 now revokes all table privileges for `anon` and `authenticated` on `public.reports`, `user_roles`, `reviewer_scopes`, and `audit_events`. The app uses Supabase Auth only; report data goes through FastAPI using its separate PostgreSQL login role. This blocks direct client/PostgREST table access when the migration is applied. RLS is not enabled on these tables; if direct Data API access is ever required, add policies and test them before granting access. Supabase documents that both grants and RLS govern Data API access, and existing projects may grant new public tables to `anon`/`authenticated` by default. Review effective grants before applying, and do not assume FastAPI role checks protect direct PostgREST access. See Supabase's [Data API security guidance](https://supabase.com/docs/guides/api/securing-your-api) and [RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security).

Supabase Auth URL/key, an Auth account, asymmetric JWT signing, an assigned reviewer/admin role and sector, current production schema, and a production API host are external setup requirements. No cloud setting, privileged account, schema, or deployment was changed here.

## Checks

From `backend`: `python -m pytest -q` and `.\.venv\Scripts\ruff.exe check app tests alembic`.

From repository root: `npx tsc --noEmit`, `npm run test:location`, and `npm run dashboard:build`.
