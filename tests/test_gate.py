from engine.backtest.gate import passes_gate, trade_stats
from engine.config import load

GATE = load("strategies")["promotion_gate"]


def test_high_win_rate_negative_payoff_fails():
    # 75% winners of +300, 25% losers of -1000 (typical naive credit spread)
    pnl = ([300.0] * 3 + [-1000.0]) * 30
    s = trade_stats(pnl, [1000.0] * len(pnl), capital=300_000)
    assert s.win_rate == 0.75 and s.expectancy < 0
    ok, fails = passes_gate(s, GATE)
    assert not ok and any("payoff" in f for f in fails)


def test_sixty_pct_with_good_payoff_passes():
    pnl = ([1200.0] * 3 + [-1000.0] * 2) * 24
    s = trade_stats(pnl, [1000.0] * len(pnl), capital=300_000)
    ok, fails = passes_gate(s, GATE)
    assert ok, fails
    assert round(s.breakeven_payoff, 2) == 0.67
