"""Integrity tests for the MAG7 overnight and HMM regime strategies. Run:

    python tests/test_new_strategies.py

Unlike `tests/test_no_lookahead.py`, everything here runs on SYNTHETIC data generated
with a fixed seed -- no network access required. That is deliberate: these tests must be
runnable in any environment, including ones with no route to a market data provider, and
the properties being checked (no look-ahead, correct return arithmetic, cost application)
do not depend on real prices to demonstrate.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.engine import COST_PER_SIDE                        # noqa: E402
from strategies import hmm_regime, mag7_overnight               # noqa: E402

failures: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    if not condition:
        failures.append(label)


def make_ohlc(seed: int, n: int, start: str = "2018-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=n, freq="B")
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, n)))
    open_ = close * np.exp(rng.normal(0.0, 0.004, n))    # a same-day open near the prior close
    return pd.DataFrame({"Open": open_, "Close": close}, index=dates)


def make_price_series(seed: int, n: int, start: str = "2015-01-01",
                      drift: float = 0.0003, vol: float = 0.012) -> pd.Series:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=n, freq="B")
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, vol, n))), index=dates)


# --------------------------------------------------------------------------------------
# MAG7 overnight
# --------------------------------------------------------------------------------------

def test_mag7_overnight_return_arithmetic() -> None:
    """Hand-computed overnight return must match the formula exactly."""
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    ohlc = pd.DataFrame({"Open": [10.0, 10.5, 9.8, 11.0],
                        "Close": [10.2, 10.0, 10.5, 11.2]}, index=dates)
    ret = mag7_overnight.overnight_returns(ohlc)
    expected = pd.Series([10.5 / 10.2 - 1.0, 9.8 / 10.0 - 1.0, 11.0 / 10.5 - 1.0],
                         index=dates[:3])
    check(bool(np.allclose(ret.to_numpy(), expected.to_numpy())),
          "MAG7 overnight: Open_(t+1)/Close_t - 1 matches by hand", f"got {ret.tolist()}")
    check(len(ret) == len(ohlc) - 1,
          "MAG7 overnight: last (incomplete) day is dropped, not fabricated")


def test_mag7_overnight_no_lookahead() -> None:
    """Truncating the future must not change any already-computed overnight return."""
    ohlc = make_ohlc(seed=1, n=300)
    full = mag7_overnight.overnight_returns(ohlc)
    cut = len(ohlc) - 50
    trunc = mag7_overnight.overnight_returns(ohlc.iloc[:cut])
    overlap = trunc.index
    delta = (full.loc[overlap] - trunc).abs().max()
    check(delta < 1e-12, "MAG7 overnight: truncating the future changes nothing already computed",
          f"max |diff| = {delta:.2e}")


def test_mag7_overnight_portfolio() -> None:
    """Equal-weight across an unaligned basket; costs applied; missing names handled."""
    a = make_ohlc(seed=1, n=100, start="2018-01-01")
    b = make_ohlc(seed=2, n=100, start="2018-01-01")
    # `c` starts 40 trading days later -- simulates a name that hadn't IPO'd yet.
    c = make_ohlc(seed=3, n=60, start="2018-02-26")

    res = mag7_overnight.run({"A": a, "B": b, "C": c})

    check(res.round_trips == (len(a) - 1) + (len(b) - 1) + (len(c) - 1),
          "MAG7 overnight: round trips = sum of active name-nights across the basket",
          f"got {res.round_trips}")
    check(bool(np.isclose(res.exposure, 1.0)),
          "MAG7 overnight: at least one name listed every single night -> full exposure")

    # On a night with only A and B listed, the portfolio return must be their mean minus
    # cost on BOTH legs -- not A's or B's return alone, and not zero-cost.
    early_day = res.daily_ret.index[5]
    hand = (mag7_overnight.overnight_returns(a).loc[early_day]
           + mag7_overnight.overnight_returns(b).loc[early_day]) / 2.0 - 2.0 * COST_PER_SIDE
    check(bool(np.isclose(res.daily_ret.loc[early_day], hand)),
          "MAG7 overnight: 2-name night is the equal-weight mean, net of 2x cost",
          f"got {res.daily_ret.loc[early_day]:.6f}, expected {hand:.6f}")


# --------------------------------------------------------------------------------------
# HMM regime
# --------------------------------------------------------------------------------------

def test_hmm_no_lookahead() -> None:
    """The strong test: truncating the future must not change any past position or return.

    This is the one that actually proves `_forward_filter` (not `hmmlearn.predict_proba`)
    was the right call, and that refits never train on data past the refit day. If either
    were violated, truncating the series would change strategy returns on days well before
    the cut point, and this test would catch it exactly the way
    `tests/test_no_lookahead.py` catches it for the other four strategies.
    """
    n = 900
    signal = make_price_series(seed=7, n=n, drift=0.0002, vol=0.014)
    traded = signal * np.exp(np.cumsum(np.random.default_rng(8).normal(0, 0.002, n)))
    traded = pd.Series(traded.to_numpy(), index=signal.index)

    kwargs = dict(warmup=120, refit_every=30, train_window=200, prob_thresh=0.5,
                 random_state=42)
    full = hmm_regime.run(signal, traded, **kwargs).daily_ret
    cut = n - 150
    trunc = hmm_regime.run(signal.iloc[:cut], traded.iloc[:cut], **kwargs).daily_ret

    overlap = trunc.index
    delta = (full.loc[overlap] - trunc).abs().max()
    check(delta < 1e-9, f"HMM regime: no look-ahead over {len(overlap)} bars",
          f"max |diff| = {delta:.2e}")


def test_hmm_costs_and_flat_means_flat() -> None:
    signal = make_price_series(seed=11, n=700, drift=0.0002, vol=0.013)
    traded = signal
    res = hmm_regime.run(signal, traded, warmup=120, refit_every=30, train_window=180)

    n_charged = int(((res.daily_ret.diff().abs() > 0) & (res.daily_ret != 0)).sum())
    check(res.round_trips > 0 and n_charged > 0, "HMM regime: trades and pays costs",
          f"{res.round_trips} round trips")

    zero_days = int((res.daily_ret == 0.0).sum())
    check(zero_days > 0 and res.exposure < 1.0,
          "HMM regime: holds cash sometimes and earns exactly 0 there",
          f"{zero_days} flat days, exposure {res.exposure*100:.0f}%")


def test_hmm_forward_filter_matches_definition() -> None:
    """`_forward_filter` must reproduce the textbook forward recursion on a tiny example
    computable independently of the function itself."""
    startprob = np.array([0.5, 0.5])
    transmat = np.array([[0.9, 0.1], [0.2, 0.8]])
    means = np.array([0.01, -0.01])
    stds = np.array([0.01, 0.01])
    obs = np.array([0.01, 0.01, -0.01])

    from scipy.stats import norm
    probs = hmm_regime._forward_filter(obs, startprob, transmat, means, stds)

    # Hand-roll the same recursion independently.
    b = np.stack([norm.pdf(obs, loc=means[s], scale=stds[s]) for s in range(2)], axis=1)
    alpha0 = startprob * b[0]
    alpha0 /= alpha0.sum()
    alpha1 = (alpha0 @ transmat) * b[1]
    alpha1 /= alpha1.sum()

    check(bool(np.allclose(probs[0], alpha0)) and bool(np.allclose(probs[1], alpha1)),
          "HMM regime: _forward_filter matches an independent hand computation",
          f"got {probs[:2].tolist()}")
    check(bool(np.allclose(probs.sum(axis=1), 1.0)),
          "HMM regime: filtered probabilities sum to 1 on every day")


def test_hmm_degenerate_short_history_does_not_crash() -> None:
    """A window shorter than the minimum fittable size must stay flat, not raise."""
    signal = make_price_series(seed=3, n=40, drift=0.0, vol=0.01)
    res = hmm_regime.run(signal, signal, warmup=10, refit_every=63, train_window=756)
    check(res.exposure == 0.0 and res.daily_ret.abs().sum() == 0.0,
          "HMM regime: too little history to fit -> stays flat, does not crash")


if __name__ == "__main__":
    test_mag7_overnight_return_arithmetic()
    test_mag7_overnight_no_lookahead()
    test_mag7_overnight_portfolio()
    test_hmm_no_lookahead()
    test_hmm_costs_and_flat_means_flat()
    test_hmm_forward_filter_matches_definition()
    test_hmm_degenerate_short_history_does_not_crash()

    print(f"\n{'ALL PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
    raise SystemExit(1 if failures else 0)
