import numpy as np
import pandas as pd


def summarize(equity, trades=None, exposure=None):
    equity = equity.dropna()
    r = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    dd = equity / equity.cummax() - 1
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    vol = r.std() * np.sqrt(252)
    out = {
        "cagr": cagr, "vol": vol,
        "sharpe": (r.mean() * 252) / vol if vol > 0 else np.nan,
        "max_dd": dd.min(),
        "calmar": cagr / abs(dd.min()) if dd.min() < 0 else np.nan,
        "years": years,
    }
    if trades is not None:
        pnl = pd.Series([t["pnl"] for t in trades], dtype=float)
        out["n_trades"] = len(pnl)
        out["win_rate"] = float((pnl > 0).mean()) if len(pnl) else np.nan
    if exposure is not None:
        out["time_invested"] = float(exposure.reindex(equity.index).fillna(0).mean())
    return out
