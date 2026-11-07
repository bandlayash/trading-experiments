# RPRX — 10-session scenario model

Entry: open 2026-11-09. Exit: close 2026-11-20. Stage-2 conviction 55/100 (Third straight guidance raise and Zacks upgrade; small edge after extended run).

| Input | Value |
|---|---|
| Volatility (max of 60d, 1y), annual | 24.4% |
| 1-sigma move over 10 sessions | 4.9% |
| Beta to SPY (1y daily) | 0.19 |
| CAPM drift, 10 sessions (rf 4.00%, ERP 5%) | +0.20% |

| Scenario | Probability | 10-session return |
|---|---|---|
| Bear | 0.25 | -5.8% |
| Base | 0.50 | +0.3% |
| Bull | 0.25 | +6.5% |
| **Probability-weighted** | 1.00 | **+0.35%** |

## Red-team

Pre-critique, reading conviction literally as P(beat SPY), the alpha is +0.61% and the expected return +0.81%. The strongest argument that this is wrong: this branch's own backtest found no 10-day edge in the screen that produced this name, and a conviction score from one week of headlines has no track record. Alpha is cut to 25%: +0.15%, expected return +0.35%.

**Post-critique:** P(up after 10 sessions) ≈ 53%; 10th-90th percentile -5.9% to +6.6%. Key risk in window: Mean reversion after 20% one-month run.
