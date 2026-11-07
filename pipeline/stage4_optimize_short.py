"""Stage 4, short-horizon variant: a 3-name sleeve for a 10-session hold.

There is no existing book here (that config is private and not in this repo), so the
optimiser builds a standalone sleeve and compares it with simply holding SPY.

* Risk: covariance of the last 252 daily log returns, scaled to 10 sessions.
* Return: Stage-3 post-critique expected 10-session returns; SPY gets CAPM drift.
* Objective: maximise sleeve Sharpe over 10 sessions.
* Hard constraints: every pick has a positive expected return; >= 2 sectors; each weight in
  [W_MIN, W_MAX] (the code and this docstring use the same band -- see README §6).

Every 3-name combination is optimised; the runners-up are reported. Pass a capital amount
to get a whole-share order list -- it is printed only, never written into the run directory,
so no account size ends up in the repo.
"""
from __future__ import annotations

import itertools
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")
H = 10
K = 3
W_MIN, W_MAX = 0.20, 0.50


def opt(mu: np.ndarray, cov: np.ndarray, rf: float) -> tuple[np.ndarray, float]:
    n = len(mu)
    neg_sharpe = lambda w: -(w @ mu - rf) / np.sqrt(w @ cov @ w)
    res = minimize(neg_sharpe, np.full(n, 1 / n), bounds=[(W_MIN, W_MAX)] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], method="SLSQP")
    return res.x, -res.fun


def main(run_dir: str, capital: float | None) -> None:
    er = pd.read_csv(os.path.join(run_dir, "stage3_scenarios", "expected_returns.csv"))
    a = json.load(open(os.path.join(run_dir, "stage3_scenarios", "assumptions.json")))
    er = er[er.er_10d > 0].set_index("symbol")
    close = pd.read_pickle(os.path.join(CACHE, "close.pkl")).loc[:"2026-11-06"]
    syms = list(er.index)
    lr = np.log(close[syms + ["SPY"]]).diff().iloc[-252:].dropna()
    cov_all = lr.cov() * H
    rf10 = a["rf"] * H / 252
    spy_mu = (a["rf"] + a["erp"]) * H / 252
    spy_sig = np.sqrt(cov_all.loc["SPY", "SPY"])

    results = []
    for combo in itertools.combinations(syms, K):
        if er.loc[list(combo), "sector"].nunique() < 2:
            continue
        mu = er.loc[list(combo), "er_10d"].values
        cov = cov_all.loc[list(combo), list(combo)].values
        w, sh = opt(mu, cov, rf10)
        pm, ps = w @ mu, np.sqrt(w @ cov @ w)
        corr = lr[list(combo)].corr().values[np.triu_indices(K, 1)].mean()
        results.append(dict(picks=combo, weights=np.round(w, 3), sharpe_10d=sh, er_10d=pm,
                            sigma_10d=ps, p_up=norm.cdf(pm / ps), p10=pm - 1.2816 * ps,
                            p90=pm + 1.2816 * ps, avg_corr=corr,
                            sectors=sorted(er.loc[list(combo), "sector"].unique())))
    res = pd.DataFrame(results).sort_values("sharpe_10d", ascending=False)
    out = os.path.join(run_dir, "stage4_portfolio")
    os.makedirs(out, exist_ok=True)
    best = res.iloc[0]
    picks = pd.DataFrame({"symbol": best.picks, "weight": best.weights}).set_index("symbol")
    picks = picks.join(er[["sector", "price", "conviction", "er_10d", "sigma_10d", "p_up", "p10",
                           "p90"]])
    spy = dict(er_10d=spy_mu, sigma_10d=spy_sig, p_up=norm.cdf(spy_mu / spy_sig),
               p10=spy_mu - 1.2816 * spy_sig, p90=spy_mu + 1.2816 * spy_sig)
    picks.to_csv(os.path.join(out, "selected_additions.csv"))
    res.head(10).to_csv(os.path.join(out, "top_combinations.csv"), index=False)
    json.dump(dict(sleeve={k: (float(best[k]) if k not in ("picks", "weights", "sectors")
                               else list(map(str, best[k]))) for k in best.index},
                   spy=spy, constraints=dict(k=K, w_min=W_MIN, w_max=W_MAX, min_sectors=2),
                   combinations_evaluated=len(res)),
              open(os.path.join(out, "comparison.json"), "w"), indent=1, default=float)
    with pd.option_context("display.width", 250, "display.max_colwidth", 60):
        print(f"{len(res)} combinations evaluated\n")
        print(res.head(6)[["picks", "weights", "sharpe_10d", "er_10d", "sigma_10d", "p_up", "p10",
                           "p90", "avg_corr"]].round(4).to_string(index=False))
        print("\nSelected:\n", picks.round(4).to_string())
        print("\nSPY:", {k: round(v, 4) for k, v in spy.items()})
    if capital:
        print(f"\nWhole-share orders for {capital:,.0f} (not saved):")
        # Floor to whole shares, then repeatedly buy one more share of the pick furthest
        # below its target weight, provided that share fits the cash and keeps the pick
        # within W_MAX. Rounding must not break the constraint the optimiser enforced.
        tgt = picks.weight * capital
        n = {s: int(np.floor(tgt[s] / picks.price[s])) for s in picks.index}
        left = capital - sum(n[s] * picks.price[s] for s in picks.index)
        while True:
            ok = [s for s in picks.index if picks.price[s] <= left
                  and (n[s] + 1) * picks.price[s] <= W_MAX * capital]
            if not ok:
                break
            s = max(ok, key=lambda x: tgt[x] - n[x] * picks.price[x])
            n[s] += 1
            left -= picks.price[s]
        rows = [[s, n[s], picks.price[s], n[s] * picks.price[s]] for s in picks.index]
        for s, n, p, v in rows:
            print(f"  {s}: {n} sh @ ~{p:.2f} = {v:,.2f} ({v / capital:.0%})")
        print(f"  cash left: {left:,.2f}")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else None)
