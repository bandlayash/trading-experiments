"""Performance metrics. One implementation, used by every strategy and benchmark.

Conventions (stated explicitly, because these choices move the headline numbers):

  * Sharpe uses ARITHMETIC mean daily return, annualized by 252, divided by annualized
    daily-return standard deviation. `RF_ANNUAL` defaults to 0.0 -- i.e. these are
    excess-of-cash-at-0% figures. Set it to ~0.04 to compare against T-bills; every
    Sharpe below drops by roughly 0.04/vol.
  * CAGR is geometric, from the compounded equity curve.
  * Max drawdown is measured on daily closes. Real intraday drawdowns were worse.

Sharpe on a strongly-trending leveraged instrument is a poor summary statistic -- the
return distribution is fat-tailed and skewed, so a single number hides a lot. It is used
here because it was the stated selection criterion, not because it is sufficient.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252
RF_ANNUAL = 0.0

# Volatility below this is treated as zero, making Sharpe undefined rather than enormous.
# Not pedantry: `pd.Series([0.001] * 500).std()` returns ~7e-18, not 0.0, so a naive
# `if ann_vol > 0` guard divides by float noise and reports a Sharpe of ~3.7e16 for a
# flat-line return series. Any real daily strategy has annualised vol far above 1e-12.
VOL_EPSILON = 1e-12


def perf_stats(daily_ret: pd.Series, rf_annual: float = RF_ANNUAL) -> dict:
    """Sharpe, CAGR, annualized vol, max drawdown and total growth multiple."""
    daily_ret = daily_ret.dropna()
    n = len(daily_ret)
    if n == 0:
        return dict.fromkeys(
            ["sharpe", "cagr", "ann_vol", "max_dd", "equity_mult"], float("nan"))

    equity = (1.0 + daily_ret).cumprod()
    ann_vol = daily_ret.std() * np.sqrt(TRADING_DAYS)
    ann_ret = daily_ret.mean() * TRADING_DAYS
    drawdown = equity / equity.cummax() - 1.0
    return {
        "sharpe": (ann_ret - rf_annual) / ann_vol if ann_vol > VOL_EPSILON else float("nan"),
        "cagr": equity.iloc[-1] ** (TRADING_DAYS / n) - 1.0,
        "ann_vol": ann_vol,
        "max_dd": drawdown.min(),
        "equity_mult": equity.iloc[-1],
    }


def split_stats(daily_ret: pd.Series, oos_start: str) -> dict:
    """Stats for the full period plus the in-sample / out-of-sample halves.

    Reporting all three together is the point: a strategy whose full-period Sharpe looks
    fine but whose OOS half collapses was fitted, not discovered.
    """
    idx = daily_ret.index
    return {
        "all": perf_stats(daily_ret),
        "is": perf_stats(daily_ret.loc[idx < oos_start]),
        "oos": perf_stats(daily_ret.loc[idx >= oos_start]),
    }


def sub_period_sharpe(daily_ret: pd.Series, starts=("2012", "2016", "2020", "2024"),
                      span: int = 4) -> dict:
    """Sharpe within fixed multi-year blocks -- a consistency check across regimes.

    The final block is labelled by the data it actually contains, not by the nominal span.
    A block headed "2024-2027" that in fact holds 2.7 years of bars invites the reader to
    compare it with the full four-year blocks beside it as though they carried equal
    weight; a trailing `*` marks the ones that do not.
    """
    idx = daily_ret.index
    out = {}
    for start in starts:
        chunk = daily_ret.loc[(idx >= start) & (idx < str(int(start) + span))]
        nominal_end = int(start) + span - 1
        if len(chunk) and chunk.index[-1].year < nominal_end:
            label = f"{start}-{chunk.index[-1].year}*"      # * = block truncated by data end
        else:
            label = f"{start}-{nominal_end}"
        out[label] = perf_stats(chunk)["sharpe"] if len(chunk) > 20 else float("nan")
    return out
