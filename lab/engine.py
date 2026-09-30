"""Underlying-level engine. A position decided at the close of day t earns day t+1's return."""
import numpy as np
import pandas as pd


def run_positions(close, pos, cost_bps=1.0):
    """pos: exposure (0..1) decided at each close. Returns equity, trades, exposure actually held."""
    ret = close.pct_change().fillna(0.0)
    held = pos.shift(1).fillna(0.0)                 # the one-bar delay that prevents look-ahead
    turnover = held.diff().abs().fillna(held.abs())
    net = held * ret - turnover * cost_bps / 1e4
    equity = (1 + net).cumprod()
    # trades = contiguous runs of held > 0
    trades, in_run, start = [], False, None
    for i, (d, h) in enumerate(held.items()):
        if h > 0 and not in_run:
            in_run, start = True, i
        if in_run and (h == 0 or i == len(held) - 1):
            end = i if h == 0 else i + 1
            e0 = equity.iloc[start - 1] if start > 0 else 1.0
            trades.append({"pnl": equity.iloc[end - 1] / e0 - 1, "bars": end - start})
            in_run = False
    return equity, trades, held
