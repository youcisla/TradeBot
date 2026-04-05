from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    status: str  # ok | warn | fail
    detail: str


@dataclass
class DoctorReport:
    checks: list[CheckResult]
    recommendations: list[str]

    @property
    def has_failures(self) -> bool:
        return any(c.status == "fail" for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.status == "warn" for c in self.checks)

    def to_json(self) -> str:
        return json.dumps(
            {
                "checks": [asdict(c) for c in self.checks],
                "recommendations": self.recommendations,
                "has_failures": self.has_failures,
                "has_warnings": self.has_warnings,
            },
            indent=2,
        )


def run_doctor(repo_root: Path) -> DoctorReport:
    checks: list[CheckResult] = []
    recommendations: list[str] = []

    checks.extend(_preflight_checks(repo_root, recommendations))
    checks.extend(_log_checks(repo_root, recommendations))

    return DoctorReport(checks=checks, recommendations=_uniq(recommendations))


def format_text_report(report: DoctorReport) -> str:
    lines: list[str] = []
    lines.append("TradeBot Ops Doctor")
    lines.append("===================")
    for check in report.checks:
        badge = {
            "ok": "[OK]",
            "warn": "[WARN]",
            "fail": "[FAIL]",
        }.get(check.status, "[INFO]")
        lines.append(f"{badge} {check.name}: {check.detail}")

    if report.recommendations:
        lines.append("")
        lines.append("Recommended Actions")
        lines.append("-------------------")
        for idx, rec in enumerate(report.recommendations, start=1):
            lines.append(f"{idx}. {rec}")

    return "\n".join(lines)


def _preflight_checks(repo_root: Path, recommendations: list[str]) -> list[CheckResult]:
    out: list[CheckResult] = []

    venv_py = repo_root / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        out.append(CheckResult("Python venv", "ok", str(venv_py)))
    else:
        out.append(CheckResult("Python venv", "fail", "Missing .venv\\Scripts\\python.exe"))
        recommendations.append("Create venv and install dependencies before running launcher")

    env_file = repo_root / ".env"
    if env_file.exists():
        env_text = env_file.read_text(encoding="utf-8", errors="ignore")
        missing = [
            key
            for key in ("DATABASE_URL", "BROKER_ACCOUNT", "BROKER_PASSWORD", "BROKER_SERVER")
            if not _env_has_value(env_text, key)
        ]
        if missing:
            out.append(CheckResult("Environment", "warn", f"Missing values: {', '.join(missing)}"))
            recommendations.append("Populate missing critical .env broker/database values")
        else:
            out.append(CheckResult("Environment", "ok", "Critical .env values detected"))
    else:
        out.append(CheckResult("Environment", "fail", "Missing .env file"))
        recommendations.append("Copy .env.example to .env and fill required credentials")

    return out


def _log_checks(repo_root: Path, recommendations: list[str]) -> list[CheckResult]:
    out: list[CheckResult] = []
    logs_dir = repo_root / "logs"
    if not logs_dir.exists():
        out.append(CheckResult("Logs", "warn", "logs/ directory does not exist yet"))
        return out

    bot_logs = sorted(logs_dir.glob("bot_*.log*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not bot_logs:
        out.append(CheckResult("Logs", "warn", "No bot_*.log files found"))
        return out

    # Keep the most recent two rotated files to keep analysis fast.
    lines: list[str] = []
    for f in bot_logs[:2]:
        lines.extend(f.read_text(encoding="utf-8", errors="ignore").splitlines())

    text = "\n".join(lines)
    if not text.strip():
        out.append(CheckResult("Recent logs", "warn", "Latest log files are empty"))
        return out

    mt5_disabled = len(re.findall(r"(10027|10017|autotrading disabled)", text, flags=re.IGNORECASE))
    spread_rejects = len(re.findall(r"RISK REJECT \[SPREAD\]", text))
    stuck_quotes = len(re.findall(r"Stuck quote", text))
    db_ssl_errors = len(re.findall(r"SSL connection has been closed unexpectedly", text))

    if mt5_disabled > 0:
        out.append(
            CheckResult(
                "MT5 autotrading",
                "fail",
                f"Detected {mt5_disabled} autotrading-disabled execution errors",
            )
        )
        recommendations.append("Enable Algo Trading in MT5 terminal before starting bot")
    else:
        out.append(CheckResult("MT5 autotrading", "ok", "No autotrading-disabled errors detected"))

    if spread_rejects > 50:
        out.append(CheckResult("Spread rejects", "warn", f"High spread rejections: {spread_rejects}"))
        recommendations.append("Review symbol spread limits or reduce symbol set during wide-spread sessions")
    else:
        out.append(CheckResult("Spread rejects", "ok", f"Spread rejection count: {spread_rejects}"))

    if stuck_quotes > 20:
        out.append(CheckResult("Data feed quality", "warn", f"Frequent stuck quotes: {stuck_quotes}"))
        recommendations.append("Check MT5 symbol subscriptions and market data feed stability")
    else:
        out.append(CheckResult("Data feed quality", "ok", f"Stuck quote events: {stuck_quotes}"))

    if db_ssl_errors > 0:
        out.append(CheckResult("Database connectivity", "warn", f"Transient DB SSL disconnects: {db_ssl_errors}"))
        recommendations.append("Harden DB connection pooling/retry settings and verify network stability")
    else:
        out.append(CheckResult("Database connectivity", "ok", "No DB SSL disconnects detected"))

    return out


def _env_has_value(env_text: str, key: str) -> bool:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", flags=re.MULTILINE)
    match = pattern.search(env_text)
    if not match:
        return False
    value = match.group(1).strip().strip('"').strip("'")
    return bool(value)


def _uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
