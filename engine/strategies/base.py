"""Strategy interface. Every strategy (strangle, spreads, condor, calendar...) implements this."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from engine.domain import Leg, OptionType


@dataclass(frozen=True)
class ChainRow:
    strike: float
    option_type: OptionType
    ltp: float
    iv: float | None = None
    oi: int = 0
    bid: float | None = None
    ask: float | None = None


@dataclass
class MarketContext:
    """Point-in-time view of one underlying. Must contain only data known at `asof`."""

    asof: date
    underlying: str
    spot: float
    expiry: date
    lot_size: int
    chain: list[ChainRow]
    atm_iv: float | None = None
    iv_percentile: float | None = None  # 0-100
    forecast_rv: float | None = None  # annualised, from models.vol_forecast
    implied_move_pct: float | None = None  # ATM straddle / spot
    hist_event_move_pct: float | None = None  # median |move| around past events
    next_event: date | None = None
    regime: str = "normal"  # normal | high_vol | shock
    direction_score: float | None = None  # -1..1, only if direction model enabled
    extra: dict[str, float] = field(default_factory=dict)

    @property
    def edge_ratio(self) -> float | None:
        if self.implied_move_pct and self.hist_event_move_pct:
            return self.hist_event_move_pct / self.implied_move_pct
        return None


@dataclass(frozen=True)
class ExitRules:
    profit_target_pct: float | None = None
    stop_loss_pct: float | None = None
    exit_days_after_event: int | None = None
    exit_before_event: bool = False
    hold_through_if_edge_ratio_gte: float | None = None
    exit_days_before_expiry: int = 2


class Strategy(Protocol):
    name: str

    def eligible(self, ctx: MarketContext) -> bool:
        """Regime / vol / event preconditions."""
        ...

    def build(self, ctx: MarketContext) -> list[Leg]:
        """Construct legs (1 lot each; the risk engine sets final size)."""
        ...

    def max_loss(self, legs: list[Leg]) -> float:
        """Positive number, finite for every v1 strategy."""
        ...

    def exit_rules(self) -> ExitRules: ...
