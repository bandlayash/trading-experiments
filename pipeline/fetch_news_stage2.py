"""Stage 2 input: dated news from the last 7 days for each Stage-1 advancer.

Pulls Yahoo Finance's per-ticker news feed, keeps items published in the window, and writes
one JSON per ticker plus a compact digest for the bull/bear review. Items carry title,
publisher, publish time and summary, so every thesis point can cite a dated, sourced item.
"""
from __future__ import annotations

import json
import os
import sys
import time

import pandas as pd
import yfinance as yf

WINDOW_DAYS = 7


def main(run_dir: str) -> None:
    top = pd.read_csv(os.path.join(run_dir, "stage1_screen", "top_30.csv"))
    out = os.path.join(run_dir, "stage2_adversarial", "news")
    os.makedirs(out, exist_ok=True)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=WINDOW_DAYS)
    digest = []
    for sym in top.symbol:
        path = os.path.join(out, f"{sym}.json")
        if not os.path.exists(path):
            items = None
            for attempt in range(3):
                try:
                    items = yf.Ticker(sym).get_news(count=40)
                    break
                except Exception as e:
                    print(sym, e)
                    time.sleep(5 * 2 ** attempt)
            if items is None:      # never write an empty file for a failed fetch
                print(f"{sym}: news fetch failed; skipped")
                continue
            kept = []
            for it in items:
                c = it.get("content", it)
                ts = pd.to_datetime(c.get("pubDate") or c.get("displayTime"), utc=True,
                                    errors="coerce")
                if pd.isna(ts) or ts < cutoff:
                    continue
                kept.append(dict(date=ts.strftime("%Y-%m-%d"),
                                 publisher=(c.get("provider") or {}).get("displayName"),
                                 title=c.get("title"),
                                 summary=(c.get("summary") or "")[:400],
                                 url=((c.get("canonicalUrl") or {}).get("url"))))
            json.dump(kept, open(path, "w"), indent=1)
            time.sleep(1)
        kept = json.load(open(path))
        digest.append(f"### {sym} ({len(kept)} items)")
        for k in kept:
            digest.append(f"- {k['date']} | {k['publisher']} | {k['title']} :: {k['summary'][:220]}")
    open(os.path.join(run_dir, "stage2_adversarial", "news_digest.md"), "w").write(
        "\n".join(digest) + "\n")
    print("\n".join(digest))


if __name__ == "__main__":
    main(sys.argv[1])
