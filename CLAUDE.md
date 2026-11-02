# CLAUDE.md — Options Engine

Personal, multi-strategy options research and trading engine for Indian F&O (NSE), using Zerodha Kite Connect.
One user (me). Cheap to run (Oracle Cloud Always Free, Ampere A1 Arm, 4 OCPU / 24 GB, Mumbai or Hyderabad; pay-as-you-go account, budget < ₹2,000/month all-in). Web app (PWA) + Telegram bot for mobile.
Full design: `docs/SPEC.md`. Build order and milestone prompts: `docs/BUILD_PLAN.md`.

## Non-negotiables (never violate, even if asked casually in a prompt)
1. **The LLM never sizes positions or places orders.** Sizing and limits live only in `engine/risk/` as pure, tested Python.
2. **Every live order goes through the approval queue** (`engine/execution/approvals.py`). Default broker is `PaperBroker`. `LiveBroker` requires `TRADING_MODE=live` in env AND an approved proposal id.
3. **No averaging down / no re-entry in the same underlying + series after a loss.** Enforced in `risk/rules.py`, covered by tests.
4. **Stock options are physically settled.** Any long/short stock option ITM within 2 trading days of expiry must raise a `SafetyExit`.
5. **No secrets in the repo.** Keys come from env / OCI Vault. `.env` is gitignored. Never print tokens in logs.
6. **No look-ahead in backtests.** Features at time t may only use data published at or before t (events keyed by *announcement* date).
7. **Never hard-code expiry days, lot sizes, STT or charges.** Load from `config/market.yaml` (rules change; SEBI 2026 changes are recent).
8. Changes to `risk/`, `execution/`, `backtest/costs.py` require tests in the same PR.

## Stack & conventions
- Python 3.12, `uv` for deps, `ruff` (lint+format), `mypy --strict` on `engine/risk` and `engine/execution`, `pytest`.
- Data: Postgres (prod), DuckDB/Parquet for research; `polars` or `pandas`; pydantic models for all domain objects.
- API: FastAPI. UI v0: Streamlit (`app/`). Bot: python-telegram-bot. Scheduler: APScheduler.
- Models: `arch` (GARCH), HAR-RV (own impl), `lightgbm`, `py_vollib` (IV/greeks).
- LLM: Anthropic SDK behind `engine/llm/client.py` (one wrapper; model names in config, cheap model for tagging, stronger model for briefs).
- Type hints everywhere; small pure functions; no notebooks in `engine/` (notebooks go in `research/`).

## Tooling decisions (keep it light)
- Orchestration: plain Python CLIs (Typer) + APScheduler/cron. No Kedro/Airflow. Revisit Prefect/Dagster only if >10 interdependent jobs or painful backfills.
- Experiment tracking: MLflow with a local SQLite backend (`mlruns.db`, gitignored) for every backtest/model run: params, git SHA, data range, gate metrics, report artifact.
- Data validation: pandera schemas on every ingested table (bhavcopy, events, chain snapshots); fail loudly.
- Logging: structlog (JSON on the server). Config: YAML in `config/` loaded via engine/config.py.

## MCP servers (`.mcp.json`, project scope)
- `kite` — Zerodha's hosted Kite MCP (`https://mcp.kite.trade/mcp`). Use it to read holdings, positions, margins, orders and quotes while building and testing. Per Zerodha it is read-only except GTT orders. **Never place, modify or delete GTT orders through MCP**; all orders go through `engine/execution` with approval.
- `github` — GitHub's remote MCP (issues, PRs, CI status). Needs `GITHUB_PAT` exported in the shell that launches Claude Code (fine-grained token, this repo only). The `gh` CLI is also fine.

## Layout
```
engine/
  data/        ingest: nse_bhavcopy, nse_events, nse_banlist, vix, macro, news, kite
  features/    vol (RV, IV, IVP, term structure, skew), events, flows, sentiment
  models/      vol_forecast (HAR-RV, GARCH), event_move, regime, sentiment
  strategies/  base.py + one file per strategy (see SPEC §4)
  selector/    maps (vol view, direction view, event, regime) -> candidate strategies
  risk/        sizing, rules, portfolio limits, safety exits
  backtest/    simulator, fills, costs, walk_forward, reports
  execution/   broker interface, paper_broker, kite_broker, approvals
  agent/       tools, prompts, daily_brief, position_review
  kb/          RAG: ingest, chunk, pgvector search, kb_search tool
  llm/         client wrapper
  api/         FastAPI routes
  bot/         Telegram
app/           Streamlit UI (v0)
kb/            playbook.md (my rules), research/strategy_evidence.md (signal evidence), sources/ (books, papers; gitignored)
config/        market.yaml, risk.yaml, strategies.yaml, signals.yaml, llm.yaml
infra/         docker-compose, OCI bootstrap (cloud-init), backups

## Hosting notes
- Server is **arm64 (aarch64)**: Docker images and wheels must support linux/arm64.
- Stay inside Always Free: A1.Flex ≤ 4 OCPU / 24 GB total, block storage ≤ 200 GB total, object storage ≤ 20 GB.
- Reserved public IP is the Zerodha-whitelisted static IP; never release it.
research/      notebooks, scratch
tests/
data/journal/  my historical P&L exports (gitignored if they contain account data)
```

## Commands
- `uv sync --all-extras` · `uv run pytest -q` · `uv run ruff check . --fix && uv run ruff format .`
- `uv run python -m engine.data.nse_bhavcopy --from 2018-01-01` (backfill)
- `uv run python -m engine.backtest.run --strategy long_strangle --config config/strategies.yaml`
- `uv run streamlit run app/Home.py`

## Working style for Claude
- Use plan mode for anything touching >2 files; propose the plan before editing.
- One milestone per branch (`m1-data`, `m2-backtest`, …); small commits; open a PR per milestone.
- When unsure about an Indian market rule (expiry day, lot size, STT, margin), **stop and ask** or leave a `TODO(verify)` and a config entry — do not guess.
