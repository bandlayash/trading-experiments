"""Price-only short-horizon features, computed from data up to and including bar t.

Shared by the backtest and the live screen so both score names on identical definitions.
Every feature at row t uses closes at or before t; the forward return starts at the open of
t+1 (next session), which is when an order placed after Friday's close actually fills.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def features(close: pd.DataFrame) -> dict[str, pd.DataFrame]:
    logret = np.log(close).diff()
    sma50 = close.rolling(50, min_periods=45).mean()
    sma200 = close.rolling(200, min_periods=180).mean()
    hi252 = close.rolling(252, min_periods=230).max()
    return {
        # Intermediate momentum, skipping the most recent month (Jegadeesh-Titman 12-1).
        "mom_12_1": close.shift(21) / close.shift(252) - 1,
        "mom_6_1": close.shift(21) / close.shift(126) - 1,
        # Proximity to the 52-week high (George & Hwang 2004).
        "hi52": close / hi252,
        # Trend stack: distance above the 50-day, plus 50-day above 200-day.
        "trend": (close / sma50 - 1) + (sma50 / sma200 - 1),
        # Short-term reversal: last week's losers tend to bounce (sign flipped so high = good).
        "rev_5d": -(close / close.shift(5) - 1),
        # Realised volatility, 60 days annualised (enters negatively: low vol = good).
        "vol_60": logret.rolling(60, min_periods=50).std() * np.sqrt(252),
    }


# Pre-specified before looking at any backtest output. Signs: + rewards high values.
WEIGHTS = {"mom_12_1": 0.30, "hi52": 0.25, "trend": 0.15, "rev_5d": 0.15, "vol_60": -0.15}


def zscore_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score per date, winsorised at 2/98 percentiles."""
    lo = df.quantile(0.02, axis=1)
    hi = df.quantile(0.98, axis=1)
    w = df.clip(lo, hi, axis=0)
    return w.sub(w.mean(axis=1), axis=0).div(w.std(axis=1), axis=0)


def composite(feats: dict[str, pd.DataFrame], weights: dict[str, float] = WEIGHTS) -> pd.DataFrame:
    total = None
    for k, w in weights.items():
        z = zscore_rows(feats[k]).fillna(0.0) * w     # missing = neutral, as in Stage 1
        total = z if total is None else total + z
    # Require the core momentum inputs: no score for names with < ~1y of history.
    return total.where(feats["mom_12_1"].notna() & feats["vol_60"].notna())
