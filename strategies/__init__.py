"""The signal/traded-pair strategies under study -- trend-following, mean-reversion, and
regime detection alike.

Each module in `ALL` exposes the same interface:

    NAME      -- display name
    DEFAULTS  -- the parameter dict used for the headline results
    run(signal, traded, warmup=252, **params) -> StrategyResult

so `run_benchmark.py` can score them interchangeably on identical bars and costs.

`mag7_overnight` is deliberately NOT in `ALL`: it trades a basket of individual names on
a close-to-open schedule rather than one signal/traded pair, so it does not share this
interface and is scored by its own `run_mag7_overnight.py` instead. See that module's
docstring.
"""

from . import donchian_aroon, ema_rsi_meanrev, hmm_regime, mag7_overnight, seykota, sma_momentum

ALL = [donchian_aroon, sma_momentum, seykota, ema_rsi_meanrev, hmm_regime]

__all__ = ["donchian_aroon", "sma_momentum", "seykota", "ema_rsi_meanrev", "hmm_regime",
          "mag7_overnight", "ALL"]
