"""Broker interface. PaperBroker is the default; KiteBroker comes in milestone M6."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol

from engine.domain import Leg, Proposal


class Broker(Protocol):
    def place(self, proposal: Proposal) -> str: ...


class LiveTradingNotAllowed(RuntimeError):
    pass


def assert_can_trade(proposal: Proposal) -> None:
    if not proposal.approved:
        raise LiveTradingNotAllowed(f"proposal {proposal.id} not approved")


@dataclass
class PaperBroker:
    slippage_pct: float = 1.0
    fills: list[tuple[str, Leg, float]] = field(default_factory=list)

    def place(self, proposal: Proposal) -> str:
        assert_can_trade(proposal)
        for leg in proposal.legs:
            px = leg.price * (1 + self.slippage_pct / 100)
            self.fills.append((proposal.id, leg, px))
        return f"paper-{proposal.id}"


def get_broker() -> Broker:
    mode = os.getenv("TRADING_MODE", "paper")
    if mode != "live":
        return PaperBroker()
    raise NotImplementedError("KiteBroker arrives in milestone M6")
