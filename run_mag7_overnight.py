"""Score the MAG7 overnight strategy and its buy-and-hold / day-session complements.

This is a separate entry point from `run_benchmark.py` rather than a `--signal/--trade`
option on it, because the strategy is structurally different: a basket of individual
names, not one signal instrument expressed through one traded instrument. See
`strategies/mag7_overnight.py` for why.

    python run_mag7_overnight.py                 # print the table
    python run_mag7_overnight.py --write         # also refresh results/mag7_overnight.md
    python run_mag7_overnight.py --tickers AAPL MSFT NVDA   # any basket you like
"""

from __future__ import annotations

import argparse
import datetime as dt
import os

import pandas as pd

from common import StrategyResult, load_ohlc_universe, perf_stats, split_stats
from common.engine import COST_PER_SIDE
from strategies import mag7_overnight

OOS_START = "2020-01-01"
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

HEADER = (f"{'Strategy':<26}{'Sharpe':>8}{'IS':>7}{'OOS':>7}{'CAGR':>9}"
          f"{'Vol':>8}{'MaxDD':>9}{'Growth':>9}{'Exp':>7}{'Trades/yr':>11}")


def _row(name: str, ret: pd.Series, exposure: float, trades: float | None) -> str:
    s = split_stats(ret, OOS_START)
    a = s["all"]
    trades_str = f"{trades:.0f}" if trades is not None else "-"
    return (f"{name:<26}{a['sharpe']:>8.2f}{s['is']['sharpe']:>7.2f}"
            f"{s['oos']['sharpe']:>7.2f}{a['cagr']*100:>8.1f}%{a['ann_vol']*100:>7.1f}%"
            f"{a['max_dd']*100:>8.1f}%{a['equity_mult']:>8.2f}x{exposure*100:>6.0f}%"
            f"{trades_str:>11}")


def buy_and_hold_basket(ohlc_by_ticker: dict[str, pd.DataFrame], name: str) -> StrategyResult:
    """Equal-weight buy-and-hold across the same basket, rebalanced daily.

    Daily rebalancing (rather than buy-once-and-never-touch) keeps this comparable to the
    overnight strategy's daily-equal-weight convention, and avoids one early name (e.g.
    Nvidia's later multi-hundred-percent run) silently dominating the whole benchmark's
    weight over a 15-year window.
    """
    closes = pd.DataFrame({sym: df["Close"] for sym, df in ohlc_by_ticker.items()})
    daily_ret = closes.pct_change().mean(axis=1, skipna=True).fillna(0.0)
    return StrategyResult(name, daily_ret, exposure=1.0, round_trips=0)


def day_session_basket(ohlc_by_ticker: dict[str, pd.DataFrame]) -> StrategyResult:
    """The complementary session the overnight strategy skips: open -> close, every day.

    This is the single most useful comparison in the whole exercise -- see the branch
    write-up. It uses the same 2x cost-per-side convention as the overnight leg so the two
    are compared on equal footing, net of the same assumed trading costs.
    """
    day_rets = pd.DataFrame({sym: mag7_overnight.day_session_returns(df)
                             for sym, df in ohlc_by_ticker.items()})
    n_active = day_rets.count(axis=1)
    gross = day_rets.mean(axis=1)
    strat = (gross - 2.0 * COST_PER_SIDE).where(n_active > 0, 0.0)
    exposure = float((n_active > 0).mean()) if len(day_rets) else 0.0
    return StrategyResult("Day session (skipped)", strat, exposure,
                          round_trips=int(n_active.sum()))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tickers", nargs="+", default=list(mag7_overnight.MAG7),
                    help="basket to trade (default: the Magnificent Seven)")
    ap.add_argument("--write", action="store_true", help="refresh results/ artifacts")
    args = ap.parse_args()

    ohlc = load_ohlc_universe(args.tickers)
    overnight = mag7_overnight.run(ohlc)
    day_session = day_session_basket(ohlc)
    bh = buy_and_hold_basket(ohlc, f"Buy & hold {'+'.join(args.tickers)} (eq-wt)")

    lines = []

    def emit(text: str = "") -> None:
        print(text)
        lines.append(text)

    span = f"{overnight.daily_ret.index[0].date()} -> {overnight.daily_ret.index[-1].date()}"
    emit("=" * len(HEADER))
    emit(f"MAG7 overnight benchmark  |  basket={'+'.join(args.tickers)}")
    emit(f"{span}  ({len(overnight.daily_ret)} nights)  IS < {OOS_START} <= OOS")
    emit(f"Costs {COST_PER_SIDE*1e4:.0f} bps/side, charged on BOTH legs of every "
         f"overnight trade.  Sharpe at 0% risk-free.")
    emit("=" * len(HEADER))
    emit(HEADER)
    emit(_row(overnight.name, overnight.daily_ret, overnight.exposure,
              overnight.trades_per_year))
    emit("-" * len(HEADER))
    emit(_row(day_session.name, day_session.daily_ret, day_session.exposure,
              day_session.trades_per_year))
    emit(_row(bh.name, bh.daily_ret, bh.exposure, None))
    emit("=" * len(HEADER))

    emit("")
    emit("Per-ticker overnight Sharpe (own history -- names IPO'd at different times):")
    for sym in args.tickers:
        r = mag7_overnight.overnight_returns(ohlc[sym]) - 2.0 * COST_PER_SIDE
        s = perf_stats(r)
        emit(f"  {sym:<8} Sharpe {s['sharpe']:>6.2f}   CAGR {s['cagr']*100:>7.1f}%   "
             f"{len(r)} nights from {r.index[0].date()}")

    if args.write:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        stamp = dt.date.today().isoformat()
        md = os.path.join(RESULTS_DIR, "mag7_overnight.md")
        with open(md, "w", encoding="utf-8") as fh:
            fh.write("# MAG7 overnight -- benchmark results\n\n")
            fh.write(f"Generated by `python run_mag7_overnight.py --write` on **{stamp}**.\n")
            fh.write("Do not edit by hand -- rerun the command.\n\n```\n")
            fh.write("\n".join(lines))
            fh.write("\n```\n")
        print(f"\nWrote {md}")


if __name__ == "__main__":
    main()
