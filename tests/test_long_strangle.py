from datetime import date

from engine.domain import OptionType
from engine.strategies.base import ChainRow, MarketContext
from engine.strategies.long_strangle import LongStrangle


def ctx(**kw) -> MarketContext:
    chain = [ChainRow(k, t, 3.0) for k in range(270, 345, 10) for t in OptionType]
    base = dict(asof=date(2026, 10, 30), underlying="NATIONALUM", spot=303.0,
                expiry=date(2026, 11, 24), lot_size=3750, chain=chain, iv_percentile=30,
                implied_move_pct=6.0, hist_event_move_pct=8.0, next_event=date(2026, 11, 2))
    base.update(kw)
    return MarketContext(**base)


def test_eligible_when_cheap_and_event_near():
    assert LongStrangle().eligible(ctx())


def test_not_eligible_when_iv_rich():
    assert not LongStrangle().eligible(ctx(iv_percentile=80))


def test_not_eligible_without_edge():
    assert not LongStrangle().eligible(ctx(hist_event_move_pct=6.0))


def test_build_and_max_loss():
    s = LongStrangle()
    legs = s.build(ctx())
    assert {leg.option_type for leg in legs} == {OptionType.CE, OptionType.PE}
    assert s.max_loss(legs) == 2 * 3.0 * 3750
