"""Strategy 3 -- Ed Seykota style: dual-EMA trend, ATR risk sizing, ATR trailing stop.

    trend      50-day EMA > 200-day EMA on the signal instrument
    sizing     risk `risk_per_trade` (2%) of equity at a stop `atr_mult` * ATR away,
               i.e. position fraction f = risk_per_trade / (atr_mult * ATR%)
    exit       ATR trailing stop from the high-water mark, or the trend turning down

The distinguishing feature is that Seykota does not go all-in. Position size falls out
of the risk budget: the more volatile the instrument, the smaller the position. On a 3x
leveraged ETF, ATR% is large, so `f` is small and most of the account sits in cash --
BY DESIGN. That is the whole reason this variant is included in the comparison.

ATR is approximated by a close-to-close volatility proxy. The harness uses split- and
dividend-adjusted closes, on which a true OHLC range is itself only an approximation,
and daily-return standard deviation is a faithful stand-in for the risk-sizing purpose.

Full write-up: the `strategy/seykota` branch (it is that branch's landing page).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.engine import COST_PER_SIDE, StrategyResult

NAME = "Seykota"
DEFAULTS = dict(ema_fast=50, ema_slow=200, risk_per_trade=0.02, atr_len=14,
                atr_mult=4.0, max_deploy=1.0)


def run(signal: pd.Series, traded: pd.Series, warmup: int = 252,
        **params) -> StrategyResult:
    """Simulate the risk-sized trend system.

    Unlike the other two strategies this one is not binary, so it tracks an explicit
    cash/position ledger rather than a boolean `holding` flag.
    """
    p = {**DEFAULTS, **params}

    ema_fast = signal.ewm(span=p["ema_fast"], adjust=False).mean()
    ema_slow = signal.ewm(span=p["ema_slow"], adjust=False).mean()
    trend_up = ema_fast > ema_slow

    ret_traded = traded.pct_change()
    atr_frac = ret_traded.rolling(p["atr_len"]).std()             # ATR proxy, as a % of price
    stop_frac = (p["atr_mult"] * atr_frac).clip(lower=1e-6)       # stop distance, as a % of price

    idx = signal.index[warmup:]
    strat = pd.Series(0.0, index=idx)
    deployed = []

    position_val = 0.0     # dollars exposed, drifting with price inside a trade
    cash = 1.0
    peak = None            # high-water close since entry, for the trailing stop
    prev_equity = 1.0
    round_trips = 0

    for day in idx:
        # 1) mark the open position to market on today's move
        r = ret_traded.loc[day]
        if position_val > 0 and not pd.isna(r):
            position_val *= 1.0 + float(r)

        # 2) act at today's close; costs accrue into today's return
        price = float(traded.loc[day])
        cost = 0.0
        if position_val > 0:
            peak = price if peak is None else max(peak, price)
            trail_hit = (price / peak - 1.0) <= -float(stop_frac.loc[day])
            trend_exit = not bool(trend_up.loc[day])
            if trail_hit or trend_exit:
                cost += COST_PER_SIDE * position_val
                cash += position_val
                position_val, peak = 0.0, None
                round_trips += 1
        elif bool(trend_up.loc[day]):
            equity_now = position_val + cash
            f = min(p["risk_per_trade"] / float(stop_frac.loc[day]), p["max_deploy"])
            notional = f * equity_now
            cost += COST_PER_SIDE * notional
            position_val, cash, peak = notional, cash - notional, price
        cash -= cost

        # 3) book today's equity return
        equity = position_val + cash
        strat.loc[day] = equity / prev_equity - 1.0 if prev_equity > 0 else 0.0
        prev_equity = equity
        deployed.append(position_val / equity if equity > 0 else 0.0)

    return StrategyResult(NAME, strat, float(np.mean(deployed)), round_trips, p)
