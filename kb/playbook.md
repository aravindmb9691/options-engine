# My Playbook (v0.1)

The agent quotes this first. I change it only through git, after a weekly review.

## 1. Sizing
- Max loss per trade: 2.5% of current capital, never above ₹20k (see `config/risk.yaml`). If one lot does not fit, skip the trade or use a spread — never round up. At most 3 open positions, 1 per stock, 2 per sector.
- Monthly loss stop: −₹25k, then no new entries until next month.

## 2. Never
- Average down a losing options position.
- Re-enter the same stock in the same series after a loss.
- Call something a "strangle" when one side is >60% of the premium. That is a directional bet.
- Hold an in-the-money stock option into expiry (physical settlement).
- Trade to "win back" a loss.

## 3. Long volatility before events (my FY26 edge)
- Enter T-3 to T-2 before results or a known catalyst; **exit on the last close before the announcement** (research: pre-event IV rise pays, holding through usually loses to IV crush). Hold through only if this stock's edge ratio ≥ 1.2. Never hold to expiry.
- Only when the historical event move / implied move is ≥ 1.2 and IV percentile ≤ 40.
- Balanced strikes, ~4% OTM each side, liquid strikes only.

## 4. When options are expensive (high IVP / VIX rising)
- Prefer defined-risk credit structures (credit spreads, iron condors) or no trade.
- No naked short options in v1.

## 5. Directional trades
- Only with a model signal that beats a naive baseline out-of-sample. Use debit/credit spreads, half size.
- My history: calls bought −₹167k, puts +₹87k over FY26–FY27. Don't trust gut direction.

## 6. Evidence
- Signal evidence and what NOT to trade: `kb/research/strategy_evidence.md`.

## 7. Regime
- Oil/geopolitical shock, VIX > 18 and rising, FII heavy selling → cut size by half, defined risk only.
