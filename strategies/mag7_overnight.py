"""MAG7 overnight -- buy the close, sell the next open, every trading day, every name.

    for each ticker in MAG7 and each trading day t:
        enter at today's close, exit at tomorrow's open
        overnight_return_t = Open_{t+1} / Close_t - 1

Portfolio: equal-weight across whichever MAG7 names have data on a given night (a name
simply does not exist before its IPO -- see `common.data.load_ohlc_universe`, which keeps
each ticker on its own index rather than truncating everything to the youngest listing).

This is structurally different from every other strategy in this repo, and deliberately
lives outside `run_benchmark.py`'s single signal/traded-pair harness because of it:

  * It trades a BASKET of individual names, not one signal instrument expressed through
    one traded instrument.
  * There is no indicator and no decision. The position is on every single night, for
    every name, unconditionally -- `DEFAULTS` is empty because there is nothing to tune.
  * The return recorded against day `t` is not fully realized until the open of day
    `t + 1`. Every other strategy here books a return that is entirely determined by data
    up to and including day `t`'s close; this one, by construction, cannot be -- there is
    no such thing as an overnight return without a following morning. That is not a
    look-ahead leak (nothing about the DECISION to trade depends on future data -- the
    strategy trades unconditionally, every night), but it is a real convention difference
    from the rest of the repo and is called out explicitly rather than glossed over.

Full write-up, including why daily round-tripping is a much bigger problem for a small
cash account than it looks on paper: the `strategy/mag7-overnight` branch (its landing
page).
"""

from __future__ import annotations

import pandas as pd

from common.engine import COST_PER_SIDE, StrategyResult

NAME = "MAG7 Overnight"
MAG7 = ("AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA")
DEFAULTS: dict = {}   # nothing to tune -- see module docstring


def overnight_returns(ohlc: pd.DataFrame) -> pd.Series:
    """Return indexed by the ENTRY day t: buy at Close_t, sell at Open_{t+1}.

    The final row is dropped rather than left as NaN or fabricated from a same-day price
    -- there is no "tomorrow" to sell into yet, so that trade simply has not happened.
    """
    open_next = ohlc["Open"].shift(-1)
    ret = open_next / ohlc["Close"] - 1.0
    return ret.iloc[:-1]


def day_session_returns(ohlc: pd.DataFrame) -> pd.Series:
    """The complementary session this strategy deliberately skips: Open_t -> Close_t.

    Not used by `run()`. Provided so the day-vs-night decomposition discussed in the
    write-up can be reproduced by anyone from the same two functions, rather than the
    branch page quoting a number nobody else can regenerate.
    """
    return ohlc["Close"] / ohlc["Open"] - 1.0


def run(ohlc_by_ticker: dict[str, pd.DataFrame], warmup: int = 0,
        **params) -> StrategyResult:
    """Equal-weight the overnight return across whichever names are listed that night.

    Every name is entered and exited every single night it has data -- there is no
    `holding` state to track and no per-name entry/exit decision, so unlike the other
    strategies this is a single vectorized pass over the whole basket rather than a
    day-by-day state machine.
    """
    per_ticker = {sym: overnight_returns(df) for sym, df in ohlc_by_ticker.items()}
    rets = pd.DataFrame(per_ticker).sort_index()
    if warmup:
        rets = rets.iloc[warmup:]

    n_active = rets.count(axis=1)                    # names actually listed that night
    gross = rets.mean(axis=1)                         # NaN on a night with zero listings
    # Two round trips' worth of cost per active name every night: one to enter at the
    # close, one to exit at the open.
    strat = (gross - 2.0 * COST_PER_SIDE).where(n_active > 0, 0.0)

    exposure = float((n_active > 0).mean()) if len(rets) else 0.0
    round_trips = int(n_active.sum())                 # one buy->sell cycle per name-night

    return StrategyResult(NAME, strat, exposure, round_trips, dict(params))
