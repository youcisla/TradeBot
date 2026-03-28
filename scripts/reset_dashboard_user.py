"""Reset the dashboard login credentials.

Usage
-----
    python scripts/reset_dashboard_user.py
    python scripts/reset_dashboard_user.py --username admin --password mypassword

With no arguments the script prompts for username and password interactively.
The next time you open the dashboard and log in, the new credentials will work.
"""

from __future__ import annotations

import argparse
import getpass
import sys
import os

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from database.db import Database


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset dashboard login credentials")
    parser.add_argument("--username", default="", help="New username (prompted if omitted)")
    # Intentionally no --password argument: passwords passed via CLI flags are
    # visible in process listings (ps aux) and shell history.  Use the prompt.
    args = parser.parse_args()

    username = args.username.strip() or input("New username [admin]: ").strip() or "admin"
    password = getpass.getpass("New password: ")
    if not password:
        print("Password cannot be empty.")
        sys.exit(1)

    db = Database()
    conn = db._get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM dashboard_users")
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
                cur.execute(
                    "INSERT INTO dashboard_users (username, password_hash) VALUES (%s, %s)",
                    (username.lower(), hashed),
                )
        print(f"\nDone. Log in with username='{username}' and your chosen password.")
        print("Restart the Next.js dashboard if it is already running.")
    finally:
        db._put_conn(conn)
    db.close()


if __name__ == "__main__":
    main()
