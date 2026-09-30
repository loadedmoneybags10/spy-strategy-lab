# Frozen rules (written before any results were looked at)

Change a rule only by adding a new dated variant below and counting it as a new trial.

Data: daily closes. Signals are computed after the close; the position applies from the next bar.
Weekly/monthly values are visible only after that week/month has closed.

| ID | Rule |
|----|------|
| S0 | Buy and hold (benchmark). |
| S1a | Long when close > 200-day SMA, else cash. |
| S1b | Long when last completed month-end close > 10-month SMA of month-end closes, else cash. |
| S2 | Gate = close > 200d SMA and 10-week SMA rising. Enter when gate and RSI(2) < 10. Exit when close > 5d SMA or gate off. |
| S3 | On the S2 entry signal, sell a 25-trading-day put credit spread: short ~0.20 delta, long 5% below. Risk 2% of equity. Close at 50% of credit, gate off, or expiry. Model-priced. |
| S4 | While the daily gate is on, hold a ~0.80 delta call with 190 trading days to expiry; roll at 42 days left; sell when gate off. Model-priced. |
| S5 | Vol-spike bounce. Not implemented: needs VIX history. |

Split: dev = start..2010-12-31. Holdout = 2011-01-01..end. Holdout is run once (`--holdout`), then locked.

Pass criteria (set now, before results): beats S0 on max drawdown AND on Sharpe/Calmar out of sample,
with at least 30 trades (S1b/monthly excepted, labelled "cannot tell" if fewer). Anything else = fail or "cannot tell".
Costs and slippage are on for every test.

Known weaknesses of the data used so far: the bundled proxy is a price index (no dividends, cash earns 0),
ends in 2018, and its dev period (1999-2010) is a flat "lost decade" that flatters trend filters.
The real test needs SPY daily data through today.
