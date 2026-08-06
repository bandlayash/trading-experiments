"""Shared simulation scaffolding: the result type, the cost model, and the no-look-ahead rule.

The one convention every strategy in this repo obeys
---------------------------------------------------
Signals are computed from data available **up to and including today's close**, and the
resulting position earns **tomorrow's** return. Concretely, each strategy loop does:

    for day in index:
        book today's return on the position we were ALREADY holding
        then decide the position to carry into tomorrow

Getting this backwards is the single most common way a backtest invents an edge that
does not exist, so it is implemented once, here, rather than per strategy.

Costs
-----
`COST_PER_SIDE` (5 bps) is charged on every change of position and models spread plus
slippage. These are liquid ETFs; commissions are zero at the broker in question. The
strategies here trade between ~1 and ~8 round trips a year, so total cost drag ranges
from ~0.1%/yr to ~0.8%/yr -- small relative to the differences being measured, but not
nothing, and deliberately not omitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

COST_PER_SIDE = 0.0005   # 5 bps per side


@dataclass
class StrategyResult:
    """What every strategy returns, so the benchmark can treat them interchangeably."""

    name: str
    daily_ret: pd.Series          # daily strategy returns, net of costs
    exposure: float               # average fraction of equity at risk
    round_trips: int              # completed buy->sell cycles
    params: dict = field(default_factory=dict)

    @property
    def trades_per_year(self) -> float:
        from .metrics import TRADING_DAYS
        years = len(self.daily_ret) / TRADING_DAYS
        return self.round_trips / years if years > 0 else float("nan")

    def equity_curve(self) -> pd.Series:
        return (1.0 + self.daily_ret).cumprod()


def buy_and_hold(prices: pd.Series, index: pd.DatetimeIndex, name: str) -> StrategyResult:
    """Benchmark: hold the instrument for the whole window, no costs after entry."""
    ret = prices.pct_change().reindex(index).fillna(0.0)
    return StrategyResult(name=name, daily_ret=ret, exposure=1.0, round_trips=0)
