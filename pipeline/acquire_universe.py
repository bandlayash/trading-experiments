"""Universe: roughly the largest ~1,000 US-listed equities, by market cap.

The iShares constituent CSV is bot-blocked (see README §4), so the Yahoo equity screener,
sorted by market cap, is used as a proxy. The screener quote already carries most of what a
short-horizon screen needs (52-week range, 50/200-day averages, analyst rating, forward PE,
next earnings timestamp), which avoids ~1,000 throttled `.info` calls.

Output: data/cache/universe_quotes.json (raw, git-ignored) and data/cache/universe.csv.
"""
from __future__ import annotations

import json
import os
import sys
import time

import pandas as pd
import yfinance as yf
from yfinance import EquityQuery as Q

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
PAGE = 250
LISTED = ["NMS", "NYQ", "NGM", "NCM", "ASE", "BTS", "PCX"]

FIELDS = ["symbol", "shortName", "quoteType", "exchange", "marketCap", "regularMarketPrice",
          "averageDailyVolume3Month", "averageAnalystRating", "forwardPE", "trailingPE",
          "epsForward", "epsTrailingTwelveMonths", "epsCurrentYear", "priceToBook",
          "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "fiftyDayAverage", "twoHundredDayAverage",
          "earningsTimestamp", "earningsTimestampStart", "earningsTimestampEnd",
          "isEarningsDateEstimate", "firstTradeDateMilliseconds", "financialCurrency"]


def fetch_page(query, offset: int) -> list[dict]:
    for attempt in range(5):
        try:
            r = yf.screen(query, sortField="intradaymarketcap", sortAsc=False,
                          size=PAGE, offset=offset)
            return r["quotes"]
        except Exception as e:  # throttling / crumb hiccups are routine here
            wait = 5 * 2 ** attempt
            print(f"offset {offset}: {e} -- retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"screener page at offset {offset} failed")


def main() -> None:
    os.makedirs(CACHE, exist_ok=True)
    # Listed on a national exchange only. Without this the screener returns hundreds of
    # foreign OTC pink-sheet lines (e.g. SSNLF), whose prices are stale or corrupt and which
    # many brokers restrict -- not something you can reliably buy at Monday's open.
    query = Q("and", [Q("eq", ["region", "us"]), Q("gt", ["intradaymarketcap", 1e9]),
                      Q("is-in", ["exchange"] + LISTED)])
    quotes: list[dict] = []
    for off in range(0, N + PAGE, PAGE):   # one spare page to cover de-duplication losses
        quotes += fetch_page(query, off)
        time.sleep(2)
    with open(os.path.join(CACHE, "universe_quotes.json"), "w") as f:
        json.dump(quotes, f)
    df = pd.DataFrame([{k: q.get(k) for k in FIELDS} for q in quotes])
    df = df[(df.quoteType == "EQUITY") & df.exchange.isin(LISTED)].drop_duplicates("symbol")
    # Share classes of one company (GOOG/GOOGL, BRK-A/BRK-B) would double-count; keep the
    # more liquid line.
    df["_name"] = df.shortName.str.replace(r"\s+(Class|Cl)\s*[A-C]\b.*", "", regex=True)
    df = (df.sort_values("averageDailyVolume3Month", ascending=False)
            .drop_duplicates("_name").drop(columns="_name")
            .sort_values("marketCap", ascending=False).head(N))
    df.to_csv(os.path.join(CACHE, "universe.csv"), index=False)
    print(f"{len(df)} names; smallest market cap {df.marketCap.min()/1e9:.1f}B")


if __name__ == "__main__":
    main()
