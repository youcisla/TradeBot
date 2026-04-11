from __future__ import annotations

from pathlib import Path

from utils.ops_doctor import run_doctor


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_doctor_flags_missing_env_and_venv(tmp_path: Path):
    report = run_doctor(tmp_path)
    assert report.has_failures is True
    names = {c.name: c for c in report.checks}
    assert names["Python venv"].status == "fail"
    assert names["Environment"].status == "fail"


def test_doctor_detects_mt5_disabled_and_spread_noise(tmp_path: Path):
    _write(tmp_path / ".env", "DATABASE_URL=postgres://x\nBROKER_ACCOUNT=1\nBROKER_PASSWORD=p\nBROKER_SERVER=s\n")
    _write(tmp_path / ".venv" / "Scripts" / "python.exe", "")

    log_lines = []
    for _ in range(60):
        log_lines.append("WARNING | agents.risk_agent | RISK REJECT [SPREAD]: too high")
    for _ in range(3):
        log_lines.append("ERROR | agents.execution_agent | MT5 error 10027: AutoTrading disabled by client")
    _write(tmp_path / "logs" / "backend" / "backend_2026-01-01.log", "\n".join(log_lines))

    report = run_doctor(tmp_path)
    checks = {c.name: c for c in report.checks}

    assert checks["Environment"].status == "ok"
    assert checks["Python venv"].status == "ok"
    assert checks["MT5 autotrading"].status == "fail"
    assert checks["Spread rejects"].status == "warn"
    assert report.has_failures is True
