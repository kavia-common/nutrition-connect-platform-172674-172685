# Backend (Django) - Environment Variables

Configure a `.env` file based on `.env.example`. Required variables to enable Supabase Auth:

- USE_SUPABASE_AUTH=true
- SUPABASE_URL=https://<your-project>.supabase.co
- SUPABASE_ANON_KEY=<TO_BE_FILLED_BY_USER_OR_DEPLOYER>
- SUPABASE_JWKS_URL=https://<your-project>.supabase.co/auth/v1/.well-known/jwks.json

Storage (kept disabled):
- SUPABASE_STORAGE_ENABLED=false
- SUPABASE_STORAGE_BUCKET=uploads

Do not include service role key in source control:
- SUPABASE_SERVICE_ROLE_KEY=

## Install and Run

- python -m venv .venv && . .venv/bin/activate
- pip install --upgrade pip
- pip install -r requirements.txt
- cp .env.example .env
- Preview default: DB is available at service `platform_database:5001` (already reflected in .env.example)
  - For local dev, set DB_HOST=127.0.0.1 and DB_PORT=5002 in .env
- python manage.py migrate
- python manage.py runserver 0.0.0.0:8000
- curl -i http://localhost:8000/health/  # expect 200 and {"message":"Server is up!"}
- curl -i http://localhost:8000/api/health/  # also available under /api

## Automated Integration Validation

A helper script is available to validate DB connectivity/migrations, API health, Supabase JWKS reachability, auth, CRUD, and WebSocket connectivity.

Quickstart:
- python -m venv .venv && . .venv/bin/activate
- pip install --upgrade pip && pip install -r requirements.txt
- export DB_HOST=127.0.0.1 DB_PORT=5002 DB_NAME=nc_app DB_USER=nc_app DB_PASSWORD=nc_app
- export USE_SUPABASE_AUTH=true
- export SUPABASE_JWKS_URL=https://<your-project>.supabase.co/auth/v1/.well-known/jwks.json
- python utils/integration_validate.py

The script will:
- run migrations (step 1),
- start runserver and check /api/health (step 2),
- check JWKS (step 3 - non-blocking),
- seed users and perform JWT login and basic Foods CRUD (steps 4-5),
- start Daphne and test WebSocket chat echo (step 6),
- print a summary and targeted suggestions (step 7).

Exit code is non-zero if any checks fail.
