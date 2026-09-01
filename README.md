> **A strategy branch of [trading-experiments](../../tree/main).** This page is the complete
> write-up for one strategy. The shared backtest harness, setup instructions, the head-to-head
> benchmark across every signal/traded-pair strategy, and the execution notes all live on
> [`main`](../../tree/main) — this branch has that same code, it just leads with the strategy
> instead.
>
> Other strategies: [Donchian + Aroon](../../tree/strategy/donchian-aroon) &middot; [SMA + Momentum](../../tree/strategy/sma-momentum) &middot; [Seykota](../../tree/strategy/seykota) &middot; [EMA9 / RSI14](../../tree/strategy/ema-rsi-meanrev) &middot; [HMM regime](../../tree/strategy/hmm-regime) &middot; [Sentiment (design)](../../tree/strategy/sentiment)

# MAG7 overnight — buy the close, sell the open

Implementation: [`strategies/mag7_overnight.py`](strategies/mag7_overnight.py)
Benchmark harness: [`run_mag7_overnight.py`](run_mag7_overnight.py)
Tests: [`tests/test_new_strategies.py`](tests/test_new_strategies.py)

> [!IMPORTANT]
> **Benchmarked, with a split verdict.** Numbers are in [§4](#4-results). Gross of costs this is
> the best risk-adjusted return anywhere in this repo — **Sharpe 1.41, 24.5% CAGR**. Net of the
> repo's 5 bps/side, charged on both legs of every night, it is **−0.12 and −3.3%**. The leg
> breaks even at **4.6 bps/side**, so the sign of the headline is decided by the cost assumption
> rather than by the signal, and both are reported side by side.
> [§3](#3-what-the-cost-model-alone-already-tells-us) computed that cost arithmetic *before* the
> run and predicted this outcome almost exactly; §4 is where the prediction gets tested.

---

## Contents

- [1. The strategy](#1-the-strategy)
- [2. Why overnight: the research this is built on](#2-why-overnight-the-research-this-is-built-on)
- [3. What the cost model alone already tells us](#3-what-the-cost-model-alone-already-tells-us)
- [4. Results](#4-results)
- [5. Account mechanics: the GFV problem this strategy has that the others don't](#5-account-mechanics-the-gfv-problem-this-strategy-has-that-the-others-dont)
- [6. Limitations and risks](#6-limitations-and-risks)
- [7. Possible refinements (not implemented)](#7-possible-refinements-not-implemented)

---

## 1. The strategy

**Buy each MAG7 name at today's close. Sell it at tomorrow's open. Every name, every trading
night.** MAG7 (the "Magnificent Seven") is Apple, Microsoft, Alphabet, Amazon, Nvidia, Meta, and
Tesla — the seven mega-cap US tech names whose combined weight now dominates S&P 500 returns.

$$r^{\text{overnight}}_{i,t} = \frac{O_{i,t+1}}{C_{i,t}} - 1$$

for name $i$, where $C_{i,t}$ is today's close and $O_{i,t+1}$ is tomorrow's open. The portfolio
return each night is the **equal-weight mean across whichever names are actually listed** that
night:

```python
def overnight_returns(ohlc: pd.DataFrame) -> pd.Series:
    open_next = ohlc["Open"].shift(-1)
    ret = open_next / ohlc["Close"] - 1.0
    return ret.iloc[:-1]          # no fabricated return for a trade that hasn't happened yet
```

There is no indicator, no filter, and no `DEFAULTS` to tune (`strategies/mag7_overnight.py`'s
`DEFAULTS` is intentionally empty) — the position is on every single night, unconditionally, for
every name. That is both the whole strategy and, as §5 and §6 argue, most of its problem.

### Why this needed its own harness

Every other strategy in this repo reads a trend off one **signal** instrument and expresses it in
one **traded** instrument, scored by `run_benchmark.py`'s `run(signal, traded, warmup, **params)`
interface. This strategy trades a **basket of seven individual names** on a schedule, with no
signal/traded split at all, so it does not fit that interface. `common/data.py` gained
`fetch_ohlc()` and `load_ohlc_universe()` (Open + Close, per ticker, each on its own index —
deliberately NOT forced onto a common date range, because Meta didn't exist before its May 2012
IPO and truncating six other names' history to match it would throw away years of data for no
reason). `run_mag7_overnight.py` is the resulting standalone entry point.

### A convention this branch breaks, on purpose

Every other strategy in this repo books, on day $t$'s row, a return fully determined by data up to
and including day $t$'s close. This strategy cannot do that — an overnight return, by definition,
is not finalized until the following morning's open. Row $t$ here means "the trade entered at
$t$'s close," not "the profit realized by $t$'s close." This is stated explicitly rather than left
implicit, because it is exactly the kind of convention shift a no-look-ahead test needs to know
about: `tests/test_new_strategies.py::test_mag7_overnight_no_lookahead` proves that truncating the
input series changes nothing about returns already computed — the decision to trade never depends
on anything beyond today's close, only the SETTLEMENT of that decision does.

---

## 2. Why overnight: the research this is built on

This is not a novel observation. It is one of the most persistently documented patterns in modern
equity market microstructure, usually filed under "overnight drift" or the "overnight/intraday
return decomposition":

- **Nearly all of the US market's long-run return has come from the close-to-open window, not the
  trading session.** Multiple independent studies, across different sample periods, find that
  cumulative overnight returns dramatically exceed cumulative intraday returns for US stocks —
  one commonly cited figure puts the gap at roughly **7 percentage points a year** between the two
  windows, averaged over decades. The academic shorthand for this literature is Lou, Polk &
  Skouras's **"Tug of War"** framing (overnight and intraday returns pulling in opposite
  directions) and the New York Fed's own **"Overnight Drift"** research note.
- **Momentum, specifically, has been shown in some studies to accumulate almost entirely
  overnight**, with the intraday session contributing close to nothing to (and in some samples
  detracting from) a momentum strategy's return. If a version of that effect is present in MAG7 —
  names with enormous momentum-driven flow, heavy pre-market futures and options positioning, and
  after-hours earnings reactions — it would show up as exactly the overnight/day-session split
  `run_mag7_overnight.py` computes and reports side by side.
- **Plausible mechanisms, not settled science**: scheduled news concentrated outside market hours
  (most large US companies report earnings before the open or after the close — see the Glossary's
  **earnings reaction** entry), overnight index-futures repricing that gets marked into the opening
  auction, ETF and index-fund rebalancing flow that executes at the open, and a retail
  attention/order-flow effect where buy pressure concentrates disproportionately at the open.
  These are documented correlates in the literature, not a single agreed-upon causal story.
- **The effect is unevenly distributed and reportedly linked to firm-specific investor
  sentiment and attention** — exactly the profile of MAG7: the most-followed, most-quoted,
  most-discussed stocks in the market, which is the a priori reason to test this basket rather
  than a random seven names.

**The honest caveat, stated as plainly as the finding.** This anomaly is decades old, extensively
published, and squarely inside what a well-resourced closing-auction desk already trades — it is
not an obscure inefficiency. Whatever edge existed at a 2005 sample size has had twenty years to
be arbitraged down, especially in the single most liquid, most closely watched names in the
market. Nothing here argues MAG7 overnight is *currently* profitable net of costs; §3 argues the
opposite is the more likely prior at this repo's assumed cost level, absent a backtest that says
otherwise.

**Further reading** (found via general web search during this session, not fetched into the
repo):

- [Night Moves: Is the Overnight Drift the Grandmother of All Market Anomalies? — Elm Wealth](https://elmwealth.com/night-moves-overnight-drift/) — the most readable overview, summarizing the Lou/Polk/Skouras and NY Fed work.
- [Strikingly Suspicious Overnight and Intraday Returns (arXiv)](https://arxiv.org/pdf/2010.01727) — a skeptical look at how much of the effect may be a market-microstructure artifact rather than a tradeable premium.
- [Does Overnight News Explain Overnight Returns? (arXiv)](https://arxiv.org/html/2507.04481v1) — recent (2025) work directly testing the news-driven mechanism.
- [Intraday and overnight return anomalies: evidence from 11.6 million price observations — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612325018926) — a large, recent cross-sectional study.

---

## 3. What the cost model alone already tells us

No backtest is needed to compute this — it follows directly from `COST_PER_SIDE = 0.0005` (5 bps,
`common/engine.py`) and the mechanics of trading every name every night.

This strategy enters at the close **and** exits at the open, every single night, for every name —
**two chargeable sides per name per night**, not the ~1–8 round trips *per year* the rest of this
repo's strategies incur. At the repo's standard cost assumption:

$$\text{daily drag} = 2 \times 5\text{ bps} = 10\text{ bps} = 0.10\%$$

Compounded over a 252-day trading year, with **zero assumed gross overnight edge**:

$$(1 - 0.0010)^{252} - 1 \approx -22.3\%\ \text{per year}$$

That is the return this strategy would post if the overnight effect from §2 were exactly zero for
MAG7 — cost alone would cost roughly a fifth of the account annually. Set against that, the
commonly cited aggregate market-wide overnight effect (≈7%/year, §2) is **smaller than the cost
drag this repo's cost model implies for daily round-tripping.** For this strategy to be
cost-positive at 5 bps/side, MAG7's overnight edge would need to run several times the documented
market-wide average, or realistic execution costs on these specific highly-liquid names would need
to run well below the repo's blanket 5 bps/side assumption (plausible — AAPL/MSFT/NVDA spreads are
often a fraction of a cent relative to price — but not something to assume without checking).

**This is exactly the kind of number a backtest is for.** The arithmetic above bounds the
best case a reader should expect before running one; it is not a substitute for actually running
`run_mag7_overnight.py` and reading off the real Sharpe, CAGR, and per-ticker breakdown once data
is available. Section 7 below discusses cost-reduction ideas (a signal to skip low-conviction
nights, cheaper broker execution) that this repo intentionally does not implement, so that the
unfiltered result is what gets reported first.

---

## 4. Results

Generated by `python run_mag7_overnight.py --write` on 2026-09-01. 3,937 nights,
2011-01-03 → 2026-08-28, 5 bps/side charged on **both** legs of every night, equal-weighted
across whichever names had listed.

| Leg | Sharpe | IS | OOS | CAGR | Vol | Max DD | Growth |
|---|---|---|---|---|---|---|---|
| **MAG7 overnight** (close → open) | **−0.12** | 0.04 | −0.27 | −3.3% | 16.5% | −59.5% | 0.60× |
| *Day session — the hours this skips* | −0.74 | −1.16 | −0.35 | −16.5% | 21.3% | −94.8% | 0.06× |
| *Buy & hold the basket, equal-weight* | **1.22** | 1.34 | 1.15 | 33.6% | 26.7% | −49.4% | 92.8× |
| *Buy & hold **SPY** (S&P 500)* | 0.87 | 0.94 | 0.82 | 14.2% | 17.0% | −33.7% | 8.0× |

SPY is the outside reference; the MAG7 basket is not one, being seven of the largest growth names
in the best decade they ever had. It scores 0.87 here against 0.94 in
[`results/benchmark.md`](results/benchmark.md) because this harness begins in 2011 and the pair
harness in 2012 — different windows, not a contradiction.

### §3's prediction, tested

§3 computed — before any data existed — that this strategy pays **22.3%/year** in costs, and
concluded that to be cost-positive "MAG7's overnight edge would need to run several times the
documented market-wide average" of ≈7%/year. That is precisely what happened. It was still not
quite enough:

| Leg | Sharpe | CAGR | Growth |
|---|---|---|---|
| Overnight, **gross** of costs | **1.41** | **24.5%** | 30.5× |
| Overnight, net of 10 bps/night | −0.12 | −3.3% | 0.60× |
| Day session, gross | 0.44 | 7.4% | 3.06× |
| Day session, net | −0.74 | −16.5% | 0.06× |

The gross overnight edge is **24.5%/year — about three and a half times the market-wide ≈7%** —
at a gross Sharpe of **1.41**, the best risk-adjusted number in this repo by a wide margin. Costs
take it to −0.12. **The leg breaks even at 4.6 bps/side against the 5 bps charged**: it misses by
0.4 of a basis point. §3's arithmetic was not merely directionally right, it was nearly exact.

Against SPY the asymmetry is sharper still. Over the same 3,937 nights, **gross, the overnight leg
returned 30.5× to the S&P 500's 8.0× — roughly four times the index — while the day session
returned 3.06× and *underperformed* it.** Whatever compensates investors in these names, it was
paid out between the closing bell and the opening one.

### The decomposition is exact

The two gross legs multiply back to buy-and-hold: **30.5× (nights) × 3.06× (days) = 93.4×**,
against the basket's own **92.8×**. That is the arithmetic check that the two sessions tile the
period with nothing double-counted or dropped — and it carries the real finding:

> **Essentially all of the Magnificent Seven's fifteen-year return arrived overnight.** The day
> session — the hours everyone actually watches — turned one dollar into 3.06 gross, while the
> nights turned it into 30.51.

![MAG7 overnight against the day session it skips and buy-and-hold the basket, gross and net](results/charts/mag7_sessions.png)

### Per ticker

Net of the same 10 bps a night:

| Ticker | Overnight Sharpe | Overnight CAGR | Nights |
|---|---|---|---|
| NVDA | **0.45** | 8.9% | 3,937 |
| TSLA | **0.43** | 9.4% | 3,937 |
| AMZN | −0.01 | −2.8% | 3,937 |
| META | −0.16 | −8.0% | 3,590 (from 2012-05-18) |
| GOOGL | −0.55 | −11.1% | 3,937 |
| AAPL | −0.70 | −13.7% | 3,937 |
| MSFT | −0.77 | −13.2% | 3,937 |

The dispersion is the point: two names clear costs and five do not, so the basket average hides a
wide spread — the concern §6 raises, confirmed. Nothing here suggests those two were identifiable
in advance, and a strategy that needed to pick them is a different strategy.

Reproduce with:

```bash
python run_mag7_overnight.py --write                    # the table above
python run_mag7_overnight.py --tickers AAPL MSFT NVDA   # any basket
```

---

## 5. Account mechanics: the GFV problem this strategy has that the others don't

Every other strategy branch in this repo argues that low turnover is an operational advantage for
a small **cash account** (see the Donchian+Aroon branch's §4, and the **T+1 settlement** / **GFV**
glossary entries). This strategy is the opposite case, and worth stating plainly because it
undercuts the strategy's practicality independent of whether the underlying return edge is real.

Selling in the morning does not produce usable cash until settlement, one business day later
(**T+1**). Buying again that same evening — which this strategy does, every single night —
therefore uses **unsettled proceeds from the position just sold**, if the account is a cash
account. That is the textbook definition of a **Good Faith Violation**, and this strategy commits
one on every single trading day it runs, not occasionally under specific conditions the way a
low-turnover trend follower might. Repeated GFVs get a cash account restricted to settled-cash-only
trading, which would halt the strategy entirely. This is not a subtle edge case — it is the
strategy's default behavior, every night, by construction.

(Selling in the morning and buying again that evening is *not* a same-day round trip on the SAME
security in the PDT sense — the buy and sell of a given name are always on different calendar
days here — so **Pattern Day Trader** rules specifically do not apply. GFV is the actual
constraint, not PDT.)

**Practical implication:** this strategy, as specified, is not viable in a small cash account of
the kind this repo's other branches target (~$200, see the Donchian+Aroon write-up). It needs
either a margin account (which changes the risk profile — margin can be called) or a broker/account
structure where next-day settlement is not a binding constraint. This alone may be reason enough to
not run it as specified, independent of what the eventual backtest says about gross returns.

---

## 6. Limitations and risks

**The result is a cost verdict, not a signal verdict (§4).** The overnight edge on this basket is
real and large gross; what the backtest establishes is that this repo's 5 bps/side assumption
consumes it, with 0.4 bps to spare. Anyone with a different cost model gets a different sign, so
the number to argue with is the cost assumption, not the Sharpe.

**The literature's effect is measured on the broad market, aggregated over decades — not on a
7-name basket over a specific, recent window.** Even if the overnight anomaly is real in
aggregate, seven names is a small, concentrated sample, and MAG7's own history (five separate
IPO/founding eras, wildly different growth phases, a period where "MAG7" was not yet a coherent
concept investors traded as a group) means the basket's overnight behavior in 2012 tells you very
little about its behavior in 2025.

**Earnings-driven overnight moves are fat-tailed, not smoothly distributed.** A handful of nights
a year — the nights after MAG7 earnings releases — plausibly account for a large share of any
edge or any loss. A strategy that is unconditionally long every night is fully exposed to that
tail in both directions, with no way to reduce size going into a known catalyst. This is a much
more concentrated risk profile than the smooth daily exposure the headline exposure/day count
implies.

**Gap risk is structural, not incidental, to this strategy.** Every single trade this strategy
makes is a bet held through a period with no opportunity to react — that is what "overnight" means.
A stop-loss cannot protect against a gap; see **Gap risk** in the Glossary. The other strategies in
this repo hold overnight too, incidentally, as a side effect of a multi-day position; this strategy
holds overnight *by design and only overnight*, so gap risk is not a tail case here, it is the
entire mechanism.

**The 5 bps/side cost assumption may be wrong in either direction for this use case.** It could be
too pessimistic (MAG7 names are among the most liquid stocks that exist, with spreads often a
fraction of a cent) or too optimistic (a market-on-close or market-on-open order participates in an
**auction**, not continuous trading, and auction execution quality — especially around news —
is its own subject, not necessarily well modeled by a flat continuous-market cost figure). This
is explicitly flagged rather than resolved, since resolving it needs either real fill data or a
much more careful microstructure model than this repo attempts anywhere else.

**Survivorship and basket composition.** "MAG7" is a retrospectively-applied label — it names
seven companies that turned out to be huge winners over the last decade. Backtesting *today's*
MAG7 list over the *past* 15 years bakes in the very survivorship this repo's methodology
otherwise tries to avoid (see **Survivorship bias** in the Glossary); Tesla and Nvidia, in
particular, would not obviously have been included in a "mega-cap tech basket" chosen in 2012.
Any real backtest of this strategy should be read with that in mind, not as a criticism unique to
this branch — it is a standard, hard-to-avoid limitation of testing any concept defined by its own
survivors.

**No slippage/impact modeling beyond the flat cost.** As with every strategy in this repo, execution
is assumed to happen exactly at the printed Open or Close, net of the flat cost — no modeling of
partial fills, of the strategy's own trading moving the auction price, or of days the strategy
would be unable to fill entirely.

---

## 7. Possible refinements (not implemented)

Kept here as an honest list of what was deliberately left out, not as a promise of a better
version. Adding any of these would also mean re-deciding the cost model and re-running everything
from §4:

- **A conviction filter** — trade only when some signal (prior-day return, realized volatility,
  proximity to an earnings date) suggests the overnight edge is more likely present, cutting the
  ~22%/year cost drag from §3 by trading less often. Now measurably the highest-leverage change
  available: §4 misses breakeven by 0.4 bps/side, so any filter that raises the average
  per-night edge without proportionally shrinking the number of nights flips the sign.
- **Skip nights before scheduled earnings releases**, or conversely, deliberately concentrate
  exposure around them — the direction of that choice is itself an empirical question this repo
  has not answered.
- **Dispersion-aware weighting** instead of flat equal weight, since a basket average can mute a
  real effect concentrated in a subset of names.
- **A wider or different universe** — testing whether an "overnight effect" is MAG7-specific or a
  general large-cap phenomenon, by comparing against a random same-size basket or the S&P 500
  overnight/day-session split as a control.

---

## Glossary

Abbreviations used on this page. The repo-wide list, covering every term used anywhere in this
project, is in [`GLOSSARY.md`](GLOSSARY.md) — it is available on every branch.

| Term | Definition |
|---|---|
| **MAG7 / Magnificent Seven** | Apple, Microsoft, Alphabet, Amazon, Nvidia, Meta, Tesla. |
| **Overnight return** | The return from one day's close to the next day's open. |
| **Intraday / day-session return** | The complementary return, from a day's open to that day's close. |
| **Overnight drift** | The documented finding that most of the US market's long-run gain has accrued overnight rather than intraday. |
| **MOC / MOO order** | Market-On-Close / Market-On-Open — an order that fills at the closing or opening auction price. |
| **Closing / opening auction** | A batch process that matches all submitted orders into one official open or close print, distinct from continuous trading. |
| **Gap risk** | The risk of a sharp price move between one session's close and the next session's open, with no chance to react — a stop-loss cannot protect against it. |
| **T+1 settlement** | Proceeds from a sale become usable cash one business day later. |
| **GFV** (Good Faith Violation) | In a cash account, buying with unsettled proceeds and selling again before settlement; repeated violations get the account restricted. |
| **PDT** (Pattern Day Trader) | A US rule restricting frequent SAME-DAY round trips in accounts below a balance threshold — does not apply here, since this strategy's buy and sell of a given name are always on different calendar days. |
| **Earnings reaction** | The price move following a company's quarterly results, typically released outside market hours — i.e. overnight. |
| **Dispersion (cross-sectional)** | How much individual names' returns differ from each other on a given day, as opposed to the basket average. |
| **Sharpe ratio** | Return per unit of volatility, at a 0% risk-free rate. ~1.0 is respectable. |
| **CAGR** | Compound Annual Growth Rate — the average yearly compounded return. |
| **Max DD (drawdown)** | Worst peak-to-trough decline. |
| **bps** | Basis points — hundredths of a percent. 5 bps = 0.05%. |
| **IS / OOS** | In-sample vs out-of-sample; see `common/metrics.py` and the main README's methodology section. |
| **Survivorship bias** | Drawing conclusions from only the things that survived, which systematically flatters results. |
