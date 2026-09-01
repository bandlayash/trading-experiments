"""Generate every chart published in this repo, into `results/charts/`.

    python make_charts.py

Charts are committed as PNG rather than SVG deliberately: GitHub's markdown renderer
sanitises embedded SVG in ways that can silently drop styling, whereas a PNG referenced
with a relative path always renders. They are drawn on an explicit white background so
they stay legible in GitHub's dark theme, where a transparent background would leave
dark text on a dark page.

Everything here is derived from the same `run_benchmark.py` machinery -- no chart shows a
number the tables do not.
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")            # headless: no display needed, and keeps CI simple
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402
import pandas as pd              # noqa: E402

from common import (fetch_close, load_ohlc_universe, load_pair,  # noqa: E402
                    buy_and_hold, perf_stats)
from common.engine import COST_PER_SIDE  # noqa: E402
from strategies import (donchian_aroon, ema_rsi_meanrev, hmm_regime,  # noqa: E402
                        mag7_overnight, seykota, sma_momentum)

WARMUP = 252
OOS_START = "2020-01-01"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "charts")

# A colour-blind-safe qualitative palette (Okabe-Ito). Benchmarks are drawn in grey and
# dashed throughout so a reader can tell strategy from benchmark without the legend.
COLORS = {
    "Donchian+Aroon":     "#0072B2",
    "SMA+Momentum":       "#D55E00",
    "Seykota":            "#009E73",
    "EMA9/RSI14 MeanRev": "#CC79A7",
    "HMM Regime":         "#E69F00",
}
BENCH_COLORS = {
    "Buy & hold SPY":  "#111111",
    "Buy & hold SMH":  "#666666",
    "Buy & hold SOXL": "#999999",
}

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 10,
})


def _save(fig, name: str) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(path, os.path.dirname(OUT_DIR))}")
    return path


def load_all():
    signal, traded = load_pair("SMH", "SOXL")
    results = [mod.run(signal, traded, warmup=WARMUP)
               for mod in (donchian_aroon, sma_momentum, seykota, ema_rsi_meanrev,
                           hmm_regime)]
    idx = results[0].daily_ret.index
    benches = [buy_and_hold(fetch_close("SPY"), idx, "Buy & hold SPY"),
               buy_and_hold(signal, idx, "Buy & hold SMH"),
               buy_and_hold(traded, idx, "Buy & hold SOXL")]
    return results, benches, idx


def chart_equity(results, benches, idx) -> None:
    """Growth of $1, log scale.

    Log scale is not a stylistic choice: on a linear axis a 262x outcome flattens every
    other line into the floor, which would make the chart a picture of one strategy
    rather than a comparison. On a log axis equal vertical distances are equal
    percentage moves, so the slopes are directly comparable.
    """
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for b in benches:
        ax.plot(idx, b.equity_curve(), label=b.name, color=BENCH_COLORS[b.name],
                lw=1.2, ls="--", alpha=0.9)
    for r in results:
        ax.plot(idx, r.equity_curve(), label=r.name, color=COLORS[r.name], lw=1.8)

    ax.axvline(pd.Timestamp(OOS_START), color="black", lw=1, alpha=0.35)
    ax.annotate("out-of-sample →", xy=(pd.Timestamp(OOS_START), ax.get_ylim()[1]),
                xytext=(6, -12), textcoords="offset points", fontsize=8, alpha=0.6)

    ax.set_yscale("log")
    ax.set_ylabel("Growth of $1 (log scale)")
    ax.set_title("Equity curves, net of 5 bps/side  |  SMH signal → SOXL, 2012–2026")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    _save(fig, "equity_curves.png")


def chart_drawdown(results, benches, idx) -> None:
    """Underwater plot -- the chart that shows what holding these actually felt like."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for b in benches:
        if b.name != "Buy & hold SPY":
            continue                      # one reference line keeps this readable
        eq = b.equity_curve()
        ax.plot(idx, (eq / eq.cummax() - 1) * 100, label=b.name,
                color=BENCH_COLORS[b.name], lw=1.2, ls="--")
    for r in results:
        eq = r.equity_curve()
        ax.plot(idx, (eq / eq.cummax() - 1) * 100, label=r.name,
                color=COLORS[r.name], lw=1.5)

    ax.set_ylabel("Drawdown from peak (%)")
    ax.set_title("Underwater plot — depth and duration of losses")
    ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
    _save(fig, "drawdowns.png")


def chart_risk_return(results, benches) -> None:
    """CAGR against max drawdown. The 'is the extra return worth it' picture."""
    # Donchian and buy-and-hold SOXL sit close together in the top-right, and their
    # default right-hand labels overlap. Nudging Donchian's label above its marker is
    # enough to separate them; the rest are uncrowded.
    LABEL_POS = {"Donchian+Aroon": (0, 15, "center")}
    DEFAULT = (9, -4, "left")

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for item, colors, marker in ((results, COLORS, "o"), (benches, BENCH_COLORS, "s")):
        for r in item:
            s = perf_stats(r.daily_ret)
            x, y = -s["max_dd"] * 100, s["cagr"] * 100
            ax.scatter(x, y, s=160, marker=marker, color=colors[r.name],
                       edgecolor="white", zorder=3)
            dx, dy, ha = LABEL_POS.get(r.name, DEFAULT)
            ax.annotate(f"{r.name}\nSharpe {s['sharpe']:.2f}", (x, y),
                        textcoords="offset points", xytext=(dx, dy), fontsize=8,
                        ha=ha, zorder=4)

    ax.set_xlabel("Max drawdown (%, worse →)")
    ax.set_ylabel("CAGR (%)")
    ax.set_title("Return vs. drawdown  —  circles: strategies, squares: buy & hold")
    ax.margins(0.22)
    _save(fig, "risk_return.png")


def chart_is_oos(results, benches) -> None:
    """In-sample vs out-of-sample Sharpe. Bars that collapse rightward were fitted."""
    names, is_v, oos_v, cols = [], [], [], []
    for r in results + benches:
        idx = r.daily_ret.index
        names.append(r.name.replace("Buy & hold ", "B&H "))
        is_v.append(perf_stats(r.daily_ret.loc[idx < OOS_START])["sharpe"])
        oos_v.append(perf_stats(r.daily_ret.loc[idx >= OOS_START])["sharpe"])
        cols.append(COLORS.get(r.name, BENCH_COLORS.get(r.name, "#999999")))

    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(x - 0.2, is_v, 0.4, color=cols, alpha=0.55, edgecolor="white")
    ax.bar(x + 0.2, oos_v, 0.4, color=cols, edgecolor="white")
    ax.axhline(1.0, color="black", lw=1, ls=":", alpha=0.5)
    # Left edge: the right-hand side is occupied by the tallest benchmark bars.
    ax.annotate("Sharpe = 1.0", xy=(-0.45, 1.03), fontsize=8, alpha=0.6, ha="left")

    # Each bar keeps its strategy's colour, so a colour-coded legend would wrongly
    # suggest blue means "in-sample". Use neutral proxy patches for the light/dark
    # convention instead.
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor="#777777", alpha=0.55, label="In-sample (2012–2019)"),
                       Patch(facecolor="#777777", label="Out-of-sample (2020–2026)")],
              fontsize=8, loc="upper left", framealpha=0.95)

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Sharpe ratio")
    ax.set_title("In-sample vs out-of-sample Sharpe — a large drop rightward means overfitting")
    _save(fig, "is_vs_oos.png")


def chart_exposure(results) -> None:
    """How much of the time each strategy actually holds a position."""
    names = [r.name for r in results]
    exp = [r.exposure * 100 for r in results]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bars = ax.barh(names, exp, color=[COLORS[n] for n in names], edgecolor="white")
    for bar, v in zip(bars, exp):
        ax.annotate(f"{v:.1f}%", (v, bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0), textcoords="offset points", va="center", fontsize=9)
    ax.set_xlabel("Share of days holding a position (%)")
    ax.set_title("Market exposure — idle capital is why Sharpe and per-trade edge diverge")
    ax.set_xlim(0, 100)
    _save(fig, "exposure.png")


def chart_single(result, benches, idx, filename: str) -> None:
    """Per-strategy equity curve against the three buy-and-hold references."""
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for b in benches:
        ax.plot(idx, b.equity_curve(), label=b.name, color=BENCH_COLORS[b.name],
                lw=1.1, ls="--", alpha=0.9)
    ax.plot(idx, result.equity_curve(), label=result.name,
            color=COLORS[result.name], lw=2.2)
    ax.axvline(pd.Timestamp(OOS_START), color="black", lw=1, alpha=0.35)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $1 (log scale)")
    s = perf_stats(result.daily_ret)
    ax.set_title(f"{result.name} — Sharpe {s['sharpe']:.2f}, "
                 f"CAGR {s['cagr']*100:.1f}%, max DD {s['max_dd']*100:.1f}%")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    _save(fig, filename)


def chart_mag7_sessions() -> None:
    """MAG7 overnight against the day session it skips, and against holding the basket.

    This one cannot share the equity-curve chart above: it trades seven individual names on
    a close-to-open schedule, not SMH-signal-into-SOXL, so its bars are a different
    instrument on a different calendar. Plotting them on one axis would invite a comparison
    that is not being made.
    """
    from run_mag7_overnight import buy_and_hold_basket, day_session_basket

    ohlc = load_ohlc_universe(list(mag7_overnight.MAG7))
    overnight = mag7_overnight.run(ohlc)
    idx = overnight.daily_ret.index
    day = day_session_basket(ohlc, idx)
    bh = buy_and_hold_basket(ohlc, "Buy & hold basket (eq-wt)", idx)
    spy = buy_and_hold(fetch_close("SPY"), idx, "Buy & hold SPY")

    # Both gross and net are drawn. Net alone would be a chart about the cost assumption:
    # the two net lines fall to 0.60x and 0.06x and visibly do NOT reconstruct the
    # buy-and-hold line, whereas the two GROSS lines multiply back to it almost exactly.
    # That reconstruction is the actual finding, so it has to be the thing you can see.
    cost = 2.0 * COST_PER_SIDE
    fig, ax = plt.subplots(figsize=(10, 5.5))

    def _curve(series):
        return (1.0 + series).cumprod()

    series = [
        (spy.daily_ret, "Buy & hold SPY", "#777777", 1.2, "--", 0.9),
        (bh.daily_ret, "Buy & hold basket (eq-wt)", "#111111", 1.5, "--", 1.0),
        (overnight.daily_ret + cost, "Overnight, gross", "#0072B2", 2.0, "-", 1.0),
        (overnight.daily_ret, "Overnight, net of 10 bps/night", "#0072B2", 1.3, ":", 0.75),
        (day.daily_ret + cost, "Day session, gross", "#D55E00", 2.0, "-", 1.0),
        (day.daily_ret, "Day session, net", "#D55E00", 1.3, ":", 0.75),
    ]
    for ret, label, color, lw, ls, alpha in series:
        s = perf_stats(ret)
        ax.plot(idx, _curve(ret), label=f"{label}  (Sharpe {s['sharpe']:.2f})",
                color=color, lw=lw, ls=ls, alpha=alpha)

    ax.axvline(pd.Timestamp(OOS_START), color="black", lw=1, alpha=0.35)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $1 (log scale)")
    ax.set_title("MAG7 sessions — the overnight premium, before and after costs")
    ax.legend(loc="lower left", fontsize=8, framealpha=0.9, ncol=1)
    _save(fig, "mag7_sessions.png")


def main() -> None:
    print("Loading data...")
    results, benches, idx = load_all()
    print(f"{len(idx)} bars, {idx[0].date()} -> {idx[-1].date()}\nWriting charts:")

    chart_equity(results, benches, idx)
    chart_drawdown(results, benches, idx)
    chart_risk_return(results, benches)
    chart_is_oos(results, benches)
    chart_exposure(results)

    slugs = {"Donchian+Aroon": "donchian_aroon", "SMA+Momentum": "sma_momentum",
             "Seykota": "seykota", "EMA9/RSI14 MeanRev": "ema_rsi_meanrev",
             "HMM Regime": "hmm_regime"}
    for r in results:
        chart_single(r, benches, idx, f"eq_{slugs[r.name]}.png")

    chart_mag7_sessions()

    print(f"\nDone -> {OUT_DIR}")


if __name__ == "__main__":
    main()
