"""One-time migration: hardcoded .env broker credentials → encrypted broker_accounts profile.

Usage
-----
    python scripts/migrate_credentials.py

Steps
-----
1. Read existing BROKER_ACCOUNT, BROKER_PASSWORD, BROKER_SERVER from .env
2. Detect if already migrated (MIGRATED=true in .env) — exit early if so
3. Prompt user to log into the dashboard at http://localhost:3000/login
4. Prompt for the session_token from browser DevTools (sessionStorage)
5. Validate the session via GET /api/auth/status
6. Create an encrypted profile via POST /api/auth/profiles
7. Activate the profile via POST /api/auth/profiles/{id}/activate
8. Update .env: clear BROKER_PASSWORD, set MIGRATED=true

After migration the bot will use the encrypted profile store. Restart the bot
and dashboard for changes to take effect.
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
API_BASE = "http://127.0.0.1:8001"


# ── .env helpers (from first_run_wizard.py) ───────────────────────────────────

def _parse_env(content: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _render_env(existing: str, updates: dict[str, str]) -> str:
    lines = existing.splitlines()
    seen: set[str] = set()
    output: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in updates:
                output.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        output.append(line)

    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={value}")

    return "\n".join(output).rstrip() + "\n"


# ── HTTP helper ────────────────────────────────────────────────────────────────

def _api_post(path: str, body: dict, token: str | None = None) -> dict:
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{API_BASE}{path}", data=data, headers=headers, method="POST")
    with urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _api_get(path: str, token: str | None = None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{API_BASE}{path}", headers=headers, method="GET")
    with urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Detect demo vs live ────────────────────────────────────────────────────────

def _is_demo_account(account_number: str) -> bool:
    lower = account_number.lower()
    return "demo" in lower or "test" in lower


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    existing = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    current = _parse_env(existing)

    account = current.get("BROKER_ACCOUNT", "").strip()
    password = current.get("BROKER_PASSWORD", "").strip()
    server = current.get("BROKER_SERVER", "").strip()

    if current.get("MIGRATED", "").lower() == "true":
        print("Already migrated — MIGRATED=true found in .env. Nothing to do.")
        sys.exit(0)

    if not account or not password or not server:
        print("Error: BROKER_ACCOUNT, BROKER_PASSWORD, and BROKER_SERVER must all be set in .env")
        sys.exit(1)

    print("TradeBot Credential Migration")
    print("------------------------------")
    print()
    print("Before you begin:")
    print("  1. Open http://localhost:3000/login in your browser")
    print("  2. Log in with your dashboard username and password")
    print("  3. Open DevTools → Application → sessionStorage → session_token")
    print("     (copy the value — it looks like a long random string)")
    print()

    token = input("Paste your session_token from sessionStorage: ").strip()
    if not token:
        print("session_token is required.")
        sys.exit(1)

    # Validate session
    try:
        status = _api_get("/api/auth/status", token)
    except URLError as exc:
        print(f"Error: Could not reach the API at {API_BASE} — is the bot running?")
        print(f"  Detail: {exc}")
        sys.exit(1)

    if not status.get("authenticated"):
        print("Error: session_token is invalid or expired. Please re-login.")
        sys.exit(1)

    print(f"Session valid for user: {status.get('username', '?')}")

    # Detect demo vs live
    demo = _is_demo_account(account)
    profile_label = "Demo" if demo else "Live"

    # Create profile
    print(f"\nCreating profile '{profile_label}' for account {account}...")
    try:
        profile = _api_post(
            "/api/auth/profiles",
            {
                "profile_label": profile_label,
                "account_number": account,
                "server": server,
                "password": password,
            },
            token,
        )
    except URLError as exc:
        print(f"Error: Failed to create profile — is the bot API accessible?")
        print(f"  Detail: {exc}")
        sys.exit(1)

    profile_id = profile.get("id")
    if not profile_id:
        print(f"Error: Unexpected response from API: {profile}")
        sys.exit(1)

    print(f"Profile created (id={profile_id}). Activating...")

    # Activate profile
    try:
        _api_post(f"/api/auth/profiles/{profile_id}/activate", {}, token)
    except URLError as exc:
        print(f"Error: Failed to activate profile.")
        print(f"  Detail: {exc}")
        sys.exit(1)

    # Update .env: clear password, set migrated flag
    updates = {
        "MIGRATED": "true",
        "BROKER_PASSWORD": "",  # plaintext no longer needed
    }
    rendered = _render_env(existing, updates)
    ENV_PATH.write_text(rendered, encoding="utf-8")

    print("\nMigration complete!")
    print(f"  Profile '{profile_label}' (id={profile_id}) is now active.")
    print("  BROKER_PASSWORD has been cleared from .env.")
    print("  Restart the bot and dashboard to use the new profile system.")


if __name__ == "__main__":
    main()
