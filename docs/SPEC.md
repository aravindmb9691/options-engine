# Options Engine — Spec (v0.1)

## 1. Goal
Daily, evidence-based option trade *proposals* across multiple strategies, with a hard risk layer, backtested on NSE data, approved by me from phone. Success = positive expectancy after all costs with controlled drawdown — **not** a high win rate.

Lessons from my own P&L (FY26 +₹88k, FY27 −₹168k) that the system must encode:
- Edge existed in small, balanced long-vol trades before catalysts (FY26 strangles 70% win).
- Losses came from 2–3× sizing, concentration (one stock = 52% of capital), call-heavy "strangles" in a falling market, and re-entering losers.
- Calls bought over two years: −₹167k; puts: +₹87k → discretionary direction calls have had no edge.

## 2. Architecture
```
Scheduler → Ingest → Postgres/S3 → Features → Models → Selector → Strategies → Risk → Proposals
                                                                                     ↓
                     Agent (news/events/explain) ──────────────────────→ Brief + Approval (Telegram/PWA)
                                                                                     ↓
                                                        Paper broker  |  Kite broker (static IP, daily 2FA)
```

## 3. Data
| Domain | Source | Freq |
|---|---|---|
| Option/futures EOD (backtest) | NSE F&O bhavcopy archives | daily, backfill 2018+ |
| Live chain, quotes, positions, orders | Kite Connect (₹500/mo plan) | live / 5-min |
| Events | NSE corporate announcements, board meetings (results), dividends | daily |
| Risk flags | NSE F&O ban list, India VIX | daily |
| Flows | FII/DII cash & F&O, participant-wise OI | daily |
| Macro | Brent, USD/INR, metals, US 10Y, Nasdaq (yfinance/FRED) | daily |
| News | RSS (ET, BS, Moneycontrol, Reuters), NSE filings, GDELT | 15-min |

## 4. Strategy library (not just strangles)
Every strategy implements one interface so the backtester, risk engine and UI treat them identically.

```python
class Strategy(Protocol):
    name: str
    def eligible(self, ctx: MarketContext) -> bool: ...            # regime/vol/event preconditions
    def build(self, ctx: MarketContext, chain: OptionChain) -> list[Leg]: ...
    def max_loss(self, legs: list[Leg]) -> float: ...               # must be finite for v1
    def exit_rules(self) -> ExitRules: ...                          # target, stop, time stop, pre-expiry
```

| View | IV cheap (low IVP / RV>IV) | IV rich (high IVP / IV>RV) |
|---|---|---|
| Big move, no direction (event) | Long strangle / straddle | Long iron fly / skip |
| Directional (model-backed only) | Debit spread (bull call / bear put) | Credit spread (bull put / bear call) |
| Range-bound | Calendar | Iron condor (defined risk) |
| Term-structure dislocation | Calendar / diagonal | Calendar / diagonal |
| Nothing clear | **No trade** | **No trade** |

v1 rule: **defined-risk only** (no naked short options). Naked directional buying allowed only at half size with a model signal attached.

## 5. Models
1. **Vol forecast** — HAR-RV per underlying (GARCH benchmark) → forecast RV to expiry; `edge_vol = forecast_RV / ATM_IV`.
2. **Event move** — empirical distribution of |move| around past results; LightGBM `P(|realized| > implied)`; features: IVP, past moves, sector, VIX, crude Δ, sentiment, OI Δ.
3. **Regime** — rules first (VIX level & slope, Nifty vs 50DMA, crude shock flag), HMM later. Gates which strategy rows are allowed.
4. **Direction** — weak, optional (LightGBM on flows/trend/sector/macro); only feeds debit/credit spreads; must beat a naive baseline out-of-sample to be enabled.
5. **Sentiment** — LLM structured tags per headline `{ticker, event_type, direction, severity, novelty}` → daily aggregates; enabled only if it adds OOS lift.
6. **Pricing** — py_vollib for IV, greeks, scenario P&L.

## 6. Risk engine (pure code, config in `risk.yaml`)
- Max premium-at-risk per trade, max open positions, max per underlying = 1, max per sector.
- Monthly loss stop → auto-halt new entries.
- No averaging / no same-series re-entry after loss.
- Balanced long strangles (CE:PE premium within 40:60).
- Safety exits: stop/target/time stop, ITM stock option ≤2 days to expiry, ban-list entry, event passed.
- Portfolio greeks limits (net delta, vega) once multiple strategies run.

## 7. Backtesting
- Daily event-driven simulator on reconstructed chains from bhavcopy.
- Fills: close ± slippage proxy scaled by moneyness/liquidity (no bid/ask in bhavcopy); reject strikes with low OI.
- Costs: brokerage, STT, exchange, SEBI, GST, stamp — from `market.yaml`, versioned by date.
- Walk-forward (train 5y → test 1y, roll); no look-ahead; announcement-date keyed events.
- Reports per strategy: expectancy, profit factor, max DD, worst month, top-3-trade share, trade count, Monte Carlo of trade order.
- Replay my 39 real trades as a sanity check.
- Promotion gate: ≥100 OOS trades positive after costs → 3 months paper → live at half size.
- Capital allocation across strategies by OOS performance (start equal-risk; cap any one at 40%).

## 8. Agent
Tools: `screen()`, `option_chain(sym)`, `positions()`, `events(sym)`, `news(sym)`, `backtest_stats(strategy, sym)`, `propose_trade(...)` (writes a proposal only).

| Decision | Owner |
|---|---|
| Scan, research, news triage, brief (8:45 & 15:45) | Agent (auto) |
| Propose trade | Agent → risk sizes → **I approve** |
| Size / limits | Risk engine only |
| Safety exits | Auto-propose; auto-execute only when I enable |
| Discretionary close | Agent recommends, I approve |
| Averaging / re-entry after loss | Blocked |

## 9. Zerodha
Kite Connect app; static IP = OCI reserved public IP; daily 2FA login via link sent on Telegram at 08:45 (no automated TOTP). Positions synced every 5 min. Kite MCP for ad-hoc chat in Claude.

## 10. Hosting & cost
Oracle Cloud Always Free (pay-as-you-go account): VM.Standard.A1.Flex 4 OCPU / 24 GB Arm, Mumbai or Hyderabad, reserved public IP, docker-compose (api, worker, postgres, bot), nightly pg_dump to OCI Object Storage. Hosting ₹0 if within free limits; Kite ₹500; LLM ₹500–1,200 (hard cap in llm.yaml). Budget < ₹2,000/month, OCI budget alert at ₹200.

## 11. Domain & access
- Domain registered and DNS on Cloudflare (free DNS).
- `www.<domain>` — **public** portfolio site (Cloudflare Pages, free): architecture, methodology, blog, anonymised backtest reports. No live positions, no account P&L, no trade calls (publishing recommendations can require SEBI Research Analyst registration).
- `app.<domain>` — **private** trading app via Cloudflare Tunnel (no inbound ports open on OCI) protected by Cloudflare Access (Zero Trust free plan, email OTP for my address only).
- Kite redirect URL: `https://app.<domain>/kite/callback`.
- SSH only via Tailscale or my IP; security list opens nothing else.
