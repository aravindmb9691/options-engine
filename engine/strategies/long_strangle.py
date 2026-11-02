"""Balanced long strangle before a catalyst — the setup that worked in FY26."""

from __future__ import annotations

from dataclasses import dataclass

from engine.domain import Leg, OptionType, Side
from engine.strategies.base import ChainRow, ExitRules, MarketContext


@dataclass
class LongStrangle:
    name: str = "long_strangle"
    min_edge_ratio: float = 1.2
    max_ivp: float = 40.0
    otm_pct: float = 0.04  # strikes ~4% OTM each side
    entry_days_before_event: int = 3

    def eligible(self, ctx: MarketContext) -> bool:
        if ctx.next_event is None or ctx.next_event > ctx.expiry:
            return False
        if (ctx.next_event - ctx.asof).days > self.entry_days_before_event + 2:
            return False
        if ctx.iv_percentile is not None and ctx.iv_percentile > self.max_ivp:
            return False
        edge = ctx.edge_ratio
        return edge is not None and edge >= self.min_edge_ratio

    def _nearest(self, rows: list[ChainRow], target: float, t: OptionType) -> ChainRow:
        cands = [r for r in rows if r.option_type == t and r.ltp > 0]
        if not cands:
            raise ValueError(f"no {t} quotes in chain")
        return min(cands, key=lambda r: abs(r.strike - target))

    def build(self, ctx: MarketContext) -> list[Leg]:
        ce = self._nearest(ctx.chain, ctx.spot * (1 + self.otm_pct), OptionType.CE)
        pe = self._nearest(ctx.chain, ctx.spot * (1 - self.otm_pct), OptionType.PE)
        return [
            Leg(
                underlying=ctx.underlying,
                expiry=ctx.expiry,
                strike=r.strike,
                option_type=r.option_type,
                side=Side.BUY,
                lots=1,
                lot_size=ctx.lot_size,
                price=r.ltp,
            )
            for r in (ce, pe)
        ]

    def max_loss(self, legs: list[Leg]) -> float:
        return -sum(leg.premium for leg in legs)

    def exit_rules(self) -> ExitRules:
        return ExitRules(
            profit_target_pct=60,
            stop_loss_pct=50,
            exit_before_event=True,
            hold_through_if_edge_ratio_gte=1.2,
            exit_days_before_expiry=2,
        )
