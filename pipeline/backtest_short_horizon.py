"""How much does the short-horizon score actually tell you about the next 10 trading days?

Every 10 trading days (non-overlapping holds), rank the universe on data up to the close,
buy at the next open, sell at the close 10 sessions later -- exactly the trade being
considered. Report, per quintile and for the top 10 names:

  * mean 10-day return, and mean excess return over the equal-weight universe
  * hit rate (share of picks that finished positive)
  * hit rate vs SPY over the same window

Split in-sample (first half of dates) / out-of-sample (second half) as on the strategy
branches. The universe is *today's* largest companies, so this is survivorship-biased in
favour of momentum: read the numbers as an upper bound, not an estimate.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import WEIGHTS, composite, features  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")
HOLD = 10
TOPN = 10


def main(outdir: str) -> None:
    close = pd.read_pickle(os.path.join(CACHE, "close.pkl"))
    opn = pd.read_pickle(os.path.join(CACHE, "open.pkl")).reindex_like(close)
    spy_c, spy_o = close.pop("SPY"), opn.pop("SPY")
    feats = features(close)
    scores = {"composite": composite(feats)}
    for k, w in WEIGHTS.items():
        scores[k] = feats[k] * np.sign(w)

    # entry at open t+1, exit at close t+HOLD
    fwd = close.shift(-HOLD) / opn.shift(-1) - 1
    spy_fwd = spy_c.shift(-HOLD) / spy_o.shift(-1) - 1
    first = feats["mom_12_1"].notna().sum(axis=1).gt(300).idxmax()
    dates = close.index[close.index.get_loc(first)::HOLD]
    dates = [d for d in dates if fwd.loc[d].notna().sum() > 300]
    half = len(dates) // 2

    rows, top_rows = [], []
    for name, s in scores.items():
        for i, d in enumerate(dates):
            sc, fr = s.loc[d], fwd.loc[d]
            ok = sc.notna() & fr.notna()
            sc, fr = sc[ok], fr[ok]
            ew = fr.mean()
            q = pd.qcut(sc.rank(method="first"), 5, labels=False)
            for k in range(5):
                r = fr[q == k]
                rows.append(dict(signal=name, date=d, period="IS" if i < half else "OOS",
                                 quintile=k + 1, ret=r.mean(), excess=r.mean() - ew,
                                 hit=(r > 0).mean(), beat_spy=(r > spy_fwd.loc[d]).mean()))
            top = fr[sc.nlargest(TOPN).index]
            top_rows.append(dict(signal=name, date=d, period="IS" if i < half else "OOS",
                                 ret=top.mean(), excess=top.mean() - ew, spy=spy_fwd.loc[d],
                                 hit=(top > 0).mean(), basket_up=top.mean() > 0,
                                 basket_beat_spy=top.mean() > spy_fwd.loc[d],
                                 worst=top.min()))
    q = pd.DataFrame(rows)
    t = pd.DataFrame(top_rows)
    os.makedirs(outdir, exist_ok=True)
    q.to_csv(os.path.join(outdir, "backtest_quintiles_by_date.csv"), index=False)
    t.to_csv(os.path.join(outdir, "backtest_top10_by_date.csv"), index=False)

    qs = (q.groupby(["signal", "period", "quintile"])[["ret", "excess", "hit"]].mean()
            .unstack("quintile"))
    spread = (q[q.quintile == 5].set_index(["signal", "date"]).excess
              - q[q.quintile == 1].set_index(["signal", "date"]).excess)
    tstat = spread.groupby("signal").agg(lambda x: x.mean() / x.std() * np.sqrt(len(x)))
    ts = t.groupby(["signal", "period"]).agg(
        n=("ret", "size"), mean_ret=("ret", "mean"), mean_excess=("excess", "mean"),
        spy=("spy", "mean"), pick_hit=("hit", "mean"), basket_up=("basket_up", "mean"),
        basket_beat_spy=("basket_beat_spy", "mean"), worst_pick=("worst", "min"))
    base = dict(
        windows=len(dates), first=str(dates[0].date()), last=str(dates[-1].date()),
        universe_stock_hit=float((fwd.loc[dates] > 0).stack().mean()),
        universe_mean=float(fwd.loc[dates].stack().mean()),
        universe_median=float(fwd.loc[dates].stack().median()),
        universe_p10=float(fwd.loc[dates].stack().quantile(0.10)),
        universe_p90=float(fwd.loc[dates].stack().quantile(0.90)),
        spy_hit=float((spy_fwd.loc[dates] > 0).mean()),
        spy_mean=float(spy_fwd.loc[dates].mean()),
    )
    with open(os.path.join(outdir, "backtest_summary.json"), "w") as f:
        json.dump(dict(base=base, q5_minus_q1_tstat=tstat.round(2).to_dict()), f, indent=1)
    pd.set_option("display.width", 200)
    print(json.dumps(base, indent=1))
    print("\nQ5-Q1 excess spread t-stat (all dates):\n", tstat.round(2))
    print("\nTop-10 basket:\n", ts.round(4))
    print("\nComposite quintile excess (bp):\n",
          (qs.loc["composite"]["excess"] * 1e4).round(0))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(CACHE, "bt"))
