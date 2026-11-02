"""Research-backed signals (see kb/research/strategy_evidence.md, config/signals.yaml).

Pure functions on point-in-time inputs. Volatilities are annualised decimals (0.30 = 30%).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def realized_vol(returns: Sequence[float], window: int = TRADING_DAYS) -> float:
    """Annualised realized vol of the last `window` daily log returns."""
    r = np.asarray(returns, dtype=float)[-window:]
    if len(r) < max(20, window // 2):
        return float("nan")
    return float(np.std(r, ddof=1) * np.sqrt(TRADING_DAYS))


def implied_move_pct(atm_call: float, atm_put: float, spot: float) -> float:
    """Straddle-implied move to expiry, as % of spot."""
    return (atm_call + atm_put) / spot * 100


def event_edge_ratio(
    hist_event_abs_moves_pct: Sequence[float], implied_move: float, min_events: int = 4
) -> float:
    """A1: median past |event move| / current implied move. >1 means options look cheap."""
    moves = [m for m in hist_event_abs_moves_pct if np.isfinite(m)]
    if len(moves) < min_events or implied_move <= 0:
        return float("nan")
    return float(np.median(moves) / implied_move)


def rv_iv_spread(returns: Sequence[float], atm_iv: float) -> float:
    """A2 (Goyal-Saretto): 12-month realized vol minus 1-month ATM implied vol."""
    return realized_vol(returns, TRADING_DAYS) - atm_iv


def iv_term_slope(atm_iv_near: float, atm_iv_next: float) -> float:
    """A3 (Vasquez): next-month ATM IV minus near-month ATM IV. Positive = upward slope."""
    return atm_iv_next - atm_iv_near


def straddle_momentum(
    monthly_straddle_returns: Sequence[float], lookback: int = 12, skip: int = 1
) -> float:
    """A4 (Heston et al.): mean straddle return over `lookback` months, skipping latest `skip`."""
    r = np.asarray(monthly_straddle_returns, dtype=float)
    window = r[-(lookback + skip) : len(r) - skip] if skip else r[-lookback:]
    if len(window) < max(3, lookback // 2):
        return float("nan")
    return float(np.nanmean(window))


def put_skew(iv_otm_put: float, iv_atm_call: float) -> float:
    """B1 (Xing-Zhang-Zhao): OTM put IV minus ATM call IV. High = bearish."""
    return iv_otm_put - iv_atm_call


def call_put_iv_spread(iv_call: float, iv_put: float) -> float:
    """B2 (Cremers-Weinbaum): call IV minus put IV at the same strike/expiry. High = bullish."""
    return iv_call - iv_put


def momentum_12_1(monthly_closes: Sequence[float]) -> float:
    """B3: return from t-12 to t-1 months (skip the most recent month)."""
    c = np.asarray(monthly_closes, dtype=float)
    if len(c) < 13:
        return float("nan")
    return float(c[-2] / c[-13] - 1)


def ts_momentum(monthly_closes: Sequence[float], lookback: int = 12) -> int:
    """B4: sign of the trailing `lookback`-month return (+1 up-trend, -1 down-trend, 0 unknown)."""
    c = np.asarray(monthly_closes, dtype=float)
    if len(c) < lookback + 1:
        return 0
    return int(np.sign(c[-1] / c[-1 - lookback] - 1))


def cross_sectional_rank(values: pd.Series, buckets: int = 10) -> pd.Series:
    """Bucket 1..buckets within one date's universe (NaNs stay NaN)."""
    pct = values.rank(pct=True)
    return np.ceil(pct * buckets).clip(1, buckets)


def zscore(values: pd.Series) -> pd.Series:
    """Cross-sectional z-score, winsorised at +/-3."""
    z = (values - values.mean()) / values.std(ddof=0)
    return z.clip(-3, 3)
