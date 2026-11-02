# Build Plan — milestones + prompts for Claude Code

How to use: one milestone per branch. Open Claude Code in the repo, switch to **plan mode** (Shift+Tab), paste the prompt, review the plan, then let it build. End each milestone with tests green and a PR.

---

## M0 · Repo bootstrap (½ day) — scaffold already created
Already in place: layout, pyproject, configs, domain models, Strategy protocol, LongStrangle, risk rules + tests, PaperBroker, journal importer, Streamlit v0, CI, pre-commit.
Branch: `m0-bootstrap` — remaining: verify `TODO(verify)` values, `pre-commit install`, push to GitHub.
> Read CLAUDE.md and docs/SPEC.md. Scaffold the repo layout from CLAUDE.md with uv, ruff, mypy, pytest, pre-commit (ruff, a secret scanner, block committing `.env`). Add `config/market.yaml` with placeholders marked `TODO(verify)` for lot sizes, expiry rules, STT and charges, and `config/risk.yaml` with my limits. Add GitHub Actions running lint + tests. No business logic yet.

## M1 · Data pipeline (1–2 weeks)
Branch: `m1-data`
> Implement `engine/data/nse_bhavcopy.py`: download NSE F&O bhavcopy archives (both old and new formats), parse to a normalized options table (date, symbol, expiry, strike, type, OHLC, close, settle, OI, volume, underlying close), store as partitioned Parquet + Postgres. Idempotent, resumable, polite rate limiting, retries. Then add India VIX history, F&O ban list, and NSE board-meeting/results announcements keyed by announcement date. Validate every table with pandera schemas. Tests with small fixtures. Typer CLI: `--from --to`.

> Add `engine/data/macro.py` (Brent, USDINR, aluminium/copper, US10Y, Nasdaq via yfinance/FRED) and `engine/data/journal.py` that imports my Zerodha P&L xlsx files from `data/journal/` into a trades table.

## M2 · Backtester + costs (2 weeks)
Branch: `m2-backtest`
> Build `engine/backtest/`: daily event-driven simulator over reconstructed chains, `costs.py` driven by market.yaml (date-versioned), `fills.py` with a slippage model by moneyness and OI, liquidity filter, walk-forward runner, and a report (expectancy, profit factor, max DD, worst month, top-3-trade share, Monte Carlo). Log every run to MLflow (local SQLite): params, git SHA, data range, gate metrics, report as artifact. Implement `strategies/base.py` (Protocol from SPEC §4) and `long_strangle.py` first. Write a test that replays my journal trades and compares simulated vs actual P&L.

## M3 · More strategies (1–2 weeks)
Branch: `m3-strategies`
> Add debit_spread, credit_spread, iron_condor, iron_fly, calendar, long_straddle — all defined risk, each with eligible/build/max_loss/exit_rules and unit tests on max loss. Add `selector/` implementing the SPEC §4 matrix. Run walk-forward for each on the top 30 liquid F&O names + Nifty and produce a comparison report.

## M4 · Models (2–3 weeks)
Branch: `m4-models`
> Implement HAR-RV and GARCH vol forecasts, event-move model (empirical + LightGBM P(|move|>implied)), rules-based regime model. Strict no-look-ahead feature store with point-in-time joins and a test that fails on leakage. Plug model outputs into selector eligibility; re-run M3 comparison and show lift vs no-model baseline.

## M5 · Risk engine + paper broker (1 week)
Branch: `m5-risk`
> Implement `engine/risk/` per SPEC §6 with mypy --strict and exhaustive tests (averaging block, re-entry block, physical-settlement safety exit, monthly halt, sector/underlying caps). Implement Broker interface, PaperBroker (fills at live mid ± slippage), approval queue in Postgres.

## M6 · Kite integration (1 week)
Branch: `m6-kite`
> Implement KiteBroker using kiteconnect: login URL + callback that stores the daily access token, positions/holdings/orders sync every 5 min, live option chain, order placement only via an approved proposal id and only when TRADING_MODE=live. Secrets from env/OCI Vault. Never log tokens.

## M7 · UI + Telegram (1–2 weeks)
Branch: `m7-ui`
> FastAPI endpoints for screener, proposals, positions, backtest reports. Streamlit app (mobile-friendly) with pages: Today, Screener, Positions, Strategies, Journal. Telegram bot: morning login link, brief, proposal cards with Approve/Reject buttons, safety-exit alerts, /halt kill switch.

## M8 · Agent (1–2 weeks)
Branch: `m8-agent`
> Build `engine/agent/` with the tools from SPEC §8 using the Anthropic SDK (model names from llm.yaml). News tagger (cheap model, structured JSON). Daily brief + position review (stronger model) that cites data and backtest stats. `propose_trade` only writes to the proposal queue; risk engine sizes. Add an eval set of 30 past days to score brief quality and check it never bypasses risk.

## M8b · Knowledge base / RAG (1 week)
Branch: `m8b-rag`
> Add `engine/kb/`: ingest PDFs/HTML/Markdown from `kb/sources/` (gitignored for licensed books), chunk by section (~800 tokens, 100 overlap), tag each chunk with metadata {source, type: book|paper|regulation|playbook|postmortem, strategies[], regime[], effective_date}. Store embeddings in pgvector in the existing Postgres. Hybrid search (BM25 + vector) with metadata filters, plus a reranker. Expose agent tool `kb_search(query, strategy=None, type=None)` returning chunks with citations. Regulations: always return the latest effective_date. Add `kb/playbook.md` (my distilled rules) and auto-generate a post-mortem note for every closed trade into the KB. Eval: 30 questions with expected source; report hit@5.

## M9 · Deploy (2–3 days)
Branch: `m9-deploy`
> docker-compose (api, worker, postgres, bot) for linux/arm64, OCI cloud-init bootstrap (Ubuntu 24.04 on VM.Standard.A1.Flex, 4 OCPU / 24 GB), reserved public IP, VCN security list with no public inbound ports except SSH from my IP, Cloudflare Tunnel (cloudflared container) for app.<domain> behind Cloudflare Access, public portfolio site on Cloudflare Pages (`site/` folder, static), 4 GB swap, Postgres memory limits, nightly pg_dump to OCI Object Storage (keep 14 days, stay < 20 GB), health check + Telegram alert on job failure, OCI budget alert. Because the box has 24 GB RAM, backfills and backtests may run here overnight too.

## Then
3 months paper trading → live at half size with approvals → enable auto safety exits only.

---

## Claude Code tips
- Put this repo's `CLAUDE.md` at the root; Claude reads it every session.
- Add Zerodha's Kite MCP for read-only portfolio questions: `claude mcp add --transport sse kite https://mcp.kite.trade/sse`
- Use a fresh session per milestone; ask for a plan first; ask it to "write tests first" for risk and costs.
- After each milestone: "review this branch for look-ahead bias, unhandled market-rule assumptions, and secrets" (or use a review subagent).
- Keep my account exports out of git (`data/journal/` in .gitignore).
