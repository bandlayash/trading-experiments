"""Stage 3, short-horizon variant: 10-session return distributions with a mandatory red-team.

For each Stage-2 advancer:

1. **Pre-critique.** Read the Stage-2 conviction literally, as P(outperform SPY over 10
   sessions), and turn it into an alpha: alpha_pre = sigma_10 * PhiInv(conviction / 100).
   Expected return = CAPM drift over 10 sessions + alpha.
2. **Red-team.** The strongest case against step 1 is the evidence on this very branch: the
   pre-specified screen had no 10-day edge (top-10 baskets beat SPY in 50% of windows), and
   the conviction scores come from reading one week of headlines, a process that has never
   been validated. So alpha is shrunk by RED_TEAM_SHRINK. The adjustment is uniform *because
   the argument is uniform*; name-specific risks were already handled by Stage 2's
   advance/no-advance gate.
3. **Scenarios.** Bear / base / bull are the lower quartile, middle half and upper quartile of
   a normal with that mean and sigma_10, each represented by its conditional mean, with
   probabilities 0.25 / 0.50 / 0.25. They sum to one and weight back to the mean exactly.

sigma_10 uses the larger of 60-day and 1-year realised volatility, so a recent quiet spell
does not understate risk.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")
H = 10                    # sessions held
ERP = 0.05                # annual equity risk premium (assumption)
RED_TEAM_SHRINK = 0.25    # keep a quarter of the conviction-implied alpha
MAX_ADVANCE = 12
TAIL = norm.pdf(norm.ppf(0.75)) / 0.25    # conditional mean of a normal's top quartile, in sigmas


def risk_free() -> float:
    path = os.path.join(CACHE, "irx.json")
    if not os.path.exists(path):
        import yfinance as yf
        v = float(yf.Ticker("^IRX").history(period="5d")["Close"].dropna().iloc[-1]) / 100
        json.dump({"rf": v}, open(path, "w"))
    return json.load(open(path))["rf"]


def main(run_dir: str) -> None:
    s2 = pd.read_csv(os.path.join(run_dir, "stage2_adversarial", "ranked_candidates.csv"))
    s1 = pd.read_csv(os.path.join(run_dir, "stage1_screen", "top_30.csv")).set_index("symbol")
    sec = json.load(open(os.path.join(CACHE, "sectors_top30.json")))
    close = pd.read_pickle(os.path.join(CACHE, "close.pkl")).loc[:"2026-11-06"]
    lr = np.log(close).diff().iloc[-252:]
    rf = risk_free()
    out = os.path.join(run_dir, "stage3_scenarios")
    os.makedirs(out, exist_ok=True)

    adv = s2[s2.advance].sort_values("conviction", ascending=False).head(MAX_ADVANCE)
    spy = lr["SPY"]
    rows = []
    for _, r in adv.iterrows():
        sym = r.symbol
        vol = max(s1.loc[sym, "vol_60"], lr[sym].std() * np.sqrt(252))
        sig = vol * np.sqrt(H / 252)
        beta = lr[sym].cov(spy) / spy.var()
        drift = (rf + beta * ERP) * H / 252
        a_pre = sig * norm.ppf(np.clip(r.conviction, 1, 99) / 100)
        a_post = RED_TEAM_SHRINK * a_pre
        mu_pre, mu = drift + a_pre, drift + a_post
        sc = {"bear": mu - TAIL * sig, "base": mu, "bull": mu + TAIL * sig}
        row = dict(symbol=sym, sector=sec.get(sym, {}).get("sector"), price=s1.loc[sym, "price"],
                   conviction=r.conviction, beta_1y=beta, vol_ann=vol, sigma_10d=sig,
                   capm_drift_10d=drift, alpha_pre=a_pre, er_10d_pre=mu_pre, alpha_post=a_post,
                   er_10d=mu, p_up=norm.cdf(mu / sig), p_beat_spy_approx=norm.cdf(a_post / sig),
                   p10=mu - 1.2816 * sig, p90=mu + 1.2816 * sig,
                   bear=sc["bear"], base=sc["base"], bull=sc["bull"])
        rows.append(row)
        with open(os.path.join(out, f"{sym}.md"), "w") as f:
            f.write(f"# {sym} — 10-session scenario model\n\n"
                    f"Entry: open 2026-11-09. Exit: close 2026-11-20. Stage-2 conviction "
                    f"{r.conviction:.0f}/100 ({r.verdict}).\n\n"
                    f"| Input | Value |\n|---|---|\n"
                    f"| Volatility (max of 60d, 1y), annual | {vol:.1%} |\n"
                    f"| 1-sigma move over 10 sessions | {sig:.1%} |\n"
                    f"| Beta to SPY (1y daily) | {beta:.2f} |\n"
                    f"| CAPM drift, 10 sessions (rf {rf:.2%}, ERP {ERP:.0%}) | {drift:+.2%} |\n\n"
                    f"| Scenario | Probability | 10-session return |\n|---|---|---|\n"
                    f"| Bear | 0.25 | {sc['bear']:+.1%} |\n| Base | 0.50 | {sc['base']:+.1%} |\n"
                    f"| Bull | 0.25 | {sc['bull']:+.1%} |\n"
                    f"| **Probability-weighted** | 1.00 | **{mu:+.2%}** |\n\n"
                    f"## Red-team\n\nPre-critique, reading conviction literally as P(beat SPY), "
                    f"the alpha is {a_pre:+.2%} and the expected return {mu_pre:+.2%}. The "
                    f"strongest argument that this is wrong: this branch's own backtest found "
                    f"no 10-day edge in the screen that produced this name, and a conviction "
                    f"score from one week of headlines has no track record. Alpha is cut to "
                    f"{RED_TEAM_SHRINK:.0%}: {a_post:+.2%}, expected return {mu:+.2%}.\n\n"
                    f"**Post-critique:** P(up after 10 sessions) ≈ {norm.cdf(mu / sig):.0%}; "
                    f"10th-90th percentile {mu - 1.2816 * sig:+.1%} to {mu + 1.2816 * sig:+.1%}. "
                    f"Key risk in window: {r.key_window_risk}.\n")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out, "expected_returns.csv"), index=False)
    json.dump(dict(rf=rf, erp=ERP, horizon_sessions=H, red_team_shrink=RED_TEAM_SHRINK),
              open(os.path.join(out, "assumptions.json"), "w"), indent=1)
    with pd.option_context("display.width", 250):
        print(df[["symbol", "sector", "price", "conviction", "beta_1y", "sigma_10d", "er_10d_pre",
                  "er_10d", "p_up", "p10", "p90"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
