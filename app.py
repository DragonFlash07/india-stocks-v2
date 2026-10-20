"""
India Market Lab: entry point. Sets up the sidebar stock selector and the pages.
Run:  streamlit run app.py
"""
import streamlit as st

from common import NIFTY50

st.set_page_config(page_title="India Market Lab", page_icon="📈", layout="wide")

with st.sidebar:
    st.markdown("### Select stock")
    default_idx = NIFTY50.index("RELIANCE") if "RELIANCE" in NIFTY50 else 0
    choice = st.selectbox("Nifty 50 stock", NIFTY50, index=default_idx)
    custom = st.text_input("Or type any NSE symbol", placeholder="e.g. IRCTC").strip().upper()

symbol = custom if custom else choice
if "." not in symbol:
    symbol += ".NS"
st.session_state["symbol"] = symbol  # every page reads this

pages = [
    st.Page("views/dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("views/stock_analysis.py", title="Stock Analysis", icon="🔎"),
    st.Page("views/monte_carlo.py", title="Monte Carlo", icon="🎲"),
]
st.navigation(pages).run()
