"""Shared harness: data loading, metrics, and the simulation conventions."""

from .data import fetch_close, fetch_ohlc, load_ohlc_universe, load_pair
from .engine import COST_PER_SIDE, StrategyResult, buy_and_hold
from .metrics import TRADING_DAYS, perf_stats, split_stats, sub_period_sharpe

__all__ = [
    "fetch_close", "fetch_ohlc", "load_ohlc_universe", "load_pair",
    "COST_PER_SIDE", "StrategyResult", "buy_and_hold",
    "TRADING_DAYS", "perf_stats", "split_stats", "sub_period_sharpe",
]
