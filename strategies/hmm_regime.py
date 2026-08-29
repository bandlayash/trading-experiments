"""Strategy 5 -- Hidden Markov Model regime detection, refit walk-forward.

    fit a Gaussian HMM with `n_states` states on trailing daily log returns of the
        SIGNAL instrument, refit every `refit_every` trading days on the trailing
        `train_window` days ONLY -- never on data past the refit day
    label the state(s) with a positive fitted mean return "bullish"
    position: hold the TRADED instrument while the FILTERED probability of being in a
        bullish state is >= `prob_thresh`; otherwise hold cash

Hidden Markov Models are a standard tool for latent market-regime detection: fit a small
number of unobserved ("hidden") states, each with its own return distribution, to a
return series, and let the model infer -- day by day, never with certainty -- which state
is most likely active right now. Two states with different means and volatilities are a
natural read of "trending/calm" versus "choppy/turbulent" markets; that read is what this
strategy trades. See the `strategy/hmm-regime` branch for the full write-up and the
literature this is built on.

Why a walk-forward refit, and why a hand-rolled forward filter
----------------------------------------------------------------
Two look-ahead traps are specific to HMM strategies and do not arise in this repo's other
strategies, which is why this module is more involved than the rest:

1. **Fitting once on the whole sample.** An HMM fit on all 15 years of data has, at day
   1000, already learned the return distribution of the 2020 COVID crash and the 2022
   drawdown. That is a textbook look-ahead leak, and a common one in HMM-regime writeups
   that fit once and then walk the decoded states back over the training period. This
   module refits periodically, and every refit trains ONLY on data up to and including the
   refit day.

2. **`hmmlearn`'s own `predict_proba` smooths.** Given an array of observations,
   `GaussianHMM.predict_proba` runs the forward-BACKWARD algorithm over the WHOLE array --
   i.e. the probability it reports for day *t* is influenced by observations *after* t, if
   they are present in the array handed to it. Calling it on a growing window and reading
   off "today's" row is a subtle leak that a truncation test is specifically built to
   catch (see `tests/test_new_strategies.py`). `_forward_filter` below hand-rolls the
   forward-ONLY recursion instead: the probability assigned to day t depends only on
   observations 1..t. That is also the only quantity actually available to a live trader,
   who has never seen tomorrow's return.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.engine import COST_PER_SIDE, StrategyResult

NAME = "HMM Regime"
DEFAULTS = dict(n_states=2, refit_every=63, train_window=756, prob_thresh=0.5,
                random_state=42)


def _forward_filter(obs: np.ndarray, startprob: np.ndarray, transmat: np.ndarray,
                    means: np.ndarray, stds: np.ndarray) -> np.ndarray:
    """Causal forward-algorithm state probabilities P(state_t | obs[0..t]).

    Deliberately NOT `hmmlearn.predict_proba` -- see the module docstring. This is the
    textbook forward recursion for a Gaussian-emission HMM:

        alpha_0(s)   = startprob(s) * b_s(obs_0)
        alpha_t(s) propto b_s(obs_t) * sum_s' alpha_{t-1}(s') * transmat(s', s)

    renormalized to sum to 1 at every step. That normalization is what makes this the
    FILTERING distribution P(state_t | obs up to t) rather than the raw joint likelihood,
    which is exactly the quantity a causal strategy is allowed to use.
    """
    from scipy.stats import norm

    n_states = len(startprob)
    n = len(obs)
    b = np.stack([norm.pdf(obs, loc=means[s], scale=max(float(stds[s]), 1e-12))
                  for s in range(n_states)], axis=1)

    probs = np.zeros((n, n_states))
    alpha = startprob * b[0]
    total = alpha.sum()
    probs[0] = alpha / total if total > 0 else startprob
    for t in range(1, n):
        alpha = (probs[t - 1] @ transmat) * b[t]
        total = alpha.sum()
        probs[t] = alpha / total if total > 0 else probs[t - 1]
    return probs


def _fit_and_label(train_returns: np.ndarray, n_states: int, random_state: int):
    """Fit a Gaussian HMM on TRAINING data only. Returns HMM params + a bullish mask.

    "Bullish" is re-derived from the fitted mean of every state every time this is
    called, rather than trusting a fixed state index -- a refit can permute which index
    corresponds to which regime ("label switching"), so pinning meaning to an index would
    silently scramble the strategy's interpretation after any refit that reordered states.
    """
    from hmmlearn.hmm import GaussianHMM

    model = GaussianHMM(n_components=n_states, covariance_type="diag",
                        n_iter=100, random_state=random_state)
    model.fit(train_returns.reshape(-1, 1))

    means = model.means_.reshape(-1)
    stds = np.sqrt(model.covars_.reshape(-1))
    bullish = means > 0.0        # states with a positive fitted mean daily log return
    return model.startprob_, model.transmat_, means, stds, bullish


def signals(signal: pd.Series, n_states: int, refit_every: int, train_window: int,
           prob_thresh: float, random_state: int) -> pd.Series:
    """Boolean `bullish` series: P(bullish state | data up to today) >= prob_thresh.

    Refit points are every `refit_every` trading days, starting at the first available
    return. Each refit trains on the trailing `train_window` log returns available AT
    that point (fewer, if history is shorter than that yet), then `_forward_filter` scores
    every day up to the NEXT refit causally. The filter restarts from the new model's own
    `startprob_` at every refit rather than carrying probabilities across a parameter
    change -- see `_fit_and_label` on label switching.
    """
    log_ret = np.log(signal / signal.shift(1)).dropna()
    idx = log_ret.index
    values = log_ret.to_numpy()

    refit_starts = list(range(0, len(idx), refit_every))
    bullish_prob = pd.Series(np.nan, index=signal.index)

    for k, seg_start in enumerate(refit_starts):
        seg_end = refit_starts[k + 1] if k + 1 < len(refit_starts) else len(idx)
        train_start = max(0, seg_start - train_window)
        train_data = values[train_start:seg_start + 1]     # up to and including refit day
        if len(train_data) < max(4 * n_states, 30):
            continue         # not enough history yet to fit anything meaningful
        try:
            startprob, transmat, means, stds, bullish = _fit_and_label(
                train_data, n_states, random_state)
        except ValueError:
            continue          # degenerate window (e.g. near-zero variance): skip, stay flat

        seg_obs = values[seg_start:seg_end]
        seg_probs = _forward_filter(seg_obs, startprob, transmat, means, stds)
        p_bullish = seg_probs[:, bullish].sum(axis=1)
        bullish_prob.loc[idx[seg_start:seg_end]] = p_bullish

    return (bullish_prob >= prob_thresh).fillna(False)


def run(signal: pd.Series, traded: pd.Series, warmup: int = 252,
        **params) -> StrategyResult:
    p = {**DEFAULTS, **params}
    bullish = signals(signal, p["n_states"], p["refit_every"], p["train_window"],
                      p["prob_thresh"], p["random_state"])

    ret_traded = traded.pct_change()
    idx = signal.index[warmup:]

    strat = pd.Series(0.0, index=idx)
    invested, holding, round_trips = [], False, 0

    for day in idx:
        r = ret_traded.loc[day]
        strat.loc[day] = float(r) if (holding and not pd.isna(r)) else 0.0
        invested.append(1.0 if holding else 0.0)

        target = bool(bullish.loc[day])
        if target != holding:
            strat.loc[day] -= COST_PER_SIDE
            round_trips += int(not target)
            holding = target

    return StrategyResult(NAME, strat, float(np.mean(invested)), round_trips, p)
