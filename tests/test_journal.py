from pathlib import Path

import pytest

from engine.data.journal import read_pnl_xlsx, summary, to_positions

FILES = sorted(Path("data/journal").glob("*.xlsx"))


@pytest.mark.skipif(not FILES, reason="no P&L exports in data/journal")
def test_journal_parses():
    import pandas as pd

    legs = pd.concat([read_pnl_xlsx(f) for f in FILES], ignore_index=True)
    pos = to_positions(legs)
    s = summary(pos)
    assert s["positions"] > 0
    assert set(pos["kind"].dropna()) <= {"strangle", "long_call", "long_put"}
