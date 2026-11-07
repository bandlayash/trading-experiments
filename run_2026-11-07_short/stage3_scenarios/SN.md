# SN — 10-session scenario model

Entry: open 2026-11-09. Exit: close 2026-11-20. Stage-2 conviction 56/100 (Big revenue beat, raised guide, bright holiday outlook; drifting higher).

| Input | Value |
|---|---|
| Volatility (max of 60d, 1y), annual | 42.3% |
| 1-sigma move over 10 sessions | 8.4% |
| Beta to SPY (1y daily) | 1.31 |
| CAPM drift, 10 sessions (rf 4.00%, ERP 5%) | +0.42% |

| Scenario | Probability | 10-session return |
|---|---|---|
| Bear | 0.25 | -10.0% |
| Base | 0.50 | +0.7% |
| Bull | 0.25 | +11.4% |
| **Probability-weighted** | 1.00 | **+0.74%** |

## Red-team

Pre-critique, reading conviction literally as P(beat SPY), the alpha is +1.27% and the expected return +1.69%. The strongest argument that this is wrong: this branch's own backtest found no 10-day edge in the screen that produced this name, and a conviction score from one week of headlines has no track record. Alpha is cut to 25%: +0.32%, expected return +0.74%.

**Post-critique:** P(up after 10 sessions) ≈ 53%; 10th-90th percentile -10.1% to +11.5%. Key risk in window: Valuation after +85% YTD; retailer inventory caution read-across.
