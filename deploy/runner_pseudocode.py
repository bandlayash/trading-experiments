"""PSEUDOCODE ONLY -- a sketch of what a live runner would look like. It does not run.

This file exists to document the *shape* of a live deployment for the strategies in this
repo. It is not a bot. It imports no broker SDK, holds no credentials, and exits
immediately if you execute it. Every `broker.*` call below is an invented placeholder for
whatever real client you would eventually use.

Read `deploy/README.md` first, in particular "What any live deployment needs" -- the
properties described there (idempotency, reconciliation, structured logging, a kill
switch, alerting) are the difference between a script that runs and a system you can
trust with money. This sketch shows where each of them belongs; it implements none of
them.

The single most important idea in this file
-------------------------------------------
The signal is computed by importing the SAME module the backtest imports:

    from strategies import donchian_aroon
    breakout, breakdown = donchian_aroon.signals(closes, **params)

Not a reimplementation. Not a port. Not "the same logic, rewritten for live." The same
function, called with the same arguments.

Backtest-vs-live signal divergence is the classic way research results fail to
materialise, and it is almost never a dramatic bug. It is an off-by-one in a rolling
window, a `.shift(1)` that got dropped, a moving average computed over a slightly
different lookback, or a partially-formed current bar treated as a closed one. Each is
individually small and invisible; collectively they are the reason a strategy that
backtested at 0.90 Sharpe delivers something unrecognisable.

The only defence that actually works is sharing the code path -- and then verifying it.
A parity test that replays real history through the live signal function and asserts the
resulting position series is identical to the backtest's, bar for bar, is worth more than
any amount of code review.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------------
# Hard stop. This file is a template, not a live bot.
# ---------------------------------------------------------------------------------
raise SystemExit(
    "runner_pseudocode.py is PSEUDOCODE -- a template, not a live bot. It does not "
    "trade, does not connect to a broker, and is not intended to be executed. "
    "Read deploy/README.md before adapting it."
)


# =================================================================================
# Everything below this line is unreachable. It is documentation in the form of code.
# =================================================================================


# --- Configuration ---------------------------------------------------------------
# Read from the environment; NEVER hardcode credentials, and never commit them.
# Where these actually live depends on the host -- repo Secrets for GitHub Actions,
# Secrets Manager or SSM for Lambda, a root-owned file for a VM. See deploy/README.md.
#
# Note what is NOT here: no API key literals, no account numbers, no tokens. If you
# find yourself typing a secret into this file, stop.

STRATEGY_NAME = "donchian_aroon"   # which strategy module to run
SIGNAL_SYMBOL = "SMH"              # instrument the trend is read from
TRADE_SYMBOL = "SOXL"              # instrument actually held
POSITION_PCT = 0.90                # fraction of equity to deploy when long

# The kill switch. Checked before anything else happens. A single flag you can flip
# from a UI, without a commit or a deploy, that stops all trading. See deploy/README.md.
LIVE_ENABLED = "read from repo Variable / SSM parameter / env var"


def main() -> None:
    """One invocation = one decision. Structured as: observe, decide, converge, log."""

    # --- 0) Kill switch ----------------------------------------------------------
    # First thing, always. Before market checks, before data fetches, before anything
    # that could have a side effect. The whole value of a kill switch is that it is
    # unconditional and unmissable.
    if not kill_switch_enabled():
        log_event("halted", reason="kill_switch_off")
        return

    # --- 1) Is the market open? --------------------------------------------------
    # Ask the broker rather than computing it yourself. Holiday calendars change,
    # half-days exist, and getting this wrong means orders rejected or -- worse --
    # queued and filled at an unexpected time.
    if not broker.market_is_open():
        log_event("market_closed")
        return

    # --- 2) Fetch bars -----------------------------------------------------------
    # Only as much history as the signal needs, plus a margin. For the Donchian model
    # that is max(entry_len, exit_len, aroon_len) + 1 bars -- around 64 with the
    # default parameters.
    #
    # TWO SUBTLETIES THAT CAUSE REAL BUGS:
    #
    # (a) The current day's bar is INCOMPLETE while the market is open. The backtest
    #     evaluates signals on closed daily bars. If you run this at 11:00 and treat
    #     the partial bar as a close, you are computing a signal the backtest never
    #     saw. Either run only near the close, or explicitly drop the current bar --
    #     but decide deliberately, and make the choice match what the backtest assumes.
    #
    # (b) Use split- and dividend-adjusted closes, the same as `common/data.py`. A
    #     leveraged ETF like SOXL has split repeatedly; unadjusted prices would
    #     manufacture enormous phantom moves and fire signals that never existed.
    closes = broker.get_daily_closes(SIGNAL_SYMBOL, bars=bars_needed())

    if len(closes) < bars_needed():
        # Not enough history to evaluate the signal. Do nothing -- never guess.
        log_event("insufficient_history", have=len(closes), need=bars_needed())
        return

    # --- 3) Compute the signal ---------------------------------------------------
    # THE SAME MODULE THE BACKTEST USES. This import is the entire point of the file.
    #
    #     from strategies import donchian_aroon
    #     breakout, breakdown = donchian_aroon.signals(closes, **donchian_aroon.DEFAULTS)
    #
    # Do not reimplement `signals()` here "for efficiency" or "to make it live-friendly."
    # The moment there are two implementations, they will drift, and the backtest stops
    # being evidence about the thing you are actually running.
    #
    # Parameters come from the strategy module's DEFAULTS so that a change to the
    # research parameters propagates here automatically rather than silently not.
    strategy = import_strategy_module(STRATEGY_NAME)
    params = strategy.DEFAULTS
    breakout, breakdown = strategy.signals(closes, **params)

    # `signals()` returns full series (that is what the backtest needs). Live, only the
    # most recent bar matters.
    entry_triggered = bool(breakout.iloc[-1])
    exit_triggered = bool(breakdown.iloc[-1])

    # --- 4) Reconcile against the broker's ACTUAL position -----------------------
    # Never trust an internal notion of what you hold. Orders get rejected, partially
    # fill, or get cancelled at the close. The broker is the only source of truth.
    #
    # Note this also recovers the strategy's state machine for free: the Donchian model
    # is stateful (entry and exit triggers are independent, and between them the correct
    # action is "do nothing"), and "am I currently long?" is exactly the state needed.
    # Holding => apply the exit rule. Flat => apply the entry rule. No database required.
    actual_position = broker.get_position(TRADE_SYMBOL)   # None if flat
    currently_long = actual_position is not None

    # --- 5) Decide the TARGET state, not a delta ---------------------------------
    # Expressing the decision as "what should I hold?" rather than "what should I do?"
    # is what makes the run idempotent. Running this twice in a row produces one trade
    # and one no-op, because the second run observes the state the first one created.
    if currently_long:
        target_long = not exit_triggered
    else:
        target_long = entry_triggered

    # --- 6) Converge to the target ------------------------------------------------
    # Trade only the difference. If target == actual, this whole block is a no-op --
    # which is the common case, since these strategies round-trip roughly once a year.
    if target_long == currently_long:
        log_event("no_change", holding=currently_long,
                  breakout=entry_triggered, breakdown=exit_triggered)
        return

    if target_long:
        equity = broker.get_equity()
        notional = POSITION_PCT * equity

        # An idempotency key: a client-side order ID derived from something stable for
        # this decision (date + symbol + side). If the request times out and you retry,
        # the broker recognises the duplicate rather than opening a second position.
        # This closes the window where you genuinely cannot tell whether an order landed.
        client_order_id = f"{today()}-{TRADE_SYMBOL}-buy"

        order = broker.submit_order(
            symbol=TRADE_SYMBOL, notional=notional, side="buy",
            client_order_id=client_order_id,
        )
        # ACCEPTED IS NOT FILLED. This log records a submission, nothing more. The next
        # run's reconciliation step (4) is what confirms the position actually exists --
        # which is another reason the target-state pattern matters.
        log_event("order_submitted", side="buy", notional=notional, order_id=order.id)
        alert(f"BUY {TRADE_SYMBOL} {notional:.2f}")

    else:
        client_order_id = f"{today()}-{TRADE_SYMBOL}-sell"
        order = broker.close_position(TRADE_SYMBOL, client_order_id=client_order_id)
        log_event("order_submitted", side="sell", reason="channel_exit", order_id=order.id)
        alert(f"SELL {TRADE_SYMBOL} (channel exit)")


# --- Supporting sketches ----------------------------------------------------------
# All placeholders. None of these are implemented.


def kill_switch_enabled() -> bool:
    """Read the kill switch from wherever the host keeps it. Fail CLOSED.

    If the flag cannot be read -- parameter store unreachable, variable unset, malformed
    value -- return False. An unreadable kill switch must mean "do not trade", never
    "assume it is fine". The failure mode of trading when you meant to halt is far worse
    than the failure mode of skipping a day.
    """
    raise NotImplementedError


def bars_needed() -> int:
    """How much history the signal requires.

    Derive this from the strategy module's parameters rather than hardcoding a number,
    so that changing `exit_len` in the research does not silently starve the live signal
    of data. For the Donchian model: max(entry_len, exit_len, aroon_len) + 1.
    """
    raise NotImplementedError


def import_strategy_module(name: str):
    """Return the strategy module from `strategies/` by name.

    Deliberately dynamic so the runner is strategy-agnostic -- but the module it returns
    is the exact one `run_benchmark.py` scores. That shared identity is the guarantee.
    """
    raise NotImplementedError


def log_event(event: str, **fields) -> None:
    """Emit ONE structured record -- JSON lines, one object per event.

    Log the inputs to the decision, not just the decision. `{"action": "buy"}` is nearly
    useless three weeks later; `{"close": 241.30, "upper": 239.80, "aroon_up": 100,
    "breakout": true}` lets you verify the logic without rerunning anything.

    On a public host (GitHub Actions logs on a public repo are world-readable) assume
    everything here is published. Never log credentials, account numbers, or anything
    derived from them.
    """
    raise NotImplementedError


def alert(message: str) -> None:
    """Push a notification a human will actually see.

    This covers the "something happened" half of alerting. The other half -- the run that
    never happened, and therefore sends nothing -- needs a dead-man's switch: a heartbeat
    pinged on every successful completion, monitored by something external that alerts
    when the pings STOP. Only that catches total failure of the host or scheduler.
    """
    raise NotImplementedError


def today() -> str:
    """Date string used to build idempotency keys. Use the exchange's date, not UTC."""
    raise NotImplementedError


class broker:  # noqa: N801 -- a namespace placeholder, not a real class
    """Stand-in for whatever broker client you eventually use.

    Kept deliberately abstract. Naming a real SDK here would invite someone to fill in
    credentials and run it, which is exactly what this file is designed to prevent.
    """

    market_is_open = get_daily_closes = get_position = None
    get_equity = submit_order = close_position = None


if __name__ == "__main__":
    main()
