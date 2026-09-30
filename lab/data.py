"""Price loading. Prefer a real SPY CSV; fall back to a bundled S&P 500 index sample."""
import pandas as pd

DEV_END = "2010-12-31"  # everything after this is holdout (touch it once, see run_all.py)


def load_prices(csv_path=None):
    """Return a DataFrame indexed by date with a 'close' column (plus others if present).

    csv_path: Yahoo/TradingView-style export with a date column and Close (or Adj Close).
    Without a path we use arch's bundled S&P 500 *price index* (1999-2018, no dividends).
    That is a development proxy only, not SPY, and it ends in 2018.
    """
    if csv_path:
        df = pd.read_csv(csv_path)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        date_col = next(c for c in ("date", "datetime", "time") if c in df.columns)
        px_col = "adj_close" if "adj_close" in df.columns else "close"
        out = pd.DataFrame({"close": df[px_col].astype(float).values},
                           index=pd.to_datetime(df[date_col]).dt.tz_localize(None).dt.normalize())
        for c in ("open", "high", "low", "volume"):
            if c in df.columns:
                out[c] = df[c].values
        out = out[~out.index.duplicated()].sort_index()
        return out.dropna(subset=["close"]), f"csv:{csv_path}"
    from arch.data import sp500
    d = sp500.load()
    d.columns = [c.strip().lower().replace(" ", "_") for c in d.columns]
    d.index = pd.to_datetime(d.index)
    return d[["close"]].sort_index(), "PROXY:arch S&P500 price index 1999-2018 (not SPY)"


def window(prices, part):
    if part == "dev":
        return prices.loc[:DEV_END]
    if part == "holdout":
        return prices.loc[DEV_END:].iloc[1:]
    return prices
