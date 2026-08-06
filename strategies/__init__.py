"""The three trend-following strategies under study.

Each module exposes the same interface:

    NAME      -- display name
    DEFAULTS  -- the parameter dict used for the headline results
    run(signal, traded, warmup=252, **params) -> StrategyResult

so `run_benchmark.py` can score them interchangeably on identical bars and costs.
"""

from . import donchian_aroon, seykota, sma_momentum

ALL = [donchian_aroon, sma_momentum, seykota]

__all__ = ["donchian_aroon", "sma_momentum", "seykota", "ALL"]
