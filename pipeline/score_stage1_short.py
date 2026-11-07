"""Stage 1, short-horizon variant: what to buy at Monday's open and hold 1-2 weeks.

Differences from the 12-month design in the README, and why:

* **Pillars.** Fundamentals (quality, valuation, balance sheet) are dropped: they move prices
  over quarters, not days. The score is price trend + 12-1 momentum + the most recent
  earnings reaction (post-earnings drift). Trend and momentum were chosen *after* the 10-day
  backtest showed the pre-specified composite had no edge and these two were the only
  components positive in both halves -- that is a data-snooping decision and is labelled as
  one in the report.
* **Event filter.** Any name with an earnings report inside the holding window is excluded.
  An earnings gap is a coin flip that dwarfs any 10-day drift.
* **Tradeability.** National-exchange listing, >= 1y of history, 3-month average volume
  >= 1M shares, share price $5-$400 so a small account can buy whole shares, and 60-day
  volatility capped so a 2-week 1-sigma move stays near 10%.

Output: run_dir/stage1_screen/{full_universe_scored.csv, top_30.csv, methodology.json}
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import features, zscore_rows  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")

ASOF = pd.Timestamp("2026-11-06")          # last completed session
ENTRY = pd.Timestamp("2026-11-09")         # Monday open
WINDOW_END = pd.Timestamp("2026-11-24")    # 10 sessions after entry, plus a day of buffer
WEIGHTS = {"trend": 0.35, "mom_12_1": 0.35, "earn_react": 0.30}
FILTERS = dict(min_price=5.0, max_price=400.0, min_adv=1_000_000, max_vol60=0.50,
               min_history_days=252)
TOPN = 30


def earnings_reaction(close: pd.DataFrame, opn: pd.DataFrame, last_ts: pd.Series) -> pd.DataFrame:
    """Price reaction to the most recent report and drift since, for reports in the last ~30 days.

    A report after 20:00 UTC is after the US close, so the reaction session is the next one;
    an earlier timestamp is pre-market and reacts the same day.
    """
    out = {}
    idx = close.index
    for sym, ts in last_ts.items():
        if pd.isna(ts) or sym not in close or ts > ASOF + pd.Timedelta(hours=23):
            continue
        day = ts.normalize()
        pos = idx.searchsorted(day, side="left")
        if ts.hour >= 20 or (pos < len(idx) and idx[pos] > day):
            pos = pos + (1 if pos < len(idx) and idx[pos] == day else 0)
        if pos <= 0 or pos >= len(idx) or len(idx) - pos > 30:
            continue
        prev, react = close[sym].iloc[pos - 1], close[sym].iloc[pos]
        out[sym] = dict(last_earnings=ts, reaction_date=idx[pos].date(),
                        earn_react=react / prev - 1, drift_since=close[sym].iloc[-1] / react - 1,
                        sessions_since=len(idx) - 1 - pos)
    return pd.DataFrame(out).T


def main(run_dir: str) -> None:
    out = os.path.join(run_dir, "stage1_screen")
    os.makedirs(out, exist_ok=True)
    u = pd.read_csv(os.path.join(CACHE, "universe.csv")).set_index("symbol")
    for c in ["earningsTimestamp", "earningsTimestampStart", "earningsTimestampEnd"]:
        u[c] = pd.to_datetime(u[c], unit="s")
    close = pd.read_pickle(os.path.join(CACHE, "close.pkl")).loc[:ASOF]
    opn = pd.read_pickle(os.path.join(CACHE, "open.pkl")).loc[:ASOF]
    close = close.drop(columns="SPY")
    f = {k: v.iloc[-1] for k, v in features(close).items()}
    df = pd.DataFrame(f)
    df["price"] = close.iloc[-1]
    df["history_days"] = close.notna().sum()
    df["ret_5d"] = close.iloc[-1] / close.iloc[-6] - 1
    df["ret_21d"] = close.iloc[-1] / close.iloc[-22] - 1
    df = df.join(u[["shortName", "exchange", "marketCap", "averageDailyVolume3Month",
                    "averageAnalystRating", "forwardPE"]])

    # Earnings: the most recent past report, and the next one.
    now = ASOF + pd.Timedelta(hours=23)
    ts, start, end = u.earningsTimestamp, u.earningsTimestampStart, u.earningsTimestampEnd
    last_ts = ts.where(ts <= now)
    nxt = pd.concat([ts.where(ts > now), start.where(start > now)], axis=1).min(axis=1)
    nxt_end = pd.concat([nxt, end.where(end > now)], axis=1).max(axis=1)
    df["next_earnings"] = nxt
    df["next_earnings_end"] = nxt_end
    df = df.join(earnings_reaction(close, opn, last_ts))
    df["earn_react"] = pd.to_numeric(df["earn_react"], errors="coerce")

    # Eligibility
    flt = FILTERS
    reasons = pd.Series("", index=df.index)
    def flag(mask, why):
        reasons.loc[mask & (reasons == "")] = why
    flag(df.history_days < flt["min_history_days"], "under 1y of history")
    flag(df.price.isna() | (df.price < flt["min_price"]) | (df.price > flt["max_price"]),
         "price outside $5-$400")
    flag(df.averageDailyVolume3Month < flt["min_adv"], "avg volume < 1M")
    flag(df.vol_60 > flt["max_vol60"], "60d vol > 50%")
    # No next date published is fine if the company reported within the last ~10 weeks:
    # its next quarterly report cannot land inside a 2-week window starting now.
    recent = last_ts.reindex(df.index) >= ASOF - pd.Timedelta(days=70)
    flag(df.next_earnings.isna() & ~recent, "next earnings date unknown")
    flag((df.next_earnings.dt.normalize() <= WINDOW_END)
         | (df.next_earnings_end.dt.normalize() <= WINDOW_END),
         "earnings inside hold window")
    df["excluded_reason"] = reasons
    df["eligible"] = reasons == ""

    # Score: cross-sectional z within the eligible set; missing earnings reaction = neutral.
    elig = df[df.eligible]
    z = pd.DataFrame({k: zscore_rows(elig[[k]].T).T[k] for k in WEIGHTS})
    df["composite"] = (z.fillna(0) * pd.Series(WEIGHTS)).sum(axis=1)
    df["score_pct"] = df.composite.rank(pct=True) * 100
    df = df.sort_values("composite", ascending=False)
    df.index.name = "symbol"
    df.to_csv(os.path.join(out, "full_universe_scored.csv"))

    top = df[df.eligible].head(TOPN).copy()
    top["reason"] = top.apply(lambda r: (
        f"12-1m mom {r.mom_12_1:+.0%}, {r.hi52:.0%} of 52w high, trend {r.trend:+.0%}"
        + (f", earnings reaction {r.earn_react:+.1%} ({r.sessions_since:.0f} sessions ago)"
           if pd.notna(r.earn_react) else "")), axis=1)
    top.to_csv(os.path.join(out, f"top_{TOPN}.csv"))
    json.dump(dict(asof=str(ASOF.date()), entry=str(ENTRY.date()),
                   hold_window_end=str(WINDOW_END.date()), weights=WEIGHTS, filters=flt,
                   universe=len(df), eligible=int(df.eligible.sum()),
                   exclusions=df.excluded_reason[~df.eligible].value_counts().to_dict(),
                   note="trend and mom_12_1 selected after the 10-day backtest; see report"),
              open(os.path.join(out, "methodology.json"), "w"), indent=1)
    print(f"eligible {df.eligible.sum()} / {len(df)}")
    print(df.excluded_reason[~df.eligible].value_counts().to_string())
    cols = ["shortName", "price", "mom_12_1", "trend", "hi52", "earn_react", "sessions_since",
            "ret_5d", "vol_60", "next_earnings"]
    with pd.option_context("display.width", 250, "display.max_colwidth", 22):
        print(top[cols].round(3).to_string())


if __name__ == "__main__":
    main(sys.argv[1])
