from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.error
import json
import os
import signal

ROOT = Path.cwd()
BASE = "http://127.0.0.1:8000"

print("=" * 60)
print("VOXMATE TASK 6 - API SMOKE TEST")
print("=" * 60)

server = None

def request(path, method="GET", headers=None, data=None):
    url = BASE + path
    req = urllib.request.Request(
        url,
        method=method,
        headers=headers or {},
        data=data
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read(2000).decode("utf-8", errors="replace")
            return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read(2000).decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:
        return None, str(e)

try:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")

    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT / "backend",
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    ready = False
    for _ in range(30):
        time.sleep(1)
        status, _ = request("/")
        if status is not None:
            ready = True
            break

    if not ready:
        raise RuntimeError("FastAPI server did not become ready.")

    checks = []

    def check(name, path, expected):
        status, body = request(path)
        ok = status in expected
        checks.append((name, status, ok))
        print(
            f"{'PASS' if ok else 'FAIL'}: {name} "
            f"[HTTP {status}]"
        )
        return ok

    check("Root endpoint", "/", {200, 307, 308})
    check("OpenAPI endpoint", "/openapi.json", {200})
    check("Swagger documentation", "/docs", {200})
    check("Health endpoint", "/health", {200, 404})

    cors_headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }

    status, body = request(
        "/openapi.json",
        method="OPTIONS",
        headers=cors_headers,
    )

    cors_ok = status in {200, 204}
    checks.append(("CORS preflight", status, cors_ok))

    print(
        f"{'PASS' if cors_ok else 'FAIL'}: "
        f"CORS preflight [HTTP {status}]"
    )

    failures = [x for x in checks if not x[2]]

    print()
    print("=" * 60)

    if failures:
        print("API SMOKE TEST: FAIL")
        print(f"Failed checks: {len(failures)}")
        raise SystemExit(1)

    print("API SMOKE TEST: 100% PASS")
    print(f"Passed checks: {len(checks)}/{len(checks)}")

finally:
    if server is not None:
        try:
            server.terminate()
            server.wait(timeout=5)
        except Exception:
            try:
                server.kill()
            except Exception:
                pass

print()
print("=" * 60)
print("RUNNING FULL PYTEST")
print("=" * 60)

result = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=ROOT,
)

if result.returncode != 0:
    raise SystemExit(result.returncode)

print()
print("=" * 60)
print("TASK 6 API + AUTOMATED TESTS: PASS")
print("=" * 60)
