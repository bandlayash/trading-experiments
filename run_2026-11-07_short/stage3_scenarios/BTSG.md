# BTSG — 10-session scenario model

Entry: open 2026-11-09. Exit: close 2026-11-20. Stage-2 conviction 56/100 (Beat-and-raise, revenue guide 4% above consensus; gap held in weak tape).

| Input | Value |
|---|---|
| Volatility (max of 60d, 1y), annual | 45.6% |
| 1-sigma move over 10 sessions | 9.1% |
| Beta to SPY (1y daily) | 1.10 |
| CAPM drift, 10 sessions (rf 4.00%, ERP 5%) | +0.38% |

| Scenario | Probability | 10-session return |
|---|---|---|
| Bear | 0.25 | -10.8% |
| Base | 0.50 | +0.7% |
| Bull | 0.25 | +12.3% |
| **Probability-weighted** | 1.00 | **+0.72%** |

## Red-team

Pre-critique, reading conviction literally as P(beat SPY), the alpha is +1.37% and the expected return +1.75%. The strongest argument that this is wrong: this branch's own backtest found no 10-day edge in the screen that produced this name, and a conviction score from one week of headlines has no track record. Alpha is cut to 25%: +0.34%, expected return +0.72%.

**Post-critique:** P(up after 10 sessions) ≈ 53%; 10th-90th percentile -10.9% to +12.4%. Key risk in window: High-vol momentum name in a de-risking market; policy headlines.
