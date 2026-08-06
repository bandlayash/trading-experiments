"""Strategy 4 -- EMA(9) / RSI(14) mean reversion.

    Entry   RSI(14) < rsi_entry (oversold) AND close < EMA(9)   -> buy the dip
    Exit    close > EMA(9)                                       -> reversion complete
            (optionally) held for max_hold bars                  -> time stop

This is the first NON-trend strategy in the repo, and that is the point of including it.
The other three all assume price movement persists. This one assumes the opposite over a
short horizon: that a sharp move away from a fast moving average tends to snap back.

The two conditions are deliberately redundant-looking but do different jobs. RSI(14) below
30 says the recent move down was unusually one-sided in magnitude; `close < EMA(9)` says
price is currently below its short-term anchor. Requiring both avoids buying a market that
is oversold on momentum but has already begun recovering.

Mean reversion and 3x leverage interact badly, and the results say so plainly -- see
STRATEGY.md on the `strategy/ema-rsi-meanrev` branch. Adding a losing strategy to the
comparison is intentional: a benchmark where everything wins is not measuring anything.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.engine import COST_PER_SIDE, StrategyResult

NAME = "EMA9/RSI14 MeanRev"
DEFAULTS = dict(ema_len=9, rsi_len=14, rsi_entry=30.0, max_hold=0)


def rsi(close: pd.Series, length: int) -> pd.Series:
    """Wilder's RSI.

    Wilder smooths average gain and loss with an EMA of alpha = 1/length (equivalently
    span = 2*length - 1), NOT a simple mean -- `ewm(alpha=1/length, adjust=False)` is the
    faithful implementation. Using a simple rolling mean here is a common and subtle error
    that shifts every threshold crossing.

        RS  = avg_gain / avg_loss
        RSI = 100 - 100 / (1 + RS)

    Edge cases, handled explicitly rather than left to produce inf/NaN:
      * avg_loss == 0 (unbroken run of up days)  -> RS infinite, RSI defined as 100
      * avg_gain == 0 (unbroken run of down days) -> RS = 0, so RSI = 0 falls out naturally
      * both zero (a perfectly flat series)       -> RSI undefined, conventionally 50
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False).mean()

    out = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    out = out.where(avg_loss > 0, 100.0)                       # no losses -> 100
    out = out.where((avg_gain > 0) | (avg_loss > 0), 50.0)     # perfectly flat -> 50
    return out


def signals(signal: pd.Series, ema_len: int, rsi_len: int,
            rsi_entry: float) -> tuple[pd.Series, pd.Series]:
    """Return (entry, exit_) boolean series, both evaluated on today's close."""
    ema = signal.ewm(span=ema_len, adjust=False).mean()
    r = rsi(signal, rsi_len)
    entry = (r < rsi_entry) & (signal < ema)
    exit_ = signal > ema
    return entry, exit_


def run(signal: pd.Series, traded: pd.Series, warmup: int = 252,
        **params) -> StrategyResult:
    """Simulate the mean-reversion system.

    `max_hold` > 0 adds a time stop: exit unconditionally after that many bars held. It
    defaults to OFF so the headline result reflects the rules as stated, including their
    worst property -- that a position entered into a sustained decline is held until price
    recovers above a 9-day EMA, which can take a very long time.
    """
    p = {**DEFAULTS, **params}
    entry, exit_ = signals(signal, p["ema_len"], p["rsi_len"], p["rsi_entry"])
    max_hold = int(p["max_hold"])

    ret_traded = traded.pct_change()
    idx = signal.index[warmup:]

    strat = pd.Series(0.0, index=idx)
    invested, holding, round_trips, bars_held = [], False, 0, 0

    for day in idx:
        r = ret_traded.loc[day]
        strat.loc[day] = float(r) if (holding and not pd.isna(r)) else 0.0
        invested.append(1.0 if holding else 0.0)

        if holding:
            bars_held += 1
            timed_out = max_hold > 0 and bars_held >= max_hold
            target = not (bool(exit_.loc[day]) or timed_out)
        else:
            target = bool(entry.loc[day])

        if target != holding:
            strat.loc[day] -= COST_PER_SIDE
            round_trips += int(not target)
            holding = target
            bars_held = 0 if target else bars_held

    return StrategyResult(NAME, strat, float(np.mean(invested)), round_trips, p)
