# Short-horizon run — buy at the open 2026-11-09, sell by the close 2026-11-20

> [!WARNING]
> **Research and modelling only, not financial advice. Expectations are not guarantees.**
> As of the close on **Friday 2026-11-06**. A screen like this goes stale quickly: re-run it
> before acting on it on any later date.

## 1. The answer in one table

| | Selected 3-name sleeve | Just hold SPY |
|---|---|---|
| Picks (weight) | ABNB 32% · XYZ 30% · ATI 38% | SPY 100% |
| Modelled expected return, 10 sessions | +0.87% | +0.36% |
| Modelled P(up after 10 sessions) | 56% | 55% |
| Modelled 10th–90th percentile | −6.7% to +8.5% | −3.1% to +3.8% |
| *Historical*: same basket, every 10-session window, last 2y | up 58% of windows, worst −20.5% | up 60%, worst −13.7% |
| *Historical*: basket beat SPY | 53% of windows | — |

**The honest reading.** The sleeve's modelled edge over SPY is about half a percent over two
weeks, and it comes from Stage-2 conviction scores that have never been validated. The
chance of the sleeve finishing up is about the same as SPY's, and the spread of outcomes is
roughly twice as wide. There is no version of this pipeline that can *ensure* a gain over
10 sessions: at this horizon a single large-cap stock finishes positive about 52% of the time
(§2).

## 2. What the 10-day backtest says (read this before the picks)

`pipeline/backtest_short_horizon.py`, the 1,000 largest exchange-listed US names, 50 non-overlapping
10-session windows from 2024-11-07 to 2026-10-23. Signal at the close, buy at the next open,
sell at the close 10 sessions later.

| Base rate (all names, all windows) | Value |
|---|---|
| Share of single stocks up after 10 sessions | 52.4% |
| Median / mean 10-session return | +0.5% / +0.8% |
| 10th / 90th percentile | −8.0% / +9.6% |
| SPY up after 10 sessions | 58% of windows |

| Top-10 basket by signal | Mean 10d return | Excess over universe | Basket up | Basket beat SPY |
|---|---|---|---|---|
| **Pre-specified composite** | +0.49% | −0.26% | 58% | **50%** |
| 12-1 momentum | +2.65% | +1.89% | 62% | 60% |
| Trend (above 50d, 50d above 200d) | +2.93% | +2.17% | 68% | 64% |
| 52-week-high proximity | +0.50% | −0.26% | 58% | 50% |
| 5-day reversal | +3.57% | +2.79% | 62% | 62% |
| Low volatility | +0.43% | −0.32% | 62% | 50% |

- The composite specified *before* the backtest ran had **no edge**: its top 10 beat SPY in
  exactly half the windows. Its quintile spread t-stat was −0.70.
- Trend and 12-1 momentum were the only components positive in both halves. Stage 1 was
  re-weighted onto them **after** seeing this, which is a data-snooping choice.
- The universe is *today's* largest companies, which is survivorship bias in favour of
  momentum and trend. Treat their numbers as an upper bound.
- Fifty windows is a small sample. Reversal's average came from the first half (+8.1%) and
  turned negative in the second (−0.9%).

## 3. How the run got from 1,000 names to 3

| Stage | In → out | What decided it |
|---|---|---|
| 1. Screen | 1,000 → 486 eligible → top 30 | Trend 0.35, 12-1 momentum 0.35, last earnings reaction 0.30 (post-earnings drift). Excluded: earnings inside the window (65), 60-day vol > 50% (160), avg volume < 1M (162), price outside $5–$400 (92), < 1y history (20) |
| 2. News, bull vs bear | 30 → 8 advance | 7-day dated news only. Dropped: a pending/closed acquisition (ROKU — the Fox deal completed 11-06), thin coverage (EAT, LTH, HAS, EXEL, MHK), and the energy/refiner group (MPC, PSX, VLO, DINO, APA, EQNR), whose sell-off on the election result and Iran-ceasefire crude unwind still looked unfinished |
| 3. Scenarios | 8 modelled | 10-session normal with σ from max(60d, 1y) vol, CAPM drift (rf 4.0%, ERP 5%), and alpha from conviction cut to 25% by the red-team |
| 4. Optimiser | 55 three-name combinations → 1 | Max 10-session Sharpe, weights 20–50%, ≥ 2 sectors, every pick with a positive expected return |

Stage-2 advancers (conviction / 100): ABNB 58, XYZ 58, BTSG 56, SN 56, ATI 56, TEVA 56,
CHYM 55, RPRX 55. Per-stock notes: [`stage2_adversarial/`](../stage2_adversarial/).
Scenario tables: [`stage3_scenarios/`](../stage3_scenarios/).

### Runners-up (all within noise of each other)

| Picks | Weights | 10d Sharpe | E[r] 10d | σ 10d |
|---|---|---|---|---|
| **ABNB, XYZ, ATI** | 32 / 30 / 38 | 0.120 | +0.87% | 5.9% |
| XYZ, BTSG, ATI | 40 / 20 / 40 | 0.115 | +0.87% | 6.2% |
| XYZ, ATI, TEVA | 40 / 39 / 21 | 0.115 | +0.83% | 5.9% |
| XYZ, SN, ATI | 41 / 20 / 39 | 0.114 | +0.88% | 6.3% |
| XYZ, ATI, RPRX | 37 / 37 / 25 | 0.114 | +0.77% | 5.3% |

The winner is not clearly better than the next four. XYZ and ATI appear in nearly every top
combination because they combine the highest convictions with low correlation to the rest.

## 4. The picks

| | ABNB — Airbnb | XYZ — Block | ATI — ATI Inc. |
|---|---|---|---|
| Listing | Nasdaq | NYSE | NYSE |
| Close 11-06 | 189.99 | 85.48 | 175.79 |
| Weight | 32% | 30% | 38% |
| Why it advanced | Fastest revenue growth in 3 years, raised guidance, $12B buyback (reported after the close 11-05, +11.7% on 11-06) | Strong beat; 2027 outlook should lift estimates; held its +15% earnings gap through a down week | Aerospace beat-and-raise (10-29, +5.9%), estimates rising, +6% more in a down week |
| Main risk in window | Gap partly priced; FX, AI-disruption narrative | Bitcoin sensitivity; fintech regulation under the new Congress; beta 1.8 | Market beta 1.6; aerospace supply-chain headlines |
| Modelled P(up), 10d | 54% | 54% | 53% |
| 10th–90th pct, 10d | −10% to +12% | −11% to +13% | −11% to +13% |

All three reported between 10-29 and 11-05, so the next quarterly report falls well after the window.

## 5. Execution notes

- **Order type.** Use limit orders near Friday's close, not market orders at 09:30. Opening
  prints after a news weekend can gap. All three names trade over 1.7M shares a day, so
  spreads should be tight once the open settles.
- **Exit.** The model is for a fixed 10-session hold: sell by the close on Friday 2026-11-20.
  Stops on a two-week hold mostly turn noise into realised losses. If you use one, set it
  outside the modelled 10th percentile (around −10% per name) rather than inside it.
- **Small accounts.** Whole-share rounding moves the weights; `stage4_optimize_short.py
  <run_dir> <capital>` prints a whole-share order list that keeps every name inside the
  20–50% band. Fractional shares match the weights exactly. The order list is printed only,
  so no account size is written into this repo.
- **Tax.** Gains on a two-week hold are short-term and taxed as ordinary income.

## 6. Limitations specific to this run

- **No validated edge.** See §2. The picks express a modest tilt, not a forecast.
- **Conviction is unvalidated.** Three reviewers scored 10 names each from one week of
  headlines, using a shared rubric. The scores cluster at 55–58, which is the honest range
  for this kind of information.
- **Market regime.** The week ending 11-06 was a risk-off week after the US election, with
  sector shocks in energy and diagnostics. Volatility estimates from calmer months may
  understate it.
- **Vendor timestamps.** Yahoo's earnings timestamps are sometimes placeholders. TEVA's said
  after the close on 11-03, but the reaction happened that same day. The earnings-reaction
  feature inherits these errors.
- **Survivorship.** The universe is today's largest companies, both in the backtest and in
  the screen.
