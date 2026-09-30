import numpy as np
import pandas as pd


def sma(s, n):
    return s.rolling(n).mean()


def rsi(close, n=2):
    """Wilder RSI."""
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def realized_vol(close, n=20):
    return np.log(close).diff().rolling(n).std() * np.sqrt(252)


def _asof_daily(series_low_freq, daily_index):
    """Map a completed weekly/monthly value onto daily bars with no look-ahead.

    A period's value is labelled with the period-end date and only becomes visible
    on that date or later, so it is never used before that period has closed.
    """
    return series_low_freq.reindex(series_low_freq.index.union(daily_index)).ffill().reindex(daily_index)


def weekly_sma_rising(close, n=10):
    w = close.resample("W-FRI").last().dropna()
    s = sma(w, n)
    rising = (s > s.shift(1)).astype(float).where(s.notna() & s.shift(1).notna())
    return _asof_daily(rising, close.index)


def monthly_above_sma(close, n=10):
    m = close.resample("ME").last().dropna()
    above = (m > sma(m, n)).astype(float).where(sma(m, n).notna())
    return _asof_daily(above, close.index)
