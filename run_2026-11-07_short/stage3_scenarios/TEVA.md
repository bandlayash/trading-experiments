# TEVA — 10-session scenario model

Entry: open 2026-11-09. Exit: close 2026-11-20. Stage-2 conviction 56/100 (Branded beat-and-raise, real +3% reaction (Stage-1 misdated), resilient at 52w high).

| Input | Value |
|---|---|
| Volatility (max of 60d, 1y), annual | 33.5% |
| 1-sigma move over 10 sessions | 6.7% |
| Beta to SPY (1y daily) | 0.60 |
| CAPM drift, 10 sessions (rf 4.00%, ERP 5%) | +0.28% |

| Scenario | Probability | 10-session return |
|---|---|---|
| Bear | 0.25 | -7.9% |
| Base | 0.50 | +0.5% |
| Bull | 0.25 | +9.0% |
| **Probability-weighted** | 1.00 | **+0.53%** |

## Red-team

Pre-critique, reading conviction literally as P(beat SPY), the alpha is +1.01% and the expected return +1.28%. The strongest argument that this is wrong: this branch's own backtest found no 10-day edge in the screen that produced this name, and a conviction score from one week of headlines has no track record. Alpha is cut to 25%: +0.25%, expected return +0.53%.

**Post-critique:** P(up after 10 sessions) ≈ 53%; 10th-90th percentile -8.0% to +9.1%. Key risk in window: Healthcare sector sell-off; generic erosion headlines.
