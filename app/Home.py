"""Streamlit v0 — journal dashboard. Run: uv run streamlit run app/Home.py"""

from pathlib import Path

import pandas as pd
import streamlit as st

from engine.data.journal import read_pnl_xlsx, summary, to_positions

st.set_page_config(page_title="Options Engine", layout="wide")
st.title("Options Engine")

files = sorted(Path("data/journal").glob("*.xlsx"))
if not files:
    st.info("Put Zerodha P&L exports in data/journal/")
    st.stop()

legs = pd.concat([read_pnl_xlsx(f) for f in files], ignore_index=True)
pos = to_positions(legs)
s = summary(pos)
c = st.columns(4)
c[0].metric("Positions", s["positions"])
c[1].metric("Win rate", f"{s['win_rate']:.0%}")
c[2].metric("Net P&L", f"₹{s['total_pnl']:,}")
c[3].metric("Avg premium", f"₹{s['avg_cost']:,}")
st.subheader("By underlying")
st.bar_chart(pos.groupby("underlying")["pnl"].sum().sort_values())
st.subheader("Positions")
st.dataframe(pos.assign(expiry=pos["expiry"].astype(str)), use_container_width=True)
