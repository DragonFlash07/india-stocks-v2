"""Shared settings and helpers for the India Market Lab app."""
import inspect

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# Edit freely. NSE symbols need ".NS" on Yahoo (added automatically below).
# Index membership changes; symbols with no data are skipped automatically.
NIFTY50 = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL",
    "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "ETERNAL",
    "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO",
    "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY",
    "ITC", "JIOFIN", "JSWSTEEL", "KOTAKBANK", "LT",
    "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
    "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SHRIRAMFIN",
    "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS",
    "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO",
]
INDICES = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
}
TEMPLATE = "plotly_dark"
GREEN, RED, AMBER = "#00c853", "#ff1744", "#ff9900"

# ------------------------------------------------------------ display helpers
_PLOTLY_HAS_WIDTH = "width" in inspect.signature(st.plotly_chart).parameters


def show_chart(fig):
    """Full-width plotly chart that works on old and new Streamlit versions."""
    if _PLOTLY_HAS_WIDTH:
        st.plotly_chart(fig, width="stretch")
    else:
        st.plotly_chart(fig, use_container_width=True)


def fmt(x, d=2, prefix="", suffix=""):
    try:
        if x is None or pd.isna(x):
            return "n/a"
        return f"{prefix}{x:,.{d}f}{suffix}"
    except Exception:
        return "n/a"


def fmt_cr(x):
    """Rupees to crores (1 crore = 10 million)."""
    try:
        if x is None or pd.isna(x):
            return "n/a"
        return f"₹{x / 1e7:,.0f} Cr"
    except Exception:
        return "n/a"


def current_symbol() -> str:
    return st.session_state.get("symbol", "RELIANCE.NS")


def short(symbol: str) -> str:
    return symbol.replace(".NS", "").replace(".BO", "")


def disclaimer():
    st.divider()
    st.caption("Educational illustration only. Data is delayed and unofficial "
               "(Yahoo Finance). Not investment advice.")


# ------------------------------------------------------------ data loaders
@st.cache_data(ttl=300, show_spinner=False)
def load_movers(symbols: tuple) -> pd.DataFrame:
    tickers = [s + ".NS" for s in symbols]
    raw = yf.download(tickers, period="10d", interval="1d",
                      auto_adjust=True, progress=False, group_by="column")
    if raw is None or raw.empty:
        return pd.DataFrame()
    close = raw["Close"].ffill().dropna(how="all")
    if len(close) < 2:
        return pd.DataFrame()
    last, prev = close.iloc[-1], close.iloc[-2]
    df = pd.DataFrame({"Price": last, "Prev": prev}).dropna()
    df["Change %"] = (df["Price"] / df["Prev"] - 1) * 100
    df.index = [i.replace(".NS", "") for i in df.index]
    df.index.name = "Symbol"
    return df.reset_index()


@st.cache_data(ttl=300, show_spinner=False)
def load_index(symbol: str):
    h = yf.Ticker(symbol).history(period="10d", interval="1d")
    if len(h) < 2:
        return None
    return float(h["Close"].iloc[-1]), float(h["Close"].iloc[-2])


@st.cache_data(ttl=300, show_spinner=False)
def load_history(symbol: str, period: str, interval: str) -> pd.DataFrame:
    return yf.Ticker(symbol).history(period=period, interval=interval)


@st.cache_data(ttl=3600, show_spinner=False)
def load_info(symbol: str) -> dict:
    # Errors are raised (and therefore not cached); callers catch them.
    return yf.Ticker(symbol).info or {}


def rsi(series: pd.Series, n: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)
