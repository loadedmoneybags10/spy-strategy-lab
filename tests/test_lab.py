import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from math import exp
from lab import bs, strategies as st
from lab.engine import run_positions
from lab.metrics import summarize


def fake_prices(n=1500, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2005-01-03", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, n))), index=idx)


class Tests(unittest.TestCase):
    def test_no_lookahead_in_positions(self):
        """Changing FUTURE prices must not change any past position/signal."""
        c = fake_prices()
        cut = 1000
        c2 = c.copy()
        c2.iloc[cut:] *= np.linspace(1, 3, len(c) - cut)   # wreck the future
        for fn in (st.s1a_daily_gate, st.s1b_monthly_gate, st.s2_pullback):
            a, b = fn(c).iloc[:cut - 30], fn(c2).iloc[:cut - 30]
            pd.testing.assert_series_equal(a, b, check_names=False, obj=fn.__name__)

    def test_no_lookahead_in_option_equity(self):
        c = fake_prices()
        cut = 1000
        c2 = c.copy()
        c2.iloc[cut:] *= 2
        for fn in (st.s3_put_credit_spread, st.s4_itm_call):
            a, b = fn(c)[0].iloc[:cut - 1], fn(c2)[0].iloc[:cut - 1]
            pd.testing.assert_series_equal(a, b, check_names=False, obj=fn.__name__)

    def test_engine_delays_one_bar(self):
        c = fake_prices(50)
        pos = pd.Series(1.0, index=c.index)
        eq, _, _ = run_positions(c, pos, cost_bps=0)
        # first bar has no position (decided at close of day 0), so equity starts flat
        self.assertAlmostEqual(eq.iloc[0], 1.0)
        self.assertAlmostEqual(eq.iloc[-1], c.iloc[-1] / c.iloc[0], places=9)

    def test_costs_reduce_equity(self):
        c = fake_prices(300)
        pos = pd.Series(([1.0] * 5 + [0.0] * 5) * 30, index=c.index)
        e0 = run_positions(c, pos, 0)[0].iloc[-1]
        e1 = run_positions(c, pos, 5)[0].iloc[-1]
        self.assertLess(e1, e0)

    def test_put_call_parity_and_delta_solver(self):
        S, K, T, sig = 100, 95, 0.5, 0.2
        self.assertAlmostEqual(bs.price("c", S, K, T, sig) - bs.price("p", S, K, T, sig), S - K, places=9)
        for kind, tgt in (("c", 0.8), ("p", 0.2)):
            k = bs.strike_for_delta(kind, tgt, S, T, sig)
            self.assertAlmostEqual(abs(bs.delta(kind, S, k, T, sig)), tgt, places=4)

    def test_metrics_known_series(self):
        idx = pd.bdate_range("2020-01-01", periods=253)
        eq = pd.Series(np.linspace(1, 1.1, 253), index=idx)
        m = summarize(eq)
        self.assertAlmostEqual(m["max_dd"], 0.0)
        self.assertGreater(m["cagr"], 0.09)

    def test_gate_only_long_above_sma(self):
        c = fake_prices()
        pos = st.s1a_daily_gate(c)
        sma200 = c.rolling(200).mean()
        self.assertTrue(((pos == 1) == (c > sma200)).iloc[200:].all())


if __name__ == "__main__":
    unittest.main()
