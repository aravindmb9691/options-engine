"""Hard risk rules. Pure functions, no I/O, no LLM. Every rule is unit-tested."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from engine.domain import Leg, OptionType, Position, Proposal, Side


@dataclass(frozen=True)
class RiskLimits:
    max_premium_at_risk_per_trade: float
    max_open_positions: int
    max_positions_per_underlying: int
    max_positions_per_sector: int
    monthly_loss_stop_inr: float
    block_reentry_after_loss_same_series: bool = True
    block_averaging_down: bool = True
    strangle_balance_min_ratio: float = 0.40
    defined_risk_only: bool = True
    risk_per_trade_pct: float = 2.5

    def max_loss_allowed(self, capital: float) -> float:
        """Per-trade max loss: % of current capital, capped by the absolute limit."""
        return min(self.max_premium_at_risk_per_trade, capital * self.risk_per_trade_pct / 100)

    @classmethod
    def from_config(cls, cfg: dict[str, object]) -> RiskLimits:
        fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in cfg.items() if k in fields})  # type: ignore[arg-type]


@dataclass(frozen=True)
class Violation:
    rule: str
    detail: str


def _premium_paid(legs: list[Leg]) -> float:
    return sum(leg.price * leg.quantity for leg in legs if leg.side == Side.BUY)


def check_proposal(
    p: Proposal,
    open_positions: list[Position],
    closed_positions: list[Position],
    month_realized_pnl: float,
    limits: RiskLimits,
    capital: float | None = None,
) -> list[Violation]:
    """Return all violations; an empty list means the proposal may go to the approval queue."""
    v: list[Violation] = []

    if month_realized_pnl <= -limits.monthly_loss_stop_inr:
        v.append(Violation("monthly_halt", f"month P&L {month_realized_pnl:.0f} hit stop"))

    cap = (
        limits.max_loss_allowed(capital)
        if capital is not None
        else limits.max_premium_at_risk_per_trade
    )
    if p.max_loss > cap:
        v.append(Violation("size_cap", f"max loss {p.max_loss:.0f} > cap {cap:.0f}"))

    if len(open_positions) >= limits.max_open_positions:
        v.append(Violation("max_open_positions", f"{len(open_positions)} already open"))

    same_und = [x for x in open_positions if x.underlying == p.underlying]
    if len(same_und) >= limits.max_positions_per_underlying:
        rule = "averaging_down" if limits.block_averaging_down else "per_underlying_cap"
        v.append(Violation(rule, f"already holding {p.underlying}"))

    if p.sector:
        same_sector = [x for x in open_positions if x.sector == p.sector]
        if len(same_sector) >= limits.max_positions_per_sector:
            v.append(Violation("sector_cap", f"{len(same_sector)} open in {p.sector}"))

    if limits.block_reentry_after_loss_same_series:
        for c in closed_positions:
            if c.underlying == p.underlying and c.expiry == p.expiry and (c.realized_pnl or 0) < 0:
                v.append(Violation("reentry_after_loss", f"lost on {c.underlying} {c.expiry}"))
                break

    if limits.defined_risk_only:
        sold = [leg for leg in p.legs if leg.side == Side.SELL]
        bought = [leg for leg in p.legs if leg.side == Side.BUY]
        for s in sold:
            hedged = any(
                b.option_type == s.option_type and b.quantity >= s.quantity for b in bought
            )
            if not hedged:
                v.append(Violation("naked_short", f"unhedged short {s.strike}{s.option_type}"))

    if p.strategy in {"long_strangle", "long_straddle"}:
        ce = _premium_paid([leg for leg in p.legs if leg.option_type == OptionType.CE])
        tot = _premium_paid(p.legs)
        if tot > 0:
            share = ce / tot
            lo = limits.strangle_balance_min_ratio
            if not lo <= share <= 1 - lo:
                v.append(Violation("unbalanced_strangle", f"CE share {share:.0%}"))

    return v


def lots_for(max_loss_per_lot: float, capital: float, limits: RiskLimits) -> int:
    """Number of lots that fit the per-trade risk budget (0 = trade does not fit; skip it)."""
    if max_loss_per_lot <= 0:
        return 0
    return int(limits.max_loss_allowed(capital) // max_loss_per_lot)


def safety_exits(
    positions: list[Position], spot: dict[str, float], today: date, warning_days: int = 2
) -> list[Violation]:
    """Flag stock options that are ITM close to expiry (physical settlement risk)."""
    out: list[Violation] = []
    for pos in positions:
        if not pos.is_open or pos.underlying not in spot:
            continue
        if (pos.expiry - today).days > warning_days:
            continue
        s = spot[pos.underlying]
        for leg in pos.legs:
            itm = (s > leg.strike) if leg.option_type == OptionType.CE else (s < leg.strike)
            if itm:
                out.append(
                    Violation(
                        "physical_settlement",
                        f"{pos.underlying} {leg.strike}{leg.option_type} ITM, expiry {pos.expiry}",
                    )
                )
    return out
