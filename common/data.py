"""Price data loading, shared by every strategy so they are scored on identical bars.

Uses yfinance adjusted closes (splits + dividends). SOXL has had multiple splits, so
using raw closes would fabricate enormous fake losses -- `auto_adjust=True` is not
optional here.

A tiny on-disk cache keeps repeated backtest runs fast and makes results reproducible
offline: delete `data/cache/` to force a refresh.

The cache key is date-stamped for open-ended requests. An `end=None` request means "every
bar up to today", and what that resolves to changes every trading day -- so caching it
under a fixed `latest` key silently re-serves yesterday's bars tomorrow, and a repo whose
whole claim is "re-run it and check" quietly stops re-running anything. A request with an
explicit `end` is immutable and keeps a permanent key.
"""

from __future__ import annotations

import datetime as dt
import glob
import os

import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "cache")

START = "2011-01-01"   # SOXL listed 2010-03; start once it has ~1y of history
END = None             # None = today


def _cache_path(symbol: str, start: str, end: str | None, kind: str) -> str:
    """Cache filename for one request. Open-ended requests get today's date in the key.

    `kind` separates the close-only and Open/Close caches so a caller asking for OHLC can
    never be served a file written by a caller that only wanted closes.
    """
    suffix = f"_{kind}" if kind else ""
    stamp = end if end else f"latest-{dt.date.today().isoformat()}"
    return os.path.join(CACHE_DIR, f"{symbol}{suffix}_{start}_{stamp}.csv")


def _prune_stale(symbol: str, start: str, kind: str, keep: str) -> None:
    """Delete superseded caches for this symbol so the directory does not grow without bound.

    Covers both today's `latest-<date>` files and the undated `latest` files written by the
    earlier cache scheme, which nothing reads any more and which would otherwise sit in
    every existing checkout forever.
    """
    suffix = f"_{kind}" if kind else ""
    stale = (glob.glob(os.path.join(CACHE_DIR, f"{symbol}{suffix}_{start}_latest-*.csv"))
             + glob.glob(os.path.join(CACHE_DIR, f"{symbol}{suffix}_{start}_latest.csv")))
    for path in stale:
        if os.path.abspath(path) != os.path.abspath(keep):
            try:
                os.remove(path)
            except OSError:      # a concurrent run already removed it; nothing to do
                pass


def fetch_close(symbol: str, start: str = START, end: str | None = END,
                use_cache: bool = True) -> pd.Series:
    """Split/dividend-adjusted daily closes for `symbol`, oldest -> newest."""
    cache_path = _cache_path(symbol, start, end, kind="")
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
        _prune_stale(symbol, start, "", keep=cache_path)
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


def fetch_ohlc(symbol: str, start: str = START, end: str | None = END,
               use_cache: bool = True) -> pd.DataFrame:
    """Split/dividend-adjusted daily Open and Close for `symbol`, oldest -> newest.

    Only Open and Close are kept -- that is all an overnight (close-to-open) strategy
    needs, and a narrow cache format avoids silently serving stale High/Low/Volume to a
    future caller that asked for something else.
    """
    cache_path = _cache_path(symbol, start, end, kind="ohlc")
    if use_cache and os.path.exists(cache_path):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        return df.astype(float)

    try:
        import yfinance as yf
    except ImportError:  # pragma: no cover
        raise SystemExit("Install deps first:  pip install -r requirements.txt")

    df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        raise SystemExit(f"No data returned for {symbol} -- check the symbol or your network.")
    out = df[["Open", "Close"]].copy()
    if isinstance(out.columns, pd.MultiIndex):     # yfinance sometimes nests columns by symbol
        out.columns = out.columns.get_level_values(0)
    out = out.astype(float)
    out.index.name = "Date"

    if use_cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        out.to_csv(cache_path)
        _prune_stale(symbol, start, "ohlc", keep=cache_path)
    return out


def load_ohlc_universe(symbols: list[str], **kwargs) -> dict[str, pd.DataFrame]:
    """Open/Close frames for a basket of tickers, each independently indexed.

    Unlike `load_pair`, this does NOT reduce everything to the common intersection of
    trading days. A basket strategy has to decide per-day, per-name, whether that name
    is tradeable (e.g. it simply hadn't IPO'd yet), and silently shrinking the whole
    backtest to the window where all N names already existed would throw away years of
    the earliest-listed names' history -- Apple and Microsoft's data going back to 2011
    would otherwise be truncated to match Meta's May 2012 IPO for no reason.
    """
    return {sym: fetch_ohlc(sym, **kwargs) for sym in symbols}
