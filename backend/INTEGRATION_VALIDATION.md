Integration Validation Checklist

Prereqs:
- PostgreSQL from platform_database is running and listening on port 5001 (preview default). For local dev use port 5002 on 127.0.0.1.
  - Quick start: from nutrition-connect-platform-172674-172683/platform_database run: ./startup.sh
  - Verify (preview): pg_isready -h platform_database -p 5001 -U nc_app
  - Verify (local): pg_isready -h 127.0.0.1 -p 5002 -U nc_app

1) Backend connects to DB (default preview: platform_database:5001) and runs migrations
- cd nutrition-connect-platform-172674-172685/backend
- cp .env.example .env (fill Supabase fields)
- python -m venv .venv && . .venv/bin/activate
- pip install --upgrade pip && pip install -r requirements.txt
- python manage.py migrate
Expected: migrations complete without error.

2) Verify /health (or /api/health) returns 200
- python manage.py runserver 0.0.0.0:8000
- curl -i http://localhost:8000/health/
Expected: HTTP/1.1 200 with JSON {"message":"Server is up!"}

Tip (DB not available): If platform_database is not reachable, use a no-DB server for health checks:
- python manage.py runserver_nodb 0.0.0.0:8000
- curl -i http://localhost:8000/health/
- curl -i http://localhost:8000/api/health/

3) Validate Supabase Auth flow enabled and JWKS reachable
- Ensure in backend .env: USE_SUPABASE_AUTH=true
- Ensure SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_JWKS_URL are set
- curl -I "$SUPABASE_JWKS_URL"
Expected: 200 OK and JSON keys

4) Attempt login flow
Option A (Supabase): Use frontend login with your Supabase email/password; session should be set in localStorage via AuthContext.
Option B (Fallback JWT): If USE_SUPABASE_AUTH=false, or for API tests:
- Create Django user: python manage.py createsuperuser
- Obtain tokens: curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"<user>","password":"<pass>"}'
Expected: 200 with access/refresh and role.

5) Exercise CRUD endpoint (requires auth)
- TOKEN=<access token from step 4>
- curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/foods/
Expected: 200 (list)
- curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"Apple","calories":52}' http://localhost:8000/api/foods/
Expected: 201 with created object

6) WebSocket chat connectivity
- Channels runs under ASGI. Start server: daphne -b 0.0.0.0 -p 8001 config.asgi:application
- Create conversation and JWT as in tests or via admin.
- Connect to ws://localhost:8001/ws/chat/<conversation_id>/?token=<ACCESS>
- Send {"content":"hello"} and expect broadcast with same content.

7) Report failures
- DB connection issues: confirm DB_* env vars (port 5002), ensure platform_database is up
- JWKS fetch issues: check SUPABASE_JWKS_URL and network egress
- 401s: ensure Authorization header bearer token present
- WS issues: run ASGI server (daphne) instead of manage.py runserver for websockets in some environments
