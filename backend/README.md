# Backend (Django) - Environment Variables

Configure a `.env` file based on `.env.example`. Required variables to enable Supabase Auth:

- USE_SUPABASE_AUTH=true
- SUPABASE_URL=https://nznsixbvloaorucujewu.supabase.co
- SUPABASE_ANON_KEY=<TO_BE_FILLED_BY_USER_OR_DEPLOYER>
- SUPABASE_JWKS_URL=https://nznsixbvloaorucujewu.supabase.co/auth/v1/.well-known/jwks.json

Storage (kept disabled):
- SUPABASE_STORAGE_ENABLED=false
- SUPABASE_STORAGE_BUCKET=uploads

Do not include service role key in source control:
- SUPABASE_SERVICE_ROLE_KEY=
