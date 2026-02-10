import json
import os
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.database import init_db, save_snapshot, get_all_snapshots, get_latest_snapshot
from services.prices import get_stock_prices, get_crypto_prices

HOLDINGS_PATH = os.path.join(os.path.dirname(__file__), "holdings.json")

# --- Page config ---
st.set_page_config(page_title="Net Worth Tracker", page_icon="📈", layout="wide")
init_db()


def load_holdings() -> dict:
    with open(HOLDINGS_PATH, "r") as f:
        return json.load(f)


def save_holdings(holdings: dict):
    with open(HOLDINGS_PATH, "w") as f:
        json.dump(holdings, f, indent=2)


def compute_snapshot(holdings: dict) -> tuple[float, dict]:
    """Fetch all prices, compute total net worth and breakdown."""
    breakdown = {
        "stocks": {},
        "etfs": {},
        "crypto": {},
        "cash": {},
        "category_totals": {},
    }

    # Stock prices
    stock_tickers = [h["ticker"] for h in holdings.get("stocks", [])]
    etf_tickers = [h["ticker"] for h in holdings.get("etfs", [])]
    all_tickers = stock_tickers + etf_tickers
    prices = get_stock_prices(all_tickers) if all_tickers else {}

    stocks_total = 0.0
    for h in holdings.get("stocks", []):
        ticker = h["ticker"]
        price = prices.get(ticker, 0.0)
        value = round(price * h["shares"], 2)
        breakdown["stocks"][ticker] = value
        stocks_total += value

    etfs_total = 0.0
    for h in holdings.get("etfs", []):
        ticker = h["ticker"]
        price = prices.get(ticker, 0.0)
        value = round(price * h["shares"], 2)
        breakdown["etfs"][ticker] = value
        etfs_total += value

    # Crypto prices
    crypto_ids = [h["id"] for h in holdings.get("crypto", [])]
    crypto_prices = get_crypto_prices(crypto_ids) if crypto_ids else {}

    crypto_total = 0.0
    for h in holdings.get("crypto", []):
        price = crypto_prices.get(h["id"], 0.0)
        value = round(price * h["amount"], 2)
        breakdown["crypto"][h["symbol"]] = value
        crypto_total += value

    # Cash (manual entries from config)
    cash_total = 0.0
    for h in holdings.get("cash", []):
        label = h["label"]
        amount = h["amount"]
        breakdown["cash"][label] = amount
        cash_total += amount

    breakdown["category_totals"] = {
        "stocks": round(stocks_total, 2),
        "etfs": round(etfs_total, 2),
        "crypto": round(crypto_total, 2),
        "cash": round(cash_total, 2),
    }

    total = round(stocks_total + etfs_total + crypto_total + cash_total, 2)
    return total, breakdown


# --- Sidebar: Holdings Editor ---
with st.sidebar:
    st.header("Manage Holdings")

    holdings = load_holdings()
    changed = False

    # --- Stocks ---
    with st.expander("Stocks", expanded=False):
        for i, h in enumerate(holdings.get("stocks", [])):
            cols = st.columns([2, 2, 1])
            cols[0].text_input("Ticker", value=h["ticker"], key=f"stock_t_{i}", disabled=True)
            cols[1].number_input("Shares", value=float(h["shares"]), key=f"stock_s_{i}", min_value=0.0, step=1.0, disabled=True)
            if cols[2].button("X", key=f"stock_del_{i}"):
                holdings["stocks"].pop(i)
                changed = True

        st.markdown("**Add stock**")
        c1, c2 = st.columns(2)
        new_stock_ticker = c1.text_input("Ticker", key="new_stock_ticker", placeholder="e.g. AAPL")
        new_stock_shares = c2.number_input("Shares", key="new_stock_shares", min_value=0.0, step=1.0, value=0.0)
        if st.button("Add Stock", key="add_stock"):
            if new_stock_ticker.strip():
                holdings.setdefault("stocks", []).append({
                    "ticker": new_stock_ticker.strip().upper(),
                    "shares": new_stock_shares,
                })
                changed = True

    # --- ETFs ---
    with st.expander("ETFs", expanded=False):
        for i, h in enumerate(holdings.get("etfs", [])):
            cols = st.columns([2, 2, 1])
            cols[0].text_input("Ticker", value=h["ticker"], key=f"etf_t_{i}", disabled=True)
            cols[1].number_input("Shares", value=float(h["shares"]), key=f"etf_s_{i}", min_value=0.0, step=1.0, disabled=True)
            if cols[2].button("X", key=f"etf_del_{i}"):
                holdings["etfs"].pop(i)
                changed = True

        st.markdown("**Add ETF**")
        c1, c2 = st.columns(2)
        new_etf_ticker = c1.text_input("Ticker", key="new_etf_ticker", placeholder="e.g. VOO")
        new_etf_shares = c2.number_input("Shares", key="new_etf_shares", min_value=0.0, step=1.0, value=0.0)
        if st.button("Add ETF", key="add_etf"):
            if new_etf_ticker.strip():
                holdings.setdefault("etfs", []).append({
                    "ticker": new_etf_ticker.strip().upper(),
                    "shares": new_etf_shares,
                })
                changed = True

    # --- Crypto ---
    with st.expander("Crypto", expanded=False):
        for i, h in enumerate(holdings.get("crypto", [])):
            cols = st.columns([2, 2, 1])
            cols[0].text_input("ID", value=h["id"], key=f"crypto_id_{i}", disabled=True)
            cols[1].number_input("Amount", value=float(h["amount"]), key=f"crypto_a_{i}", min_value=0.0, step=0.01, disabled=True)
            if cols[2].button("X", key=f"crypto_del_{i}"):
                holdings["crypto"].pop(i)
                changed = True

        st.markdown("**Add crypto**")
        c1, c2 = st.columns(2)
        new_crypto_id = c1.text_input("CoinGecko ID", key="new_crypto_id", placeholder="e.g. bitcoin")
        new_crypto_symbol = c1.text_input("Symbol", key="new_crypto_symbol", placeholder="e.g. BTC")
        new_crypto_amount = c2.number_input("Amount", key="new_crypto_amount", min_value=0.0, step=0.01, value=0.0)
        if st.button("Add Crypto", key="add_crypto"):
            if new_crypto_id.strip() and new_crypto_symbol.strip():
                holdings.setdefault("crypto", []).append({
                    "id": new_crypto_id.strip().lower(),
                    "symbol": new_crypto_symbol.strip().upper(),
                    "amount": new_crypto_amount,
                })
                changed = True

    # --- Cash ---
    with st.expander("Cash", expanded=False):
        for i, h in enumerate(holdings.get("cash", [])):
            cols = st.columns([2, 2, 1])
            cols[0].text_input("Label", value=h["label"], key=f"cash_l_{i}", disabled=True)
            new_amt = cols[1].number_input("Amount", value=float(h["amount"]), key=f"cash_a_{i}", min_value=0.0, step=100.0)
            if new_amt != h["amount"]:
                holdings["cash"][i]["amount"] = new_amt
                changed = True
            if cols[2].button("X", key=f"cash_del_{i}"):
                holdings["cash"].pop(i)
                changed = True

        st.markdown("**Add cash account**")
        c1, c2 = st.columns(2)
        new_cash_label = c1.text_input("Label", key="new_cash_label", placeholder="e.g. Checking")
        new_cash_amount = c2.number_input("Amount ($)", key="new_cash_amount", min_value=0.0, step=100.0, value=0.0)
        if st.button("Add Cash", key="add_cash"):
            if new_cash_label.strip():
                holdings.setdefault("cash", []).append({
                    "label": new_cash_label.strip(),
                    "amount": new_cash_amount,
                })
                changed = True

    # Save if anything changed
    if changed:
        save_holdings(holdings)
        st.rerun()

# --- Header ---
st.title("📈 Daily Net Worth Tracker")
st.caption(f"Today: {date.today().strftime('%A, %B %d, %Y')}")

# --- Refresh button ---
if st.button("🔄 Refresh Prices", type="primary"):
    with st.spinner("Fetching prices..."):
        holdings = load_holdings()
        total, breakdown = compute_snapshot(holdings)
        save_snapshot(date.today().isoformat(), total, breakdown)
    st.success("Snapshot saved!")

# --- Load latest data ---
latest = get_latest_snapshot()
all_snapshots = get_all_snapshots()

if latest is None:
    st.info("No data yet. Click **Refresh Prices** to fetch your first snapshot.")
    st.stop()

total_value = latest["total_value"]
breakdown = latest["breakdown"]
cat_totals = breakdown.get("category_totals", {})

# --- Compute daily change ---
daily_change = 0.0
daily_pct = 0.0
if len(all_snapshots) >= 2:
    prev = all_snapshots[-2]["total_value"]
    daily_change = total_value - prev
    daily_pct = (daily_change / prev * 100) if prev != 0 else 0.0

# --- Top metrics ---
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.metric(
        label="Net Worth",
        value=f"${total_value:,.2f}",
        delta=f"${daily_change:+,.2f} ({daily_pct:+.2f}%)" if len(all_snapshots) >= 2 else None,
    )
with col2:
    st.metric("Latest Snapshot", latest["date"])
with col3:
    st.metric("Total Snapshots", len(all_snapshots))

# --- Category totals ---
st.subheader("Category Breakdown")
cat_cols = st.columns(4)
categories = [
    ("Stocks", cat_totals.get("stocks", 0)),
    ("ETFs", cat_totals.get("etfs", 0)),
    ("Crypto", cat_totals.get("crypto", 0)),
    ("Cash", cat_totals.get("cash", 0)),
]
for col, (name, val) in zip(cat_cols, categories):
    col.metric(name, f"${val:,.2f}")

# --- Charts ---
st.subheader("Net Worth Over Time")

if len(all_snapshots) >= 2:
    df = pd.DataFrame(all_snapshots)
    df["date"] = pd.to_datetime(df["date"])
    fig_line = px.line(
        df, x="date", y="total_value",
        labels={"date": "Date", "total_value": "Net Worth ($)"},
    )
    fig_line.update_traces(line_color="#0052FF", line_width=3)
    fig_line.update_layout(
        hovermode="x unified",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.0f",
    )
    st.plotly_chart(fig_line, key="line_chart")
else:
    st.info("Need at least 2 snapshots to show a chart. Refresh again tomorrow!")

# --- Allocation pie chart ---
st.subheader("Allocation")

pie_data = {k: v for k, v in cat_totals.items() if v > 0}
if pie_data:
    fig_pie = go.Figure(data=[go.Pie(
        labels=list(pie_data.keys()),
        values=list(pie_data.values()),
        hole=0.4,
        textinfo="label+percent",
        marker=dict(colors=["#0052FF", "#00C49F", "#FF8042", "#00B4D8"]),
    )])
    fig_pie.update_layout(showlegend=True, margin=dict(t=20, b=20))
    st.plotly_chart(fig_pie, key="pie_chart")

# --- Holdings detail tables ---
st.subheader("Holdings Detail")

holdings = load_holdings()

# Stocks
if breakdown.get("stocks"):
    st.markdown("**Stocks**")
    rows = []
    for h in holdings.get("stocks", []):
        ticker = h["ticker"]
        value = breakdown["stocks"].get(ticker, 0)
        price = round(value / h["shares"], 2) if h["shares"] else 0
        rows.append({"Ticker": ticker, "Shares": h["shares"], "Price": f"${price:,.2f}", "Value": f"${value:,.2f}"})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

# ETFs
if breakdown.get("etfs"):
    st.markdown("**ETFs**")
    rows = []
    for h in holdings.get("etfs", []):
        ticker = h["ticker"]
        value = breakdown["etfs"].get(ticker, 0)
        price = round(value / h["shares"], 2) if h["shares"] else 0
        rows.append({"Ticker": ticker, "Shares": h["shares"], "Price": f"${price:,.2f}", "Value": f"${value:,.2f}"})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

# Crypto
if breakdown.get("crypto"):
    st.markdown("**Crypto**")
    rows = []
    for h in holdings.get("crypto", []):
        symbol = h["symbol"]
        value = breakdown["crypto"].get(symbol, 0)
        price = round(value / h["amount"], 2) if h["amount"] else 0
        rows.append({"Asset": symbol, "Amount": h["amount"], "Price": f"${price:,.2f}", "Value": f"${value:,.2f}"})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

# Cash
if breakdown.get("cash"):
    st.markdown("**Cash**")
    rows = []
    for label, amount in breakdown["cash"].items():
        rows.append({"Account": label, "Balance": f"${amount:,.2f}"})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
