"""Promotion gate: a strategy goes live only if its out-of-sample trades show a real edge.

Win rate alone is not enough: a 60% win rate loses money if avg win < 0.67 x avg loss.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TradeStats:
    n: int
    win_rate: float
    avg_win: float
    avg_loss: float  # positive number
    payoff_ratio: float  # avg_win / avg_loss
    breakeven_payoff: float  # (1 - p) / p
    expectancy: float  # avg P&L per trade, after costs
    expectancy_r: float  # expectancy / avg risk per trade
    profit_factor: float
    max_drawdown_pct: float
    top3_profit_share: float


def trade_stats(pnl: list[float], risk: list[float], capital: float) -> TradeStats:
    """pnl: per-trade P&L after costs; risk: per-trade max loss at entry (positive)."""
    x = np.asarray(pnl, dtype=float)
    r = np.asarray(risk, dtype=float)
    if len(x) == 0:
        raise ValueError("no trades")
    wins, losses = x[x > 0], -x[x <= 0]
    p = len(wins) / len(x)
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0
    equity = capital + np.cumsum(x)
    peak = np.maximum.accumulate(np.concatenate([[capital], equity]))[1:]
    gross_win = float(wins.sum())
    return TradeStats(
        n=len(x),
        win_rate=p,
        avg_win=avg_win,
        avg_loss=avg_loss,
        payoff_ratio=avg_win / avg_loss if avg_loss else float("inf"),
        breakeven_payoff=(1 - p) / p if p else float("inf"),
        expectancy=float(x.mean()),
        expectancy_r=float(x.mean() / r.mean()) if r.mean() else 0.0,
        profit_factor=gross_win / float(losses.sum()) if losses.sum() else float("inf"),
        max_drawdown_pct=float(((peak - equity) / peak).max() * 100),
        top3_profit_share=float(np.sort(wins)[-3:].sum() / gross_win) if gross_win else 1.0,
    )


def passes_gate(s: TradeStats, gate: dict[str, float]) -> tuple[bool, list[str]]:
    fails: list[str] = []
    if s.n < gate["min_oos_trades"]:
        fails.append(f"only {s.n} trades")
    if s.expectancy_r < gate["min_expectancy_r"]:
        fails.append(f"expectancy {s.expectancy_r:.2f}R")
    if s.payoff_ratio < s.breakeven_payoff + gate["min_payoff_ratio_margin"]:
        fails.append(f"payoff {s.payoff_ratio:.2f} vs breakeven {s.breakeven_payoff:.2f}")
    if s.max_drawdown_pct > gate["max_drawdown_pct"]:
        fails.append(f"drawdown {s.max_drawdown_pct:.0f}%")
    if s.top3_profit_share > gate["max_top3_profit_share"]:
        fails.append(f"top-3 trades = {s.top3_profit_share:.0%} of profit")
    if s.profit_factor < gate["min_profit_factor"]:
        fails.append(f"profit factor {s.profit_factor:.2f}")
    return (not fails, fails)
