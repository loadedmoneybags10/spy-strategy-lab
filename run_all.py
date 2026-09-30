#!/usr/bin/env python3
"""Run every strategy on identical data/costs and print one comparison table.

  python run_all.py                      # dev period only (default)
  python run_all.py --csv SPY.csv       # real SPY export
  python run_all.py --holdout           # the untouched period. Allowed ONCE; a lock file records it.
"""
import argparse, json, sys, time
from pathlib import Path
import pandas as pd
from lab import data, strategies as st
from lab.metrics import summarize

ROOT = Path(__file__).parent
RES = ROOT / "results"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--part", choices=["dev", "holdout", "all"], default="dev")
    ap.add_argument("--holdout", action="store_true", help="shorthand for --part holdout")
    ap.add_argument("--force", action="store_true", help="re-run holdout knowing it is no longer clean")
    a = ap.parse_args()
    part = "holdout" if a.holdout else a.part
    RES.mkdir(exist_ok=True)
    lock = RES / "holdout_lock.json"
    if part in ("holdout", "all"):
        if lock.exists() and not a.force:
            sys.exit(f"REFUSED: holdout already used ({lock.read_text()}). Re-running it is peeking; --force to override.")
        lock.write_text(json.dumps({"used_at": time.strftime("%Y-%m-%d %H:%M:%S"), "csv": a.csv}))

    prices, source = data.load_prices(a.csv)
    close_full = prices["close"]
    results = st.build_all(close_full)          # signals use only past data, so computing on the full series is safe
    win = data.window(prices, part).index

    rows = {}
    for name, (eq, trades, expo) in results.items():
        eq = eq.reindex(win)
        eq = eq / eq.iloc[0]
        rows[name] = summarize(eq, trades if name != "S0 buy&hold" else None, expo)
    df = pd.DataFrame(rows).T
    fmt = df.copy()
    for c in ("cagr", "vol", "max_dd", "win_rate", "time_invested"):
        if c in fmt: fmt[c] = (fmt[c] * 100).round(1).astype(str) + "%"
    for c in ("sharpe", "calmar", "years"):
        if c in fmt: fmt[c] = fmt[c].astype(float).round(2)
    print(f"\nDATA: {source}\nPERIOD: {part}  {win[0].date()} -> {win[-1].date()}\n")
    print(fmt.to_string())
    print("\n* = option strategies are Black-Scholes MODEL prices (IV proxy from realized vol). Use for ranking ideas, not for return claims.")
    print("S5 vol-spike bounce: NOT TESTED (needs VIX history; not reachable from this environment).")
    print("Assumptions:", json.dumps(st.P))
    trials = RES / "trials.jsonl"
    with trials.open("a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "part": part, "source": source, "params": st.P}) + "\n")
    n = sum(1 for _ in trials.open())
    print(f"\nTrials logged so far: {n}  (every extra variant you test raises the odds a winner is luck)")
    df.to_csv(RES / f"report_{part}.csv")


if __name__ == "__main__":
    main()
