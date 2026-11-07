"""Daily adjusted closes (and volume) for the universe plus SPY, chunked and resumable.

Each chunk is written to data/cache/prices/ as soon as it lands, so a throttled run can be
resumed without re-downloading what already succeeded.
"""
from __future__ import annotations

import glob
import os
import sys
import time

import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")
OUT = os.path.join(CACHE, "prices")
PERIOD = sys.argv[1] if len(sys.argv) > 1 else "3y"
CHUNK = 100


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    syms = pd.read_csv(os.path.join(CACHE, "universe.csv")).symbol.tolist()
    syms = ["SPY"] + [s for s in syms if s != "SPY"]
    for i in range(0, len(syms), CHUNK):
        path = os.path.join(OUT, f"chunk_{i // CHUNK:03d}.pkl")
        if os.path.exists(path):
            continue
        batch = syms[i:i + CHUNK]
        for attempt in range(4):
            try:
                d = yf.download(batch, period=PERIOD, auto_adjust=True, progress=False,
                                threads=True, group_by="column")
                break
            except Exception as e:
                print(f"chunk {i}: {e}; retrying")
                time.sleep(10 * 2 ** attempt)
        d[["Close", "Volume", "Open"]].to_pickle(path)
        print(f"chunk {i // CHUNK}: {d['Close'].notna().any().sum()}/{len(batch)} with data")
        time.sleep(2)
    parts = [pd.read_pickle(p) for p in sorted(glob.glob(os.path.join(OUT, "chunk_*.pkl")))]
    full = pd.concat(parts, axis=1)
    full = full.loc[:, ~full.columns.duplicated()]
    # A non-positive price is a vendor error, never a real print.
    full = full.mask(full[["Close", "Open"]].reindex(columns=full.columns, fill_value=1) <= 0)
    full["Close"].to_pickle(os.path.join(CACHE, "close.pkl"))
    full["Volume"].to_pickle(os.path.join(CACHE, "volume.pkl"))
    full["Open"].to_pickle(os.path.join(CACHE, "open.pkl"))
    c = full["Close"]
    print(f"close matrix {c.shape}, last bar {c.index[-1].date()}")


if __name__ == "__main__":
    main()
