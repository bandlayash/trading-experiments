# XYZ — 10-session scenario model

Entry: open 2026-11-09. Exit: close 2026-11-20. Stage-2 conviction 58/100 (Strong beat, 2027 outlook should lift estimates; held gap through market rout).

| Input | Value |
|---|---|
| Volatility (max of 60d, 1y), annual | 47.9% |
| 1-sigma move over 10 sessions | 9.6% |
| Beta to SPY (1y daily) | 1.78 |
| CAPM drift, 10 sessions (rf 4.00%, ERP 5%) | +0.51% |

| Scenario | Probability | 10-session return |
|---|---|---|
| Bear | 0.25 | -11.1% |
| Base | 0.50 | +1.0% |
| Bull | 0.25 | +13.1% |
| **Probability-weighted** | 1.00 | **+0.99%** |

## Red-team

Pre-critique, reading conviction literally as P(beat SPY), the alpha is +1.93% and the expected return +2.44%. The strongest argument that this is wrong: this branch's own backtest found no 10-day edge in the screen that produced this name, and a conviction score from one week of headlines has no track record. Alpha is cut to 25%: +0.48%, expected return +0.99%.

**Post-critique:** P(up after 10 sessions) ≈ 54%; 10th-90th percentile -11.2% to +13.2%. Key risk in window: Bitcoin slide, Democratic Congress fintech regulation, DOJ final terms.
