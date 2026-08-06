"""Strategy 1 -- Donchian channel breakout with an Aroon market filter.

Rules (from the r/algotrading "Strategy 1: Trend Following" post):

    Input          closing prices for the last x periods on timeframe t
    Market filter  trade only when Aroon says we are in a trend
    Buy trigger    buy when the asset reaches ABOVE the high for the period x
    Sell trigger   sell when the asset reaches BELOW the low for the period x

The signal is STATEFUL: the buy and sell triggers are independent, and between them
there is a third state -- do nothing. Once long, the position is held through chop
until the exit channel actually breaks. That patience is where the return comes from.

See STRATEGY.md on the `strategy/donchian-aroon` branch for the full write-up.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.engine import COST_PER_SIDE, StrategyResult

NAME = "Donchian+Aroon"

# NOTE: at these defaults `aroon_len == entry_len`, which makes the Aroon filter INERT --
# see the docstring of `aroon_up_down` for why. The headline configuration is therefore a
# pure Donchian 50/63 breakout. That is a measured result, not an oversight: configurations
# where the filter actually binds (aroon_len = 100 or more) scored WORSE in the sweep
# (Sharpe 0.81 vs 0.90). The post's market filter is implemented faithfully here; it simply
# does not earn its keep on this data.
DEFAULTS = dict(entry_len=50, exit_len=63, aroon_len=50, aroon_thresh=50.0)


def aroon_up_down(close: pd.Series, length: int) -> tuple[pd.Series, pd.Series]:
    """Aroon Up/Down computed on closing prices.

        AroonUp   = 100 * (length - bars since the highest close) / length
        AroonDown = 100 * (length - bars since the lowest  close) / length

    Both use a window of `length + 1` closes ending at the current bar. 100 means the
    extreme is today; 0 means it is `length` bars ago.

    IMPORTANT -- this filter is a no-op when `length <= entry_len`. A close that sets a
    new `entry_len`-day high is necessarily the maximum of any window that short, so
    AroonUp is pinned at 100 on every entry bar and can never veto anything. Aroon only
    does real work as a LONGER-horizon regime read. Verified empirically: aroon lengths
    of 14, 25 and 50 give byte-identical results for entry_len >= 50.
    """
    window = length + 1
    bars_since_high = close.rolling(window).apply(
        lambda w: len(w) - 1 - int(np.argmax(w)), raw=True)
    bars_since_low = close.rolling(window).apply(
        lambda w: len(w) - 1 - int(np.argmin(w)), raw=True)
    return (100.0 * (length - bars_since_high) / length,
            100.0 * (length - bars_since_low) / length)


def signals(signal: pd.Series, entry_len: int, exit_len: int, aroon_len: int,
            aroon_thresh: float) -> tuple[pd.Series, pd.Series]:
    """Return (breakout, breakdown) boolean series.

    `.shift(1)` on the channel bounds is the no-look-ahead guard: the high/low must come
    from the PRIOR x closes. Without it today's close would be part of its own channel
    and could never exceed it.
    """
    upper = signal.rolling(entry_len).max().shift(1)
    lower = signal.rolling(exit_len).min().shift(1)
    aroon_up, aroon_down = aroon_up_down(signal, aroon_len)
    trending = (aroon_up > aroon_down) & (aroon_up >= aroon_thresh)
    return (signal > upper) & trending, signal < lower


def run(signal: pd.Series, traded: pd.Series, warmup: int = 252,
        **params) -> StrategyResult:
    """Simulate the breakout system. `signal` supplies the trend read, `traded` is held."""
    p = {**DEFAULTS, **params}
    breakout, breakdown = signals(signal, **p)

    ret_traded = traded.pct_change()
    idx = signal.index[warmup:]

    strat = pd.Series(0.0, index=idx)
    invested, holding, round_trips = [], False, 0

    for day in idx:
        # 1) today's return accrues on the position we came into today with
        r = ret_traded.loc[day]
        strat.loc[day] = float(r) if (holding and not pd.isna(r)) else 0.0
        invested.append(1.0 if holding else 0.0)

        # 2) decide what to carry into tomorrow, from signals as of today's close
        target = (not bool(breakdown.loc[day])) if holding else bool(breakout.loc[day])
        if target != holding:
            strat.loc[day] -= COST_PER_SIDE
            round_trips += int(not target)      # count on the exit leg
            holding = target

    return StrategyResult(NAME, strat, float(np.mean(invested)), round_trips, p)
