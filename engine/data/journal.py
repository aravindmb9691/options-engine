"""Import Zerodha Console F&O P&L exports (xlsx) and group legs into positions.

Usage: python -m engine.data.journal data/journal/*.xlsx
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

SYMBOL_RE = re.compile(r"^([A-Z&\-]+?)(\d{2})([A-Z]{3})([\d.]+)(CE|PE)$")
COLS = {
    "Symbol": "symbol", "Quantity": "qty", "Buy Value": "buy_value",
    "Sell Value": "sell_value", "Realized P&L": "realized_pnl",
    "Open Quantity": "open_qty", "Open Value": "open_value", "Unrealized P&L": "unrealized_pnl",
}


def read_pnl_xlsx(path: str | Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="F&O", header=None)
    hdr = raw.index[raw.apply(lambda r: "Symbol" in r.values and "ISIN" in r.values, axis=1)]
    if len(hdr) == 0:
        raise ValueError(f"{path}: trade table header not found")
    df = pd.read_excel(path, sheet_name="F&O", header=int(hdr[0]))
    df = df.rename(columns=COLS)[list(COLS.values())]
    df = df[df["symbol"].astype(str).str.match(SYMBOL_RE)].copy()
    parts = df["symbol"].str.extract(SYMBOL_RE)
    df["underlying"] = parts[0]
    df["expiry"] = pd.to_datetime("01" + parts[2] + parts[1], format="%d%b%y").dt.to_period("M")
    df["strike"] = parts[3].astype(float)
    df["option_type"] = parts[4]
    num = ["buy_value", "sell_value", "realized_pnl", "open_value", "unrealized_pnl"]
    df[num] = df[num].fillna(0).astype(float)
    df["cost"] = df["buy_value"] + df["open_value"]
    df["pnl"] = df["realized_pnl"] + df["unrealized_pnl"]
    df["source"] = Path(path).name
    return df


def to_positions(legs: pd.DataFrame) -> pd.DataFrame:
    g = legs.groupby(["underlying", "expiry"]).agg(
        types=("option_type", lambda s: "+".join(sorted(set(s)))),
        legs=("option_type", "size"),
        cost=("cost", "sum"),
        ce_cost=("cost", lambda s: s[legs.loc[s.index, "option_type"] == "CE"].sum()),
        pnl=("pnl", "sum"),
    ).reset_index()
    g["kind"] = g["types"].map({"CE+PE": "strangle", "CE": "long_call", "PE": "long_put"})
    g["ce_share"] = (g["ce_cost"] / g["cost"]).round(2)
    g["ret_pct"] = (g["pnl"] / g["cost"] * 100).round(1)
    return g.sort_values("expiry")


def summary(pos: pd.DataFrame) -> dict[str, float]:
    return {
        "positions": len(pos),
        "win_rate": round(float((pos["pnl"] > 0).mean()), 2),
        "total_cost": round(float(pos["cost"].sum())),
        "total_pnl": round(float(pos["pnl"].sum())),
        "avg_cost": round(float(pos["cost"].mean())),
        "top_underlying_cost_share": round(
            float(pos.groupby("underlying")["cost"].sum().max() / pos["cost"].sum()), 2),
    }


if __name__ == "__main__":
    files = sys.argv[1:] or [str(p) for p in Path("data/journal").glob("*.xlsx")]
    legs = pd.concat([read_pnl_xlsx(f) for f in files], ignore_index=True)
    pos = to_positions(legs)
    pd.set_option("display.width", 160)
    print(pos.to_string(index=False))
    print(summary(pos))
