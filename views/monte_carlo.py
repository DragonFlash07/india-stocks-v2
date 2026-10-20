import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (AMBER, GREEN, RED, TEMPLATE, current_symbol, disclaimer,
                    fmt, load_history, short, show_chart)

symbol = current_symbol()
st.title(f"Monte Carlo simulator: {short(symbol)}")
st.caption("Simulates thousands of possible price paths from the stock's own history, "
           "to show a range of outcomes. It is not a forecast.")

HORIZONS = {"1 month": 21, "3 months": 63, "6 months": 126, "1 year": 252, "2 years": 504}

c1, c2, c3 = st.columns(3)
horizon = c1.selectbox("Horizon", list(HORIZONS), index=3)
n_sims = c2.select_slider("Simulations", [500, 1000, 2000, 5000, 10000], value=2000)
window = c3.selectbox("History used to measure risk", ["1y", "2y", "5y"], index=1)
days = HORIZONS[horizon]

try:
    hist = load_history(symbol, window, "1d")
except Exception:
    hist = None
close = hist["Close"].dropna() if hist is not None and not hist.empty else pd.Series(dtype=float)
if len(close) < 60:
    st.warning(f"Not enough price history for {symbol}. Check the symbol in the sidebar.")
    st.stop()

S0 = float(close.iloc[-1])
r = np.log(close / close.shift(1)).dropna().values
s_hist = float(r.std(ddof=1))
hist_vol = s_hist * np.sqrt(252) * 100

with st.expander("Advanced settings"):
    a1, a2, a3 = st.columns(3)
    method = a1.radio("Daily shocks", ["Normal (bell curve)", "Bootstrap (reuse real days)"],
                      help="Bootstrap reshuffles the stock's actual daily moves, so big "
                           "crashes and spikes can reappear.")
    drift_mode = a2.radio("Expected return", ["Historical average", "Neutral (no expected gain)", "Custom"])
    custom_mu = a2.number_input("Custom annual return (%)", -50.0, 100.0, 10.0, 1.0)
    override = a3.checkbox("Override volatility")
    vol_in = a3.number_input("Annual volatility (%)", 5.0, 150.0,
                             float(min(max(round(hist_vol, 1), 5.0), 150.0)), 1.0)
    seed = a3.number_input("Random seed", 0, 999999, 42, 1,
                           help="Same seed gives the same result. Change it for a new run.")

s = vol_in / 100 / np.sqrt(252) if override else s_hist
if drift_mode == "Historical average":
    drift = float(r.mean())
elif drift_mode.startswith("Neutral"):
    drift = -0.5 * s ** 2
else:
    drift = custom_mu / 100 / 252 - 0.5 * s ** 2

# ------------------------------------------------------------------ simulate
rng = np.random.default_rng(int(seed))
if method.startswith("Normal"):
    shocks = rng.standard_normal((n_sims, days)) * s
else:
    pool = r - r.mean()
    shocks = pool[rng.integers(0, len(pool), size=(n_sims, days))] * (s / s_hist)
paths = S0 * np.exp(np.cumsum(drift + shocks, axis=1))
paths = np.hstack([np.full((n_sims, 1), S0), paths])
final = paths[:, -1]

p5, p25, p50, p75, p95 = np.percentile(final, [5, 25, 50, 75, 95])
st.info(
    f"Out of {n_sims:,} simulated futures, the middle outcome after {horizon} is "
    f"**₹{p50:,.2f}** ({(p50 / S0 - 1) * 100:+.1f}% vs ₹{S0:,.2f} today). "
    f"About 9 in 10 outcomes land between **₹{p5:,.2f}** and **₹{p95:,.2f}**.")
st.caption(f"Settings used: volatility {s * np.sqrt(252) * 100:.1f}% a year, "
           f"expected drift {drift * 252 * 100:.1f}% a year (log terms), {method.lower()}.")

# ------------------------------------------------------------------ fan chart
x = np.arange(days + 1)
bands = np.percentile(paths, [5, 25, 50, 75, 95], axis=0)
fig = go.Figure()
for i in range(min(25, n_sims)):
    fig.add_trace(go.Scatter(x=x, y=paths[i], mode="lines", showlegend=False,
                             line=dict(width=0.6, color="rgba(255,255,255,0.10)"),
                             hoverinfo="skip"))
fig.add_trace(go.Scatter(x=x, y=bands[4], mode="lines", line=dict(width=0),
                         showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=x, y=bands[0], mode="lines", line=dict(width=0),
                         fill="tonexty", fillcolor="rgba(255,153,0,0.15)", name="5th to 95th percentile"))
fig.add_trace(go.Scatter(x=x, y=bands[3], mode="lines", line=dict(width=0),
                         showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=x, y=bands[1], mode="lines", line=dict(width=0),
                         fill="tonexty", fillcolor="rgba(255,153,0,0.30)", name="25th to 75th percentile"))
fig.add_trace(go.Scatter(x=x, y=bands[2], mode="lines", name="Median",
                         line=dict(color=AMBER, width=2.5)))
fig.add_hline(y=S0, line_dash="dot", line_color="#9e9e9e",
              annotation_text="Today", annotation_position="bottom left")
fig.update_layout(template=TEMPLATE, height=480, title="Possible price paths",
                  xaxis_title="Trading days ahead", yaxis_title="Price (₹)",
                  margin=dict(l=10, r=10, t=50, b=10),
                  legend=dict(orientation="h", y=1.08))
show_chart(fig)

# ------------------------------------------------------------------ distribution
left, right = st.columns(2)
hfig = go.Figure(go.Histogram(x=final, nbinsx=60, marker_color=AMBER, opacity=0.8))
hfig.add_vline(x=S0, line_dash="dot", line_color="#9e9e9e", annotation_text="Today")
hfig.add_vline(x=p50, line_color="#ffffff", annotation_text="Median")
hfig.update_layout(template=TEMPLATE, height=360, title=f"Price after {horizon}",
                   xaxis_title="Price (₹)", yaxis_title="Number of simulations",
                   margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
with left:
    show_chart(hfig)

table = pd.DataFrame({
    "Outcome": ["Bad case (5th percentile)", "Weak (25th)", "Median", "Good (75th)",
                "Strong (95th)", "Average"],
    "Price (₹)": [p5, p25, p50, p75, p95, final.mean()],
})
table["Change vs today (%)"] = (table["Price (₹)"] / S0 - 1) * 100
with right:
    st.markdown("**Outcome table**")
    st.dataframe(table.round(2), hide_index=True)

# ------------------------------------------------------------------ probabilities
st.subheader("Probability checks")
t1, t2 = st.columns(2)
up_target = t1.number_input("Upside target (₹)", min_value=0.01, value=round(S0 * 1.10, 2))
down_level = t2.number_input("Downside level (₹)", min_value=0.01, value=round(S0 * 0.90, 2))

k = st.columns(4)
k[0].metric("Ends above today's price", fmt((final > S0).mean() * 100, 1, suffix="%"))
k[1].metric(f"Ends above ₹{up_target:,.0f}", fmt((final >= up_target).mean() * 100, 1, suffix="%"))
k[2].metric(f"Touches ₹{up_target:,.0f} at any point", fmt((paths.max(axis=1) >= up_target).mean() * 100, 1, suffix="%"))
k[3].metric(f"Touches ₹{down_level:,.0f} at any point", fmt((paths.min(axis=1) <= down_level).mean() * 100, 1, suffix="%"))

with st.expander("How this works, and its limits"):
    st.markdown(
        "- Each simulated path adds random daily moves, sized by the stock's own "
        "historical volatility, to today's price.\n"
        "- **Normal** shocks follow a bell curve. **Bootstrap** reuses real past daily "
        "moves, so crashes and spikes can reappear.\n"
        "- The result depends on the history window and the expected-return setting. "
        "Historical averages can be very different from the future.\n"
        "- Real markets have gaps, news shocks and changing volatility that this simple "
        "model does not capture. Treat the output as a way to understand risk, not as a prediction.")

disclaimer()
