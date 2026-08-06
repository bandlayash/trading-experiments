"""Strategy 2 -- 200-day SMA regime filter with 12-month absolute momentum.

    uptrend = close > SMA(200) AND 12-month return > 0
    position: uptrend -> hold the traded instrument; otherwise -> cash

This is the classic dual-filter trend model (Faber-style moving-average timing combined
with absolute/time-series momentum). It was the live strategy for this account until
August 2026 and is kept here as the incumbent to beat.

Unlike the breakout model this signal is STATELESS: `uptrend` fully determines the
position on any given day, so it flips in and out whenever price oscillates around the
moving average. That is the source of its ~4 round trips a year, against ~0.9 for the
breakout model.

Full write-up: the `strategy/sma-momentum` branch (it is that branch's landing page).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.engine import COST_PER_SIDE, StrategyResult

NAME = "SMA+Momentum"
DEFAULTS = dict(sma_len=200, mom_len=252)


def signals(signal: pd.Series, sma_len: int, mom_len: int) -> pd.Series:
    """Boolean `uptrend` series -- the whole strategy, since position == signal."""
    sma = signal.rolling(sma_len).mean()
    momentum = signal.pct_change(mom_len)
    return (signal > sma) & (momentum > 0)


def run(signal: pd.Series, traded: pd.Series, warmup: int = 252,
        **params) -> StrategyResult:
    p = {**DEFAULTS, **params}
    uptrend = signals(signal, **p)

    ret_traded = traded.pct_change()
    idx = signal.index[warmup:]

    strat = pd.Series(0.0, index=idx)
    invested, holding, round_trips = [], False, 0

    for day in idx:
        r = ret_traded.loc[day]
        strat.loc[day] = float(r) if (holding and not pd.isna(r)) else 0.0
        invested.append(1.0 if holding else 0.0)

        target = bool(uptrend.loc[day])
        if target != holding:
            strat.loc[day] -= COST_PER_SIDE
            round_trips += int(not target)
            holding = target

    return StrategyResult(NAME, strat, float(np.mean(invested)), round_trips, p)
