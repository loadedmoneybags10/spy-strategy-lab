"""Black-Scholes helpers (model prices, not market prices)."""
from math import erf, exp, log, sqrt


def _N(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def price(kind, S, K, T, sig, r=0.0):
    if T <= 0:
        return max(S - K, 0.0) if kind == "c" else max(K - S, 0.0)
    d1 = (log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * sqrt(T))
    d2 = d1 - sig * sqrt(T)
    if kind == "c":
        return S * _N(d1) - K * exp(-r * T) * _N(d2)
    return K * exp(-r * T) * _N(-d2) - S * _N(-d1)


def delta(kind, S, K, T, sig, r=0.0):
    if T <= 0:
        return (1.0 if S > K else 0.0) if kind == "c" else (-1.0 if S < K else 0.0)
    d1 = (log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * sqrt(T))
    return _N(d1) if kind == "c" else _N(d1) - 1


def strike_for_delta(kind, target_abs_delta, S, T, sig, r=0.0):
    """Bisection on strike so that |delta| == target."""
    lo, hi = S * 0.3, S * 1.7
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        d = abs(delta(kind, S, mid, T, sig, r))
        # |delta| falls as call strike rises, and rises as put strike rises
        if kind == "c":
            lo, hi = (mid, hi) if d > target_abs_delta else (lo, mid)
        else:
            lo, hi = (lo, mid) if d > target_abs_delta else (mid, hi)
    return 0.5 * (lo + hi)
