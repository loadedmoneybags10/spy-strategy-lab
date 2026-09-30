# spy-strategy-lab

Backtest harness that runs every candidate strategy on identical data, dates and costs, and prints one table.

    python -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python -m unittest discover -s tests -v     # look-ahead + engine + pricing tests
    .venv/bin/python run_all.py                           # dev period, bundled proxy data
    .venv/bin/python run_all.py --csv SPY.csv             # real SPY export (Date, Close/Adj Close)
    .venv/bin/python run_all.py --holdout --csv SPY.csv   # once only; writes results/holdout_lock.json

Read `rules.md` first. Option strategies (S3, S4) are Black-Scholes model prices, good for ranking ideas only.
