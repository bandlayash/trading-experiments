# trading-experiments

Open research notes on **trend-following strategies**, with a reproducible backtest harness.

Every number published here is produced by `python run_benchmark.py --write` from the code in
this repo — nothing is hand-copied. If you disagree with a result, you can rerun it and say so
with evidence.

> [!IMPORTANT]
> **This is research, not a trading system, and not financial advice.** Nothing here is wired to
> a broker. The execution artifacts under [`deploy/`](deploy/) are deliberately pseudocode and
> placeholders. Backtests are a measurement of the past under stated assumptions; they are not a
> forecast. Leveraged instruments appear throughout and the drawdowns are severe.

---

## The three strategies

Each strategy gets its own branch with a full write-up — the strategy, the math, expected
results, recommended setup, and the research behind it.

| Branch | Strategy | One-line summary |
|---|---|---|
| [`strategy/donchian-aroon`](../../tree/strategy/donchian-aroon) | **Donchian breakout + Aroon filter** | Buy above the 50-day high, sell below the 63-day low, gated by an Aroon trend filter |
| [`strategy/sma-momentum`](../../tree/strategy/sma-momentum) | **200-day SMA + 12-month momentum** | Hold while price is above its 200-day average *and* the 12-month return is positive |
| [`strategy/seykota`](../../tree/strategy/seykota) | **Seykota ATR risk-sizing** | 50/200 EMA trend, position sized to risk 2% of equity at an ATR stop, ATR trailing exit |

`main` holds the shared harness, all three implementations, and the head-to-head benchmark.
The strategy branches add their deep-dive `STRATEGY.md` on top.

---

## Headline results

Signal read from **SMH** (VanEck Semiconductor ETF), expressed in **SOXL** (3× semiconductors).
2012-01-03 → 2026-08-05, 3,668 trading days, 5 bps/side costs, Sharpe at a 0% risk-free rate.
In-sample is before 2020-01-01; out-of-sample is 2020 onward.

| Strategy | Sharpe | IS | OOS | CAGR | Vol | Max DD | Growth | Exposure | Round trips/yr |
|---|---|---|---|---|---|---|---|---|---|
| **Donchian + Aroon** | **0.90** | 0.86 | 0.97 | 46.6% | 71.8% | −75.7% | 262× | 79% | 0.9 |
| SMA + Momentum | 0.81 | 0.86 | 0.83 | 38.0% | 71.7% | −74.2% | 108× | 76% | 4.0 |
| Seykota (ATR-sized) | 0.49 | 0.52 | 0.49 | 5.2% | 11.7% | **−16.1%** | 2.1× | 12% | 6.1 |
| *Buy & hold SOXL* | 0.90 | 1.05 | 0.85 | 49.1% | 91.8% | −90.5% | 335× | 100% | — |
| *Buy & hold SMH* | **1.02** | 1.08 | 1.05 | 29.7% | 29.8% | −45.3% | 44× | 100% | — |

Four-year sub-period Sharpe, as a consistency check across regimes:

| Strategy | 2012–2015 | 2016–2019 | 2020–2023 | 2024–2027 |
|---|---|---|---|---|
| Donchian + Aroon | 0.71 | 0.99 | 0.88 | 1.09 |
| SMA + Momentum | 0.63 | 1.05 | 0.66 | 1.05 |
| Seykota | 0.23 | 0.76 | 0.46 | 0.53 |
| *Buy & hold SMH* | 0.92 | 1.22 | 0.82 | 1.39 |

Full generated output: [`results/benchmark.md`](results/benchmark.md).

### What these results actually say

Read in one sitting, the honest conclusions are less exciting than the top row suggests:

- **Nothing here beat buy-and-hold SMH on Sharpe (1.02).** Every leveraged strategy bought CAGR
  with a more-than-proportional increase in drawdown. If risk-adjusted return is your objective,
  the unleveraged index won this test.
- **The Donchian result is the good corner of its parameter neighbourhood, not its centre.**
  Across the 48 nearby parameter sets the median Sharpe is 0.83, against 0.81 for the incumbent.
  Selecting parameters on the in-sample peak instead produced out-of-sample Sharpe of 0.68–0.71 —
  naive optimisation actively overfits on this data.
- **The robust findings are structural, not statistical:** the exit-channel length dominates
  everything else, and the breakout model trades ~4× less than the SMA model — which matters for a
  small cash account under T+1 settlement far more than the ~0.3%/yr of direct cost it saves.
- **The Aroon market filter did not earn its keep.** Implemented faithfully from the source post,
  it is mathematically inert whenever its lookback is ≤ the entry channel (a new *N*-day-high close
  pins AroonUp at 100, so it can never veto an entry). Configurations where it *does* bind scored
  worse (0.81 vs 0.90). The winning configuration is therefore effectively a pure Donchian
  breakout — a negative result about the filter, reported rather than buried.
- **Seykota's poor CAGR here is a mandate mismatch, not a refutation.** Its 2% risk rule is built
  for a diversified multi-market book; applied to one leveraged instrument it holds ~88% cash. It
  posted by far the best drawdown (−16.1%) of anything tested.

---

## Methodology

The parts that determine whether a backtest means anything:

- **No look-ahead.** Signals use data up to and including today's close; the resulting position
  earns **tomorrow's** return. Channel highs/lows are `.shift(1)`-ed so today's bar is never part
  of its own channel. Implemented once, in `common/engine.py`, rather than per strategy.
- **Identical scoring.** All strategies run on the same bars, the same warm-up (252 days), the
  same cost model, through the same metrics code. Differences in the table are differences in
  strategy, not in harness.
- **Costs.** 5 bps per side on every position change, modelling spread and slippage. These are
  liquid ETFs and commissions are zero at most retail brokers.
- **Data.** Split- and dividend-adjusted daily closes from Yahoo Finance via `yfinance`. SOXL has
  split repeatedly, so adjusted prices are mandatory — raw closes would fabricate huge losses.
- **Metrics.** Sharpe uses annualised arithmetic mean daily return over annualised daily standard
  deviation, at a 0% risk-free rate. CAGR is geometric. Max drawdown is on daily closes, so real
  intraday drawdowns were worse.
- **Cash earns 0%, and that is not neutral.** It penalises whichever strategy holds the most cash.
  Seykota sits ~88% in cash, so at a realistic 2–4% on idle balances its returns would improve
  materially while the near-fully-invested strategies would barely move. This does not change the
  ranking — the gap is far too large — but any comparison that turns on a few points of CAGR
  should re-run with `rf_annual` set appropriately.
- **Out-of-sample split.** 2012–2019 in-sample, 2020–2026 out-of-sample, reported separately
  everywhere. A strategy whose OOS half collapses was fitted, not discovered.

### Known limitations

- **One sector, one regime.** 2012–2026 was the best semiconductor decade in history. These
  results will not necessarily generalise, and certainly not repeat.
- **Daily-close fills.** No intraday modelling, no gap handling, no partial fills, no borrow.
- **Survivorship-free but narrow.** SMH and SOXL both existed for the whole window, so there is
  no survivorship bias — but a two-instrument test is not a broad study.
- **Leveraged-ETF decay.** SOXL resets 3× daily and bleeds in choppy tape. This is captured in
  the price data used, but it means naive "3× the index" intuitions do not apply.
- **Sharpe is a poor summary here.** These return distributions are fat-tailed and skewed; a
  single ratio hides a great deal. It is used because it was the stated selection criterion.

---

## Running it

```bash
git clone https://github.com/bandlayash/trading-experiments.git
cd trading-experiments
pip install -r requirements.txt

python run_benchmark.py                    # print the tables
python run_benchmark.py --write            # regenerate results/
python run_benchmark.py --signal SPY --trade SPY   # try another instrument pair
```

First run downloads price history and caches it under `data/cache/` (git-ignored). Later runs are
offline and fast; delete the cache to refresh.

Using a strategy directly:

```python
from common import load_pair, perf_stats
from strategies import donchian_aroon

signal, traded = load_pair("SMH", "SOXL")
result = donchian_aroon.run(signal, traded, exit_len=80)   # override any parameter
print(perf_stats(result.daily_ret))
```

Every strategy module exposes the same interface — `NAME`, `DEFAULTS`, and
`run(signal, traded, warmup=252, **params) -> StrategyResult` — so adding a fourth is a matter of
writing one file and adding it to `strategies/__init__.py`.

---

## Execution options

If you ever wanted to run something like this for real, [`deploy/`](deploy/) walks through the
realistic hosting choices — local cron, GitHub Actions, AWS Lambda, a small always-on VM, and
broker-native platforms — with the trade-offs of each, plus the operational requirements
(idempotency, position reconciliation, kill switch, alerting) that matter more than the host you
pick.

Those files are **pseudocode and templates by design**. This repo does not place orders.

---

## Repo layout

```
trading-experiments/
├── common/                 # shared harness — used identically by every strategy
│   ├── data.py             #   price loading + on-disk cache
│   ├── engine.py           #   result type, cost model, no-look-ahead convention
│   └── metrics.py          #   Sharpe / CAGR / drawdown / IS-OOS splits
├── strategies/
│   ├── donchian_aroon.py   #   breakout + Aroon filter
│   ├── sma_momentum.py     #   200-day SMA + 12-month momentum
│   └── seykota.py          #   EMA trend + ATR risk sizing
├── deploy/                 # execution options + placeholder runner (not live code)
├── results/                # generated: benchmark.md, summary.csv, equity_curves.csv
├── run_benchmark.py        # the head-to-head that produces results/
└── requirements.txt
```

---

## Contributing / disagreeing

Corrections are welcome, especially methodology bugs — a look-ahead leak or a cost assumption
that flatters a result is the most valuable thing anyone could find here. Open an issue with the
rerun output that demonstrates it.
