# CHYM — 10-session scenario model

Entry: open 2026-11-09. Exit: close 2026-11-20. Stage-2 conviction 55/100 (Fresh beat, accelerating revenue, relative strength; offset by valuation and fintech tape).

| Input | Value |
|---|---|
| Volatility (max of 60d, 1y), annual | 61.8% |
| 1-sigma move over 10 sessions | 12.3% |
| Beta to SPY (1y daily) | 1.82 |
| CAPM drift, 10 sessions (rf 4.00%, ERP 5%) | +0.52% |

| Scenario | Probability | 10-session return |
|---|---|---|
| Bear | 0.25 | -14.7% |
| Base | 0.50 | +0.9% |
| Bull | 0.25 | +16.6% |
| **Probability-weighted** | 1.00 | **+0.91%** |

## Red-team

Pre-critique, reading conviction literally as P(beat SPY), the alpha is +1.55% and the expected return +2.07%. The strongest argument that this is wrong: this branch's own backtest found no 10-day edge in the screen that produced this name, and a conviction score from one week of headlines has no track record. Alpha is cut to 25%: +0.39%, expected return +0.91%.

**Post-critique:** P(up after 10 sessions) ≈ 53%; 10th-90th percentile -14.9% to +16.7%. Key risk in window: Fintech regulatory headlines, high volatility; Stride deal news.
