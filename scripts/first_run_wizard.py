"""Interactive first-run onboarding wizard for TradeBot.

Creates or updates .env with safe defaults and runtime profile selection.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


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


def _prompt(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value if value else default


def main() -> None:
    existing = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    current = _parse_env(existing)

    print("TradeBot First-Run Wizard")
    print("-------------------------")
    print("This wizard writes safe defaults to .env for a first deployment.\n")

    profile = _prompt(
        "Select BOT_PROFILE (custom/dev/paper/live-safe/live-full)",
        current.get("BOT_PROFILE", "paper"),
    ).lower()
    if profile not in {"custom", "dev", "paper", "live-safe", "live-full"}:
        print("Invalid profile, falling back to 'paper'.")
        profile = "paper"

    database_url = _prompt("DATABASE_URL", current.get("DATABASE_URL", ""))
    broker_account = _prompt("BROKER_ACCOUNT (empty = mock mode)", current.get("BROKER_ACCOUNT", ""))
    broker_password = _prompt("BROKER_PASSWORD", current.get("BROKER_PASSWORD", ""))
    broker_server = _prompt("BROKER_SERVER", current.get("BROKER_SERVER", ""))

    deepseek_key = _prompt("DEEPSEEK_API_KEY (optional)", current.get("DEEPSEEK_API_KEY", ""))
    telegram_token = _prompt("TELEGRAM_BOT_TOKEN (optional)", current.get("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat = _prompt("TELEGRAM_CHAT_ID (optional)", current.get("TELEGRAM_CHAT_ID", ""))

    weekend_symbols = _prompt(
        "WEEKEND_SYMBOLS",
        current.get("WEEKEND_SYMBOLS", "BTCUSD,ETHUSD"),
    )

    updates = {
        "BOT_PROFILE": profile,
        "DATABASE_URL": database_url,
        "BROKER_ACCOUNT": broker_account,
        "BROKER_PASSWORD": broker_password,
        "BROKER_SERVER": broker_server,
        "DEEPSEEK_API_KEY": deepseek_key,
        "TELEGRAM_BOT_TOKEN": telegram_token,
        "TELEGRAM_CHAT_ID": telegram_chat,
        "WEEKEND_SYMBOLS": weekend_symbols,
        "COUNCIL_ENABLED": current.get("COUNCIL_ENABLED", "true"),
        "COUNCIL_MODE": current.get("COUNCIL_MODE", "blocking" if profile in {"paper", "live-safe"} else "advisory"),
        "RISK_VALIDATION_PROFILE": current.get(
            "RISK_VALIDATION_PROFILE",
            "strict" if profile == "live-safe" else "agile",
        ),
    }

    rendered = _render_env(existing, updates)
    ENV_PATH.write_text(rendered, encoding="utf-8")

    print("\nSaved .env successfully.")
    print("Next steps:")
    print("1. Review .env values manually.")
    print("2. Run: .\\start.ps1")
    print("3. Confirm bot status at http://localhost:3000/dashboard")


if __name__ == "__main__":
    main()
