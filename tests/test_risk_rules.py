from datetime import date

from engine.domain import Leg, OptionType, Position, Proposal, Side
from engine.risk.rules import RiskLimits, check_proposal, safety_exits

LIM = RiskLimits(
    max_premium_at_risk_per_trade=20_000, max_open_positions=3,
    max_positions_per_underlying=1, max_positions_per_sector=2, monthly_loss_stop_inr=25_000,
)
EXP = date(2026, 11, 24)


def leg(strike: float, t: OptionType, price: float, side: Side = Side.BUY, lots: int = 1) -> Leg:
    return Leg(underlying="NATIONALUM", expiry=EXP, strike=strike, option_type=t,
               side=side, lots=lots, lot_size=3750, price=price)


def strangle(ce_px: float = 2.0, pe_px: float = 2.0) -> Proposal:
    legs = [leg(320, OptionType.CE, ce_px), leg(290, OptionType.PE, pe_px)]
    return Proposal(id="p1", strategy="long_strangle", underlying="NATIONALUM", expiry=EXP,
                    legs=legs, max_loss=sum(x.price * x.quantity for x in legs), sector="metals")


def pos(pnl: float | None = None, closed: bool = False) -> Position:
    return Position(underlying="NATIONALUM", expiry=EXP, strategy="long_strangle",
                    legs=strangle().legs, opened_on=date(2026, 10, 1),
                    closed_on=date(2026, 10, 10) if closed else None, realized_pnl=pnl,
                    sector="metals")


def rules(v): return {x.rule for x in v}


def test_clean_proposal_passes():
    assert check_proposal(strangle(), [], [], 0, LIM) == []


def test_size_cap():
    assert "size_cap" in rules(check_proposal(strangle(5, 5), [], [], 0, LIM))


def test_averaging_down_blocked():
    assert "averaging_down" in rules(check_proposal(strangle(), [pos()], [], 0, LIM))


def test_reentry_after_loss_blocked():
    closed = [pos(pnl=-30_000, closed=True)]
    assert "reentry_after_loss" in rules(check_proposal(strangle(), [], closed, 0, LIM))


def test_monthly_halt():
    assert "monthly_halt" in rules(check_proposal(strangle(), [], [], -26_000, LIM))


def test_call_heavy_strangle_rejected():
    # FY27 NALCO pattern: ~6x more premium in calls than puts
    assert "unbalanced_strangle" in rules(check_proposal(strangle(3.0, 0.5), [], [], 0, LIM))


def test_naked_short_rejected():
    p = strangle()
    p.legs.append(leg(340, OptionType.CE, 1.0, side=Side.SELL, lots=2))
    assert "naked_short" in rules(check_proposal(p, [], [], 0, LIM))


def test_physical_settlement_warning():
    v = safety_exits([pos()], {"NATIONALUM": 330.0}, today=date(2026, 11, 23))
    assert rules(v) == {"physical_settlement"}
    assert safety_exits([pos()], {"NATIONALUM": 300.0}, today=date(2026, 11, 23)) == []
