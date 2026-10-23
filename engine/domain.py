"""Core domain objects shared by strategies, risk, backtest and execution."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class OptionType(StrEnum):
    CE = "CE"
    PE = "PE"


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class Leg(BaseModel):
    underlying: str
    expiry: date
    strike: float
    option_type: OptionType
    side: Side
    lots: int = Field(gt=0)
    lot_size: int = Field(gt=0)
    price: float = Field(ge=0)

    @property
    def quantity(self) -> int:
        return self.lots * self.lot_size

    @property
    def premium(self) -> float:
        """Signed cash flow: negative = paid."""
        sign = -1 if self.side == Side.BUY else 1
        return sign * self.price * self.quantity


class Position(BaseModel):
    underlying: str
    expiry: date
    strategy: str
    legs: list[Leg]
    sector: str | None = None
    opened_on: date
    closed_on: date | None = None
    realized_pnl: float | None = None

    @property
    def is_open(self) -> bool:
        return self.closed_on is None


class Proposal(BaseModel):
    id: str
    strategy: str
    underlying: str
    expiry: date
    legs: list[Leg]
    max_loss: float
    sector: str | None = None
    rationale: str = ""
    citations: list[str] = []
    approved: bool = False
