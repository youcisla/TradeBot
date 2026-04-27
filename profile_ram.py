"""RAM profiler — run standalone to snapshot current memory state.

Usage (inside the bot process):
    from profile_ram import snapshot_and_report
    snapshot_and_report()

Usage (standalone):
    python profile_ram.py
"""
import gc, sys, os, time, threading

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

def fmt(b):
    if b is None:
        return "N/A"
    return f"{b / 1024 / 1024:.1f} MB"

def snapshot(proc=None):
    if HAS_PSUTIL and proc:
        return proc.memory_info().rss
    return 0

def _top_objects(limit=20):
    """Find modules that import a lot of sub-modules (heuristic for heavy imports)."""
    print(f"\nTop modules by import depth (heuristic):")
    heavy = []
    for name, mod in sys.modules.items():
        if not hasattr(mod, '__file__') or not mod.__file__:
            continue
        if any(x in name for x in ('lightgbm', 'xgboost', 'numpy', 'pandas', 'sklearn', 'shap')):
            heavy.append(name)
    for h in sorted(heavy):
        print(f"  {h}")

def snapshot_and_report(label="now"):
    """Call this from within the bot process for an in-process memory snapshot."""
    gc.collect()
    proc = psutil.Process(os.getpid()) if HAS_PSUTIL else None
    rss = snapshot(proc)
    threads = threading.active_count()
    print(f"\n[RAM {label}] RSS={fmt(rss)} threads={threads}")
    return rss

def main():
    pid = os.getpid()
    proc = psutil.Process(pid) if HAS_PSUTIL else None

    baseline = snapshot(proc)
    print(f"[{pid}] Baseline RSS: {fmt(baseline)}")

    # ── Import all agents ──────────────────────────────────────────────
    t0 = time.monotonic()
    print("\nImporting agents...")
    imports = [
        ("ExecutionAgent", "agents.execution_agent"),
        ("RiskAgent", "agents.risk_agent"),
        ("MarketAgent", "agents.market_agent"),
        ("AnalysisAgent", "agents.analysis_agent"),
        ("LearningAgent", "agents.learning_agent"),
        ("TradeManagerAgent", "agents.trade_manager"),
        ("StrategyAgent", "agents.strategy_agent"),
        ("LoggingAgent", "agents.logging_agent"),
        ("CrucixAgent", "agents.crucix_agent"),
        ("LGBMEnsemble", "models.lgbm_ensemble"),
        ("LGBMPriceModel", "models.lgbm_price_model"),
    ]
    for name, path in imports:
        __import__(path)

    gc.collect()
    after_import = snapshot(proc)
    print(f"After imports: {fmt(after_import)} (+{fmt(after_import - baseline)}) [{time.monotonic()-t0:.1f}s]")

    # ── Thread count ──────────────────────────────────────────────────
    print(f"\nThread count: {threading.active_count()}")
    for t in threading.enumerate():
        print(f"  {t.name} daemon={t.daemon}")

    # ── GC stats ──────────────────────────────────────────────────────
    print("\nGC stats:")
    gc.collect()
    stats = gc.get_stats()
    print(f"  GC generations: {len(stats)}")
    for s in stats:
        print(f"    {s}")

    print(f"\nFinal RSS: {fmt(snapshot(proc))}")

    # ── Heavy module heuristic ─────────────────────────────────────────
    _top_objects()

if __name__ == "__main__":
    main()
