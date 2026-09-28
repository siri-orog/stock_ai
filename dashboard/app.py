import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from indicators.smma import calculate_smma
from strategy.crossover import get_signal
from ml.model import evaluate_trade
from data.fetch import get_live_data
from data.symbols import SYMBOLS

st.set_page_config(layout="wide")

# 🎨 NAVY BLUE THEME
st.markdown("""
<style>

body {
    background-color: #0b1220;
}

.main {
    background-color: #0b1220;
}

h1 {
    color: #00d4ff;
}

table {
    width: 100%;
    border-collapse: collapse;
    background-color: #111827;
    color: white;
    border-radius: 10px;
    overflow: hidden;
}

th {
    background-color: #1f2937;
    padding: 12px;
    text-align: left;
    font-size: 14px;
    color: #9ca3af;
}

td {
    padding: 12px;
    border-bottom: 1px solid #1f2937;
}

tr:hover {
    background-color: #1a2332;
}

.buy { color: #22c55e; font-weight: bold; }
.sell { color: #ef4444; font-weight: bold; }
.hold { color: #facc15; font-weight: bold; }

.badge {
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
}

.green { background: #14532d; color: #22c55e; }
.red { background: #7f1d1d; color: #ef4444; }
.orange { background: #78350f; color: #facc15; }

</style>
""", unsafe_allow_html=True)

# 🔥 HEADER
st.markdown("# 📊 AI Trading Dashboard 🚀")

# 📡 DATA
stocks = get_live_data(SYMBOLS)

if len(stocks) == 0:
    st.warning("No data from API")
    st.stop()

# 📊 CALCULATIONS
prices = [s["ltp"] for s in stocks]

smma20 = calculate_smma(prices, 20)
smma120 = calculate_smma(prices, 120)

# 🧾 TABLE HEADER
table_html = """
<table>
<tr>
    <th>Symbol</th>
    <th>LTP</th>
    <th>SMMA20</th>
    <th>SMMA120</th>
    <th>BidQty</th>
    <th>AskQty</th>
    <th>Signal</th>
    <th>Confidence</th>
    <th>Decision</th>
    <th>Reason</th>
</tr>
"""

# 📊 LOOP
for i, stock in enumerate(stocks):

    if i == 0:
        continue

    signal = get_signal(smma20[i], smma120[i])

    confidence, decision, reason = evaluate_trade({
        "volume": stock["volume"],
        "bidQty": stock["bidQty"],
        "askQty": stock["askQty"],
        "ltp": stock["ltp"],
        "smma20": smma20[i],
        "smma120": smma120[i]
    })

    # 🎨 styling
    signal_class = "hold"
    badge = "orange"

    if signal == "BUY":
        signal_class = "buy"
        badge = "green"
    elif signal == "SELL":
        signal_class = "sell"
        badge = "red"

    table_html += f"""
    <tr>
        <td>{stock['symbol']}</td>
        <td>{stock['ltp']}</td>
        <td>{round(smma20[i],2)}</td>
        <td>{round(smma120[i],2)}</td>
        <td>{stock['bidQty']}</td>
        <td>{stock['askQty']}</td>
        <td class="{signal_class}">{signal}</td>
        <td>{confidence}</td>
        <td><span class="badge {badge}">{decision}</span></td>
        <td>{reason}</td>
    </tr>
    """

table_html += "</table>"

# 🚀 RENDER TABLE
st.markdown(table_html, unsafe_allow_html=True)