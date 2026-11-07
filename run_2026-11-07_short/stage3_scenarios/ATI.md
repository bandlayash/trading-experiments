# ATI — 10-session scenario model

Entry: open 2026-11-09. Exit: close 2026-11-20. Stage-2 conviction 56/100 (Aerospace beat-and-raise with rising estimates and post-print drift; no visible offset).

| Input | Value |
|---|---|
| Volatility (max of 60d, 1y), annual | 47.8% |
| 1-sigma move over 10 sessions | 9.5% |
| Beta to SPY (1y daily) | 1.57 |
| CAPM drift, 10 sessions (rf 4.00%, ERP 5%) | +0.47% |

| Scenario | Probability | 10-session return |
|---|---|---|
| Bear | 0.25 | -11.3% |
| Base | 0.50 | +0.8% |
| Bull | 0.25 | +12.9% |
| **Probability-weighted** | 1.00 | **+0.83%** |

## Red-team

Pre-critique, reading conviction literally as P(beat SPY), the alpha is +1.44% and the expected return +1.91%. The strongest argument that this is wrong: this branch's own backtest found no 10-day edge in the screen that produced this name, and a conviction score from one week of headlines has no track record. Alpha is cut to 25%: +0.36%, expected return +0.83%.

**Post-critique:** P(up after 10 sessions) ≈ 53%; 10th-90th percentile -11.4% to +13.0%. Key risk in window: Market rout beta; unknown-direction analyst call Nov 5.
