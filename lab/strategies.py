"""Frozen strategy definitions. See ../rules.md — do not tune these to results."""
import numpy as np
import pandas as pd
from . import bs
from .indicators import sma, rsi, realized_vol, weekly_sma_rising, monthly_above_sma
from .engine import run_positions

P = dict(  # every assumption in one place; printed with every report
    cost_bps_underlying=1.0,
    rsi_len=2, rsi_entry=10, exit_sma=5, gate_sma=200, weekly_sma=10, monthly_sma=10,
    iv_mult=1.10, iv_floor=0.10, put_skew=0.02, opt_half_spread_frac_spot=0.0002,
    s3_dte=25, s3_short_delta=0.20, s3_width_frac=0.05, s3_take_profit=0.50, s3_risk_frac=0.02,
    s4_dte=190, s4_roll_at=42, s4_delta=0.80,
)


def signals(close):
    gate = (close > sma(close, P["gate_sma"]))
    wk = weekly_sma_rising(close, P["weekly_sma"]) == 1
    dip = rsi(close, P["rsi_len"]) < P["rsi_entry"]
    entry = gate & wk & dip
    exit_ = (close > sma(close, P["exit_sma"])) | ~gate
    return dict(gate=gate.fillna(False), entry=entry.fillna(False), exit=exit_.fillna(False))


def s0_buy_hold(close):
    return pd.Series(1.0, index=close.index)


def s1a_daily_gate(close):
    return (close > sma(close, P["gate_sma"])).astype(float).where(sma(close, P["gate_sma"]).notna(), 0.0)


def s1b_monthly_gate(close):
    return monthly_above_sma(close, P["monthly_sma"]).fillna(0.0)


def s2_pullback(close):
    sg = signals(close)
    pos, cur = [], 0.0
    for e, x in zip(sg["entry"].values, sg["exit"].values):
        if cur == 0.0 and e:
            cur = 1.0
        elif cur == 1.0 and x:
            cur = 0.0
        pos.append(cur)
    return pd.Series(pos, index=close.index)


def _iv(rv, put=False):
    return max(P["iv_floor"], P["iv_mult"] * rv) + (P["put_skew"] if put else 0.0)


def s3_put_credit_spread(close):
    """Model-priced. Enter on the S2 entry signal, one spread at a time, risk 2% of equity."""
    sg, rv = signals(close), realized_vol(close)
    px, hs = close.values, P["opt_half_spread_frac_spot"]
    equity, eq, trade, trades = [], 1.0, None, []
    for i in range(len(px)):
        S, r = px[i], rv.iloc[i]
        if trade is not None:
            trade["age"] += 1
            T = (P["s3_dte"] - trade["age"]) / 252
            sig = _iv(r, True) if r == r else 0.2
            val = bs.price("p", S, trade["Ks"], T, sig) - bs.price("p", S, trade["Kl"], T, sig)
            close_now = (T <= 0) or (val <= trade["credit"] * (1 - P["s3_take_profit"])) or (not sg["gate"].iloc[i])
            if close_now:
                cost = 2 * hs * S
                pnl = trade["n"] * (trade["credit"] - val - cost)
                eq = trade["eq0"] + pnl
                trades.append({"pnl": pnl / trade["eq0"]})
                trade = None
            else:
                equity.append(trade["eq0"] + trade["n"] * (trade["credit"] - val))
                continue
        if trade is None and sg["entry"].iloc[i] and r == r:
            T, sig = P["s3_dte"] / 252, _iv(r, True)
            Ks = bs.strike_for_delta("p", P["s3_short_delta"], S, T, sig)
            Kl = Ks * (1 - P["s3_width_frac"])
            credit = bs.price("p", S, Ks, T, sig) - bs.price("p", S, Kl, T, sig) - 2 * hs * S
            max_loss = (Ks - Kl) - credit
            if credit > 0 and max_loss > 0:
                trade = dict(Ks=Ks, Kl=Kl, credit=credit, age=0, eq0=eq, n=P["s3_risk_frac"] * eq / max_loss)
        equity.append(eq if trade is None else trade["eq0"])
    e = pd.Series(equity, index=close.index)
    expo = pd.Series(0.0, index=close.index)  # exposure proxy left empty for option strategies
    return e, trades, expo


def s4_itm_call(close):
    """Model-priced 0.80-delta long-dated call held while the daily gate is on; rolled near expiry."""
    sg, rv = signals(close), realized_vol(close)
    px, hs = close.values, P["opt_half_spread_frac_spot"]
    equity, eq, pos, trades, held = [], 1.0, None, [], []
    for i in range(len(px)):
        S, r = px[i], rv.iloc[i]
        sig = _iv(r) if r == r else 0.2
        if pos is not None:
            pos["age"] += 1
            T = (P["s4_dte"] - pos["age"]) / 252
            C = bs.price("c", S, pos["K"], T, sig)
            eq_now = pos["cash"] + pos["n"] * C
            gate_on = sg["gate"].iloc[i]
            if (not gate_on) or (P["s4_dte"] - pos["age"] <= P["s4_roll_at"]):
                eq_now -= pos["n"] * hs * S
                trades.append({"pnl": eq_now / pos["eq0"] - 1})
                eq, pos = eq_now, None
                if gate_on and r == r:  # roll
                    pass
            else:
                eq = eq_now
        if pos is None and sg["gate"].iloc[i] and r == r:
            T = P["s4_dte"] / 252
            K = bs.strike_for_delta("c", P["s4_delta"], S, T, sig)
            C = bs.price("c", S, K, T, sig)
            n = eq / (S * bs.delta("c", S, K, T, sig))          # ~1x delta-adjusted exposure
            cash = eq - n * C - n * hs * S
            pos = dict(K=K, n=n, cash=cash, age=0, eq0=eq)
            eq = cash + n * C
        equity.append(eq)
        held.append(0.0 if pos is None else 1.0)
    return pd.Series(equity, index=close.index), trades, pd.Series(held, index=close.index)


def build_all(close):
    """name -> (equity, trades, exposure)"""
    out = {}
    for name, fn in (("S0 buy&hold", s0_buy_hold), ("S1a daily 200d gate", s1a_daily_gate),
                     ("S1b monthly 10m gate", s1b_monthly_gate), ("S2 gate+RSI2 pullback", s2_pullback)):
        out[name] = run_positions(close, fn(close), P["cost_bps_underlying"])
    out["S3 put credit spread*"] = s3_put_credit_spread(close)
    out["S4 0.80d ITM call*"] = s4_itm_call(close)
    return out
