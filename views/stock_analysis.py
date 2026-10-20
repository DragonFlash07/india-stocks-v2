import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from common import (AMBER, GREEN, RED, TEMPLATE, current_symbol, disclaimer,
                    fmt, fmt_cr, load_history, load_info, rsi, short,
                    show_chart)

symbol = current_symbol()

try:
    info = load_info(symbol)
except Exception:
    info = {}

try:
    hist = load_history(symbol, "5y", "1d")
except Exception:
    hist = None

if hist is None or hist.empty:
    st.title(short(symbol))
    st.warning(f"No price data for {symbol}. Check the symbol in the sidebar "
               "(NSE symbols only, e.g. TCS or IRCTC) or try again in a minute.")
    st.stop()

close = hist["Close"].dropna()
price, prev = float(close.iloc[-1]), float(close.iloc[-2])

st.title(info.get("longName") or short(symbol))
bits = [b for b in (info.get("sector"), info.get("industry")) if b]
if bits:
    st.caption(" · ".join(bits))

# ------------------------------------------------------------------ metrics
c1, c2 = st.columns([1, 3])
c1.metric("Last price", fmt(price, 2, "₹"), f"{(price / prev - 1) * 100:+.2f}%")

yr = hist.tail(252)
hi, lo = float(yr["High"].max()), float(yr["Low"].min())
with c2:
    st.write(f"**52-week range:** ₹{lo:,.2f}  to  ₹{hi:,.2f}")
    st.progress(min(max((price - lo) / (hi - lo), 0.0), 1.0) if hi > lo else 0.0)


def row(items):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


if not info:
    st.info("Company metrics are unavailable right now (Yahoo may be throttling). "
            "The price-based stats and chart below still work.")

roe, pm, rg = info.get("returnOnEquity"), info.get("profitMargins"), info.get("revenueGrowth")
rate = info.get("dividendRate")
div_yield = (rate / price * 100) if rate and price else None

st.subheader("Valuation and quality")
row([("Market cap", fmt_cr(info.get("marketCap"))),
     ("P/E (trailing)", fmt(info.get("trailingPE"), 1)),
     ("P/E (forward)", fmt(info.get("forwardPE"), 1)),
     ("Price / Book", fmt(info.get("priceToBook"), 2))])
row([("EPS (trailing)", fmt(info.get("trailingEps"), 2, "₹")),
     ("Return on equity", fmt(roe * 100 if roe is not None else None, 1, suffix="%")),
     ("Debt / Equity (%)", fmt(info.get("debtToEquity"), 1)),
     ("Dividend yield", fmt(div_yield, 2, suffix="%"))])
row([("Profit margin", fmt(pm * 100 if pm is not None else None, 1, suffix="%")),
     ("Revenue growth (yoy)", fmt(rg * 100 if rg is not None else None, 1, suffix="%")),
     ("Beta", fmt(info.get("beta"), 2)),
     ("Avg. volume", fmt(info.get("averageVolume"), 0))])

# ------------------------------------------------------------ performance/risk
st.subheader("Performance and risk")


def ret(n):
    return (close.iloc[-1] / close.iloc[-1 - n] - 1) * 100 if len(close) > n else None


logret = np.log(close / close.shift(1)).dropna().tail(252)
vol = float(logret.std() * np.sqrt(252) * 100) if len(logret) > 20 else None
last_year = close.tail(252)
max_dd = float((last_year / last_year.cummax() - 1).min() * 100)

row([("1 month", fmt(ret(21), 1, suffix="%")),
     ("3 months", fmt(ret(63), 1, suffix="%")),
     ("6 months", fmt(ret(126), 1, suffix="%")),
     ("1 year", fmt(ret(252), 1, suffix="%"))])
row([("Volatility (1y, annualised)", fmt(vol, 1, suffix="%")),
     ("Worst drop from a peak (1y)", fmt(max_dd, 1, suffix="%")),
     ("Best day (1y)", fmt(np.exp(logret.max()) * 100 - 100 if len(logret) else None, 1, suffix="%")),
     ("Worst day (1y)", fmt(np.exp(logret.min()) * 100 - 100 if len(logret) else None, 1, suffix="%"))])

with st.expander("What do these terms mean?"):
    st.markdown(
        "- **P/E**: price divided by yearly earnings per share. Higher can mean "
        "growth is expected, or that the stock is expensive.\n"
        "- **Price / Book**: price compared with the company's net assets per share.\n"
        "- **Return on equity**: profit earned per rupee of shareholders' money.\n"
        "- **Debt / Equity**: borrowing relative to shareholders' money, shown as Yahoo "
        "reports it (a percentage).\n"
        "- **Beta**: how strongly the stock moves with the market. Above 1 means bigger swings.\n"
        "- **Volatility**: how much the price typically swings in a year.\n"
        "- **Worst drop from a peak**: the largest fall from a high point in the last year.")

# ------------------------------------------------------------------ chart
st.subheader("Price chart")
c1, c2 = st.columns(2)
period = c1.selectbox("Range", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
interval = c2.selectbox("Interval", ["1d", "1wk"], index=0)

h = load_history(symbol, period, interval)
if h.empty or len(h) < 3:
    st.warning("Not enough data for this range.")
else:
    h = h.copy()
    h["MA20"] = h["Close"].rolling(20).mean()
    h["MA50"] = h["Close"].rolling(50).mean()
    h["RSI"] = rsi(h["Close"])

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(
        x=h.index, open=h["Open"], high=h["High"], low=h["Low"], close=h["Close"],
        name="Price", increasing_line_color=GREEN, decreasing_line_color=RED), row=1, col=1)
    fig.add_trace(go.Scatter(x=h.index, y=h["MA20"], name="MA20",
                             line=dict(color=AMBER, width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=h.index, y=h["MA50"], name="MA50",
                             line=dict(color="#40c4ff", width=1)), row=1, col=1)
    vol_colors = [GREEN if c >= o else RED for c, o in zip(h["Close"], h["Open"])]
    fig.add_trace(go.Bar(x=h.index, y=h["Volume"], marker_color=vol_colors,
                         name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=h.index, y=h["RSI"], name="RSI 14",
                             line=dict(color="#ce93d8", width=1)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color=RED, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color=GREEN, row=3, col=1)
    fig.update_layout(template=TEMPLATE, height=720, xaxis_rangeslider_visible=False,
                      margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.02))
    show_chart(fig)

disclaimer()
