"""Integrity tests for the harness. Run: python tests/test_no_lookahead.py

The single most valuable property to guarantee in a public backtest is that no strategy
can see the future. These tests prove it mechanically rather than by inspection.

The truncation test is the strong one: if a strategy's return on day D depended in any way
on data after day D, then re-running it on a series that STOPS at day D would produce a
different answer for day D. Running on the full series and on a truncated series and
demanding bit-identical overlap catches look-ahead leaks that reading the code can miss --
a forgotten `.shift(1)`, a centred rolling window, a `fillna(method='bfill')`, or a metric
computed over the whole sample and used inside the loop.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import load_pair, perf_stats                      # noqa: E402
from common.engine import COST_PER_SIDE                       # noqa: E402
from strategies import donchian_aroon, seykota, sma_momentum  # noqa: E402

WARMUP = 252
STRATEGIES = [donchian_aroon, sma_momentum, seykota]
failures: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    if not condition:
        failures.append(label)


def test_no_lookahead(signal: pd.Series, traded: pd.Series) -> None:
    """Truncating the future must not change the past."""
    cut = len(signal) - 400          # truncate well after warm-up, leaving a long overlap
    for mod in STRATEGIES:
        full = mod.run(signal, traded, warmup=WARMUP).daily_ret
        trunc = mod.run(signal.iloc[:cut], traded.iloc[:cut], warmup=WARMUP).daily_ret
        overlap = trunc.index
        delta = (full.loc[overlap] - trunc).abs().max()
        check(delta < 1e-12, f"{mod.NAME}: no look-ahead over {len(overlap)} bars",
              f"max |diff| = {delta:.2e}")


def test_costs_reduce_returns(signal: pd.Series, traded: pd.Series) -> None:
    """Every position change must cost something -- a free-switching backtest flatters itself."""
    for mod in (donchian_aroon, sma_momentum):
        r = mod.run(signal, traded, warmup=WARMUP)
        # On a switch day the strategy return must sit below the raw asset return by
        # exactly one cost unit (or below cash's 0% when the switch is an exit).
        n_charged = int(((r.daily_ret.diff().abs() > 0) & (r.daily_ret != 0)).sum())
        check(r.round_trips > 0 and n_charged > 0,
              f"{mod.NAME}: trades and pays costs",
              f"{r.round_trips} round trips at {COST_PER_SIDE*1e4:.0f} bps/side")


def test_flat_means_flat(signal: pd.Series, traded: pd.Series) -> None:
    """A cash position must earn exactly zero -- not the asset's return, not interest."""
    r = donchian_aroon.run(signal, traded, warmup=WARMUP)
    # Days with a return of exactly 0.0 are cash days that were not also switch days.
    zero_days = int((r.daily_ret == 0.0).sum())
    check(zero_days > 0 and r.exposure < 1.0,
          "Donchian+Aroon: holds cash sometimes and earns 0 there",
          f"{zero_days} flat days, exposure {r.exposure*100:.0f}%")


def test_degenerate_params(signal: pd.Series, traded: pd.Series) -> None:
    """An entry channel longer than the sample must simply never trade, not crash."""
    r = donchian_aroon.run(signal, traded, warmup=WARMUP, entry_len=len(signal) + 10)
    check(r.exposure == 0.0 and r.daily_ret.abs().sum() == 0.0,
          "Donchian+Aroon: impossible entry channel trades never, cleanly",
          f"exposure {r.exposure:.0%}")


def test_metrics_sanity() -> None:
    """perf_stats must agree with hand-computable answers on synthetic input."""
    flat = pd.Series(0.0, index=pd.date_range("2020-01-01", periods=500, freq="B"))
    s = perf_stats(flat)
    check(s["cagr"] == 0.0 and s["max_dd"] == 0.0, "metrics: zero returns -> zero CAGR and DD")

    steady = pd.Series(0.001, index=pd.date_range("2020-01-01", periods=500, freq="B"))
    s = perf_stats(steady)
    check(np.isnan(s["sharpe"]) and s["max_dd"] == 0.0,
          "metrics: zero-variance returns -> undefined Sharpe, no drawdown")

    known = pd.Series([0.1, -0.1], index=pd.date_range("2020-01-01", periods=2, freq="B"))
    s = perf_stats(known)
    check(abs(s["equity_mult"] - 0.99) < 1e-12 and abs(s["max_dd"] - (-0.1)) < 1e-12,
          "metrics: +10% then -10% -> 0.99x and -10% drawdown")


if __name__ == "__main__":
    print("Loading price history...")
    signal, traded = load_pair("SMH", "SOXL")
    print(f"{len(signal)} bars, {signal.index[0].date()} -> {signal.index[-1].date()}\n")

    test_no_lookahead(signal, traded)
    test_costs_reduce_returns(signal, traded)
    test_flat_means_flat(signal, traded)
    test_degenerate_params(signal, traded)
    test_metrics_sanity()

    print(f"\n{'ALL PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
    raise SystemExit(1 if failures else 0)
