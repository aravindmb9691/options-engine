import math

import numpy as np
import pandas as pd

from engine.features import signals as s


def test_realized_vol_matches_input_scale():
    rng = np.random.default_rng(1)
    r = rng.normal(0, 0.02, 252)  # 2% daily ≈ 31.7% annual
    assert abs(s.realized_vol(r) - 0.02 * math.sqrt(252)) < 0.03


def test_event_edge_ratio():
    assert s.event_edge_ratio([8, 9, 7, 10, 6], implied_move=6.0) == 8 / 6
    assert math.isnan(s.event_edge_ratio([8, 9], implied_move=6.0))  # too few events


def test_vol_spreads_and_slope():
    assert s.iv_term_slope(0.30, 0.34) > 0
    assert s.put_skew(0.40, 0.30) > 0
    assert s.call_put_iv_spread(0.31, 0.30) > 0


def test_straddle_momentum_skips_latest_month():
    r = [0.1] * 12 + [-0.9]
    assert abs(s.straddle_momentum(r, lookback=12, skip=1) - 0.1) < 1e-12


def test_momentum_and_ts():
    closes = list(range(100, 114))  # rising
    assert s.momentum_12_1(closes) > 0
    assert s.ts_momentum(closes) == 1


def test_cross_sectional_rank_and_z():
    x = pd.Series(range(20), dtype=float)
    b = s.cross_sectional_rank(x, 10)
    assert b.min() == 1 and b.max() == 10
    assert abs(s.zscore(x).mean()) < 1e-9
