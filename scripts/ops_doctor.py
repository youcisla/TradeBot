from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is importable when script is run directly.
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.ops_doctor import format_text_report, run_doctor


def main() -> int:
    parser = argparse.ArgumentParser(description="TradeBot operations doctor")
    parser.add_argument("--root", default=str(_REPO), help="Repo root path")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any failure is detected",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = run_doctor(root)

    if args.json:
        print(report.to_json())
    else:
        print(format_text_report(report))

    if args.strict and report.has_failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
