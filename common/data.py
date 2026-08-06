"""Price data loading, shared by every strategy so they are scored on identical bars.

Uses yfinance adjusted closes (splits + dividends). SOXL has had multiple splits, so
using raw closes would fabricate enormous fake losses -- `auto_adjust=True` is not
optional here.

A tiny on-disk cache keeps repeated backtest runs fast and makes results reproducible
offline: delete `data/cache/` to force a refresh.
"""

from __future__ import annotations

import os

import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "cache")

START = "2011-01-01"   # SOXL listed 2010-03; start once it has ~1y of history
END = None             # None = today


def fetch_close(symbol: str, start: str = START, end: str | None = END,
                use_cache: bool = True) -> pd.Series:
    """Split/dividend-adjusted daily closes for `symbol`, oldest -> newest."""
    cache_path = os.path.join(CACHE_DIR, f"{symbol}_{start}_{end or 'latest'}.csv")
    if use_cache and os.path.exists(cache_path):
        s = pd.read_csv(cache_path, index_col=0, parse_dates=True).iloc[:, 0]
        return s.astype(float).rename(symbol)

    try:
        import yfinance as yf
    except ImportError:  # pragma: no cover
        raise SystemExit("Install deps first:  pip install -r requirements.txt")

    df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        raise SystemExit(f"No data returned for {symbol} -- check the symbol or your network.")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):      # yfinance sometimes returns a 1-column frame
        close = close.iloc[:, 0]
    close = close.astype(float).rename(symbol)

    if use_cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        close.to_csv(cache_path)
    return close


def load_pair(signal_symbol: str = "SMH", trade_symbol: str = "SOXL",
              **kwargs) -> tuple[pd.Series, pd.Series]:
    """Load a (signal, traded) pair aligned to their common trading days.

    Aligning matters: the strategies read a trend off one instrument and express it in
    another, so a day present in only one series would silently shift the two apart.
    """
    a = fetch_close(signal_symbol, **kwargs)
    b = fetch_close(trade_symbol, **kwargs)
    data = pd.concat([a, b], axis=1).dropna()
    return data[signal_symbol], data[trade_symbol]
