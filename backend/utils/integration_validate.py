#!/usr/bin/env python3
"""
Automated integration validator for the backend.

Checks performed:
1) DB connectivity and migrations (PostgreSQL on port 5002 by default).
2) API health at /api/health/.
3) Supabase JWKS URL reachability if USE_SUPABASE_AUTH=true.
4) Auth flow:
   - Fallback JWT login via /api/auth/login (creates users if needed).
5) CRUD: GET /api/foods/ and POST a minimal Food entity.
6) WebSocket connectivity via Channels (Daphne) to /ws/chat/<id>/?token=...
7) Report failures and targeted fixes.

Usage:
  python utils/integration_validate.py

Environment variables honored:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
  USE_SUPABASE_AUTH, SUPABASE_JWKS_URL
  BIND_HOST (default 127.0.0.1)
  HTTP_PORT (default 8000)
  WS_PORT (default 8001)

Note: This script will spawn background dev servers (runserver, daphne) and terminate them.
"""
import os
import sys
import time
import json
import socket
import signal
import subprocess
from contextlib import closing

import requests


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANAGE = os.path.join(BASE_DIR, "manage.py")


def log(msg):
    print(msg, flush=True)


def port_open(host, port, timeout=1.5):
    try:
        with closing(socket.create_connection((host, int(port)), timeout=timeout)):
            return True
    except Exception:
        return False


def run(cmd, env=None, cwd=None, timeout=None):
    return subprocess.run(
        cmd,
        shell=True,
        env=env or os.environ.copy(),
        cwd=cwd or BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )


def start_bg(cmd, env=None, cwd=None):
    return subprocess.Popen(
        cmd,
        shell=True,
        env=env or os.environ.copy(),
        cwd=cwd or BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )


def stop_bg(proc):
    if proc and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass


def wait_until(check_fn, timeout=20, interval=0.5):
    start = time.time()
    while time.time() - start < timeout:
        if check_fn():
            return True
        time.sleep(interval)
    return False


def migrate(env):
    log("Running migrations...")
    res = run(
        ". .venv/bin/activate && python manage.py migrate --noinput",
        env=env,
        cwd=BASE_DIR,
    )
    if res.returncode != 0:
        return False, res.stdout
    return True, res.stdout


def create_users(env):
    """
    Create three users with roles via Django shell for auth tests:
    admin:pass (is_staff)
    coach:pass (profile.role=coach)
    client:pass (profile.role=client)
    """
    script = r"""
from django.contrib.auth.models import User
from api.models import UserProfile

def ensure_user(username, is_staff=False, role="client"):
    u, _ = User.objects.get_or_create(username=username)
    u.set_password("pass")
    u.is_staff = is_staff
    u.save()
    up, _ = UserProfile.objects.get_or_create(user=u)
    up.role = role
    up.save()

ensure_user("admin", is_staff=True, role="admin")
ensure_user("coach", is_staff=False, role="coach")
ensure_user("client", is_staff=False, role="client")
print("OK")
"""
    res = run(
        f'''. .venv/bin/activate && python manage.py shell -c "{script.replace('"', '\\"').replace('\n', ';')}"''',
        env=env,
        cwd=BASE_DIR,
    )  # noqa: E501
    return res.returncode == 0, res.stdout


def jwt_login(base_url, username="coach", password="pass"):
    url = f"{base_url}/api/auth/login"
    resp = requests.post(url, json={"username": username, "password": password}, timeout=10)
    if resp.status_code == 200 and "access" in resp.json():
        return True, resp.json()
    return False, f"status={resp.status_code}, body={resp.text}"


def health(base_url):
    url = f"{base_url}/api/health/"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200 and resp.json().get("message") == "Server is up!":
            return True, resp.text
        return False, f"status={resp.status_code}, body={resp.text}"
    except Exception as e:
        return False, str(e)


def foods_list(base_url, token):
    resp = requests.get(f"{base_url}/api/foods/", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    return resp.status_code == 200, f"status={resp.status_code}, body={resp.text}"


def foods_create(base_url, token):
    payload = {"name": "Apple", "calories": 52}
    resp = requests.post(
        f"{base_url}/api/foods/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=10,
    )
    return resp.status_code in (200, 201), f"status={resp.status_code}, body={resp.text}"


def create_conversation(env):
    script = r"""
from django.contrib.auth.models import User
from api.models import Conversation
u = User.objects.get(username="coach")
c = Conversation.objects.create(title="c1")
c.participants.add(u)
print(c.id)
"""
    res = run(
        '. .venv/bin/activate && python manage.py shell -c "'
        + script.replace('"', '\\"').replace('\n', ';')
        + '"',
        env=env,
        cwd=BASE_DIR,
    )
    if res.returncode == 0:
        try:
            cid = int(res.stdout.strip().splitlines()[-1])
            return True, cid, res.stdout
        except Exception:
            return False, None, res.stdout
    return False, None, res.stdout


def ws_validate(ws_host, ws_port, conversation_id, token):
    # Use websockets via Python std? Not in stdlib. We will do a minimal check via websocket-client if available.
    try:
        import websocket  # websocket-client
    except Exception:
        return False, "websocket-client not installed"

    url = f"ws://{ws_host}:{ws_port}/ws/chat/{conversation_id}/?token={token}"
    try:
        ws = websocket.create_connection(url, timeout=10)
        ws.send(json.dumps({"content": "hello"}))
        msg = ws.recv()
        ws.close()
        ok = "hello" in msg
        return ok, msg
    except Exception as e:
        return False, str(e)


def main():
    # Settings
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "5002")  # expected per checklist
    db_name = os.getenv("DB_NAME", "nc_app")  # from platform DB defaults in checklist
    db_user = os.getenv("DB_USER", "nc_app")
    db_password = os.getenv("DB_PASSWORD", "nc_app")
    bind_host = os.getenv("BIND_HOST", "127.0.0.1")
    http_port = int(os.getenv("HTTP_PORT", "8000"))
    ws_port = int(os.getenv("WS_PORT", "8001"))
    use_supabase = os.getenv("USE_SUPABASE_AUTH", "false").lower() == "true"
    jwks_url = os.getenv("SUPABASE_JWKS_URL", "")

    env = os.environ.copy()
    env.update({
        "DB_HOST": db_host,
        "DB_PORT": str(db_port),
        "DB_NAME": db_name,
        "DB_USER": db_user,
        "DB_PASSWORD": db_password,
        # Django runserver/hosts
        "ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
        "DEBUG": "True",
    })

    results = []

    # 1) Migrations (DB connectivity)
    log("Step 1: DB migrations (port {} @ {} -> db {})".format(db_port, db_host, db_name))
    if not port_open(db_host, db_port):
        results.append(("DB_CONNECT", False, f"Cannot connect to {db_host}:{db_port}. Is platform_database up?"))
    ok, out = migrate(env)
    results.append(("MIGRATIONS", ok, out if ok else out))

    # 2) Start server and check /api/health
    base_url = f"http://{bind_host}:{http_port}"
    log("Starting runserver for API checks...")
    srv = start_bg(
        f". .venv/bin/activate && python manage.py runserver {bind_host}:{http_port}",
        env=env,
        cwd=BASE_DIR,
    )
    ready = wait_until(lambda: port_open(bind_host, http_port), timeout=25)
    ok_h, health_out = (False, "server not up")
    if ready:
        # After port opens, wait until /api/health returns 200 to ensure Django is fully ready
        log("Waiting for /api/health readiness...")

        def health_ready():
            ok, _ = health(base_url)
            return ok

        # Allow up to 25s for healthready in addition to port open
        if wait_until(health_ready, timeout=25, interval=0.5):
            ok_h, health_out = health(base_url)
        else:
            ok_h, health_out = health(base_url)
    results.append(("API_HEALTH", ok_h, health_out))

    # 3) Supabase JWKS reachability
    if use_supabase and jwks_url:
        try:
            r = requests.get(jwks_url, timeout=10)
            ok_j = r.ok and "keys" in r.json()
            body_has_keys = "keys" in r.json()
            results.append(
                ("SUPABASE_JWKS", ok_j, f"status={r.status_code}, body_has_keys={body_has_keys}")
            )
        except Exception as e:
            results.append(("SUPABASE_JWKS", False, str(e)))
    else:
        results.append(("SUPABASE_JWKS", True, "Skipped (USE_SUPABASE_AUTH=false or JWKS URL not set)"))

    # 4) Auth flow (fallback JWT)
    log("Preparing users for JWT login flow...")
    ok_users, create_out = create_users(env)
    results.append(("SEED_USERS", ok_users, create_out))
    ok_login, login_out = jwt_login(base_url, username="coach", password="pass")
    token = None
    if ok_login:
        token = login_out.get("access")
    results.append(("JWT_LOGIN", ok_login, login_out if ok_login else login_out))

    # 5) CRUD tests (Foods)
    if token:
        ok_list, list_out = foods_list(base_url, token)
        results.append(("FOODS_LIST", ok_list, list_out))
        ok_post, post_out = foods_create(base_url, token)
        results.append(("FOODS_CREATE", ok_post, post_out))
    else:
        results.append(("FOODS_LIST", False, "No token"))
        results.append(("FOODS_CREATE", False, "No token"))

    # Stop runserver before launching daphne
    stop_bg(srv)
    time.sleep(1)

    # 6) WebSocket via Daphne
    log("Starting Daphne for WebSocket test...")
    ws_proc = start_bg(
        f". .venv/bin/activate && daphne -b {bind_host} -p {ws_port} config.asgi:application",
        env=env,
        cwd=BASE_DIR,
    )
    ready_ws = wait_until(lambda: port_open(bind_host, ws_port), timeout=25)
    if not ready_ws:
        results.append(("WEBSOCKET_UP", False, "Daphne not listening"))
        stop_bg(ws_proc)
    else:
        # Create a conversation and connect to /ws/chat/<id>/?token=<access>
        ok_conv, conv_id, conv_out = create_conversation(env)
        if not ok_conv:
            results.append(("WS_CONVERSATION", False, conv_out))
            stop_bg(ws_proc)
        else:
            # Ensure websocket-client is available
            ws_lib_installed = True
            try:
                import websocket  # noqa: F401
            except Exception:
                ws_lib_installed = False
                # Try to install it into venv
                _ = run(
                    ". .venv/bin/activate && pip install websocket-client",
                    env=env,
                    cwd=BASE_DIR,
                )

            if not ws_lib_installed:
                try:
                    import websocket as _ws  # noqa: F401
                    ws_lib_installed = True
                except Exception:
                    pass

            if not ws_lib_installed:
                results.append(("WEBSOCKET_CLIENT_LIB", False, "websocket-client not available"))
                stop_bg(ws_proc)
            else:
                ok_ws, ws_out = ws_validate(bind_host, ws_port, conv_id, token or "")
                results.append(("WEBSOCKET_ECHO", ok_ws, ws_out))
                stop_bg(ws_proc)

    # 7) Report
    log("\n=== Integration Validation Report ===")
    failed = []
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        log(f"- {name}: {status}")
        if not ok:
            failed.append((name, detail))

    if failed:
        log("\nFailures and targeted suggestions:")
        for name, detail in failed:
            if name in ("DB_CONNECT", "MIGRATIONS"):
                log(
                    f"* {name}: {detail}\n"
                    "  - Ensure platform_database is running on port 5002 with "
                    "DB_NAME/USER/PASSWORD matching (default nc_app)."
                )
                log("  - Update backend .env or export DB_* env vars accordingly.")
            elif name == "API_HEALTH":
                log(
                    f"* {name}: {detail}\n"
                    "  - Check server logs for startup errors. Verify migrations and ports."
                )
            elif name == "SUPABASE_JWKS":
                log(
                    f"* {name}: {detail}\n"
                    "  - Verify USE_SUPABASE_AUTH=true and JWKS URL correctness; "
                    "ensure network egress."
                )
            elif name == "JWT_LOGIN":
                log(
                    f"* {name}: {detail}\n"
                    "  - Verify users exist and passwords. The script attempts to seed users; check logs."
                )
            elif name in ("FOODS_LIST", "FOODS_CREATE"):
                log(
                    f"* {name}: {detail}\n"
                    "  - Ensure Authorization: Bearer <token> is provided and user has permissions."
                )
            elif name in ("WEBSOCKET_UP", "WEBSOCKET_ECHO"):
                log(
                    f"* {name}: {detail}\n"
                    "  - Ensure Daphne is used for WS and token is valid. Check CHANNEL_LAYERS config."
                )
            else:
                log(f"* {name}: {detail}")
    else:
        log("All checks passed.")

    # Exit non-zero on failures
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
