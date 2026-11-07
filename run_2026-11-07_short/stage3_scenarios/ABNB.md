# ABNB — 10-session scenario model

Entry: open 2026-11-09. Exit: close 2026-11-20. Stage-2 conviction 58/100 (Fastest growth in 3 yrs, raised guide, $12B buyback; partly priced).

| Input | Value |
|---|---|
| Volatility (max of 60d, 1y), annual | 42.1% |
| 1-sigma move over 10 sessions | 8.4% |
| Beta to SPY (1y daily) | 1.07 |
| CAPM drift, 10 sessions (rf 4.00%, ERP 5%) | +0.37% |

| Scenario | Probability | 10-session return |
|---|---|---|
| Bear | 0.25 | -9.9% |
| Base | 0.50 | +0.8% |
| Bull | 0.25 | +11.5% |
| **Probability-weighted** | 1.00 | **+0.79%** |

## Red-team

Pre-critique, reading conviction literally as P(beat SPY), the alpha is +1.69% and the expected return +2.06%. The strongest argument that this is wrong: this branch's own backtest found no 10-day edge in the screen that produced this name, and a conviction score from one week of headlines has no track record. Alpha is cut to 25%: +0.42%, expected return +0.79%.

**Post-critique:** P(up after 10 sessions) ≈ 54%; 10th-90th percentile -9.9% to +11.5%. Key risk in window: FX and payment-timing caveats; AI-disruption fears could return.
