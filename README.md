# options-engine

Personal multi-strategy options research & trading engine for NSE F&O (Zerodha Kite Connect).
Web app + Telegram on mobile, hosted on AWS Lightsail (Mumbai) for ≤ ₹3,000/month.

- Design: [`docs/SPEC.md`](docs/SPEC.md)
- Build order + Claude Code prompts: [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md)
- Rules for Claude Code: [`CLAUDE.md`](CLAUDE.md)
- My trading rules: [`kb/playbook.md`](kb/playbook.md)

## Quick start
```bash
uv sync --all-extras          # creates .venv with Python 3.12
uv run pytest -q              # risk rules + journal tests
uv run python -m engine.data.journal data/journal/*.xlsx   # summarize my Zerodha P&L
uv run streamlit run app/Home.py
```

Copy `.env.example` to `.env` and fill in keys (never commit `.env`).

**Trading mode defaults to `paper`.** Live orders require `TRADING_MODE=live` *and* an approved proposal.
