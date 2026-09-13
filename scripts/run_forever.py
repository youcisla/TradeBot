"""Always-on entry point — run the bot under supervision.

    python scripts/run_forever.py

Same bot as ``python main.py``, plus:

* automatic restart on crash, with exponential backoff capped at 5 minutes;
* hung-process detection — if the bot stops writing its heartbeat, it is
  killed and restarted, because a hung bot looks alive while managing nothing;
* a kill switch.  To stop everything cleanly::

      python scripts/run_forever.py --stop

* a restart budget: after too many crashes in an hour the supervisor gives up
  rather than crash-looping against the broker.

Live capital is refused outright unless ``autonomy/edge_gate.py`` says the
strategy has earned it.  Demo mode is unaffected.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from autonomy.edge_gate import evaluate_file  # noqa: E402
from autonomy.supervisor import Supervisor, SupervisorConfig  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_forever")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the trading bot under supervision")
    parser.add_argument("--stop", action="store_true", help="Create the kill switch and exit")
    parser.add_argument("--clear", action="store_true", help="Remove the kill switch and exit")
    parser.add_argument("--stale-after", type=float, default=300.0,
                        help="Seconds without a heartbeat before the bot is considered hung")
    parser.add_argument("--entry", default="main.py", help="Bot entry point to supervise")
    args = parser.parse_args()

    cfg = SupervisorConfig(
        command=[sys.executable, args.entry],
        cwd=_REPO,
        heartbeat_path=_REPO / "state" / "heartbeat.json",
        kill_switch_path=_REPO / "state" / "STOP",
        stale_after_s=args.stale_after,
    )

    if args.stop:
        cfg.kill_switch_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.kill_switch_path.write_text(
            "Stop requested. Remove this file (or run --clear) to allow restarts.\n",
            encoding="utf-8",
        )
        logger.info("Kill switch set at %s — a running supervisor will stop.", cfg.kill_switch_path)
        return 0

    if args.clear:
        cfg.kill_switch_path.unlink(missing_ok=True)
        logger.info("Kill switch cleared.")
        return 0

    # Show the promotion verdict before anything starts, so the reason a run is
    # refused (or permitted) is never buried in a log tail.
    verdict = evaluate_file()
    logger.info("\n%s", verdict.render())

    return Supervisor(cfg).run()


if __name__ == "__main__":
    sys.exit(main())
