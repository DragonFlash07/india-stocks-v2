import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (GREEN, INDICES, NIFTY50, RED, TEMPLATE, disclaimer,
                    load_index, load_movers, show_chart)

st.title("INDIA MARKET DASHBOARD")
if st.button("Refresh data"):
    st.cache_data.clear()

cols = st.columns(len(INDICES))
for col, (name, sym) in zip(cols, INDICES.items()):
    try:
        data = load_index(sym)
    except Exception:
        data = None
    if data:
        last, prev = data
        col.metric(name, f"{last:,.2f}", f"{(last / prev - 1) * 100:+.2f}%")
    else:
        col.metric(name, "n/a")

tab1, tab2 = st.tabs(["Top / Bottom 5", "Heatmap"])

with st.spinner("Loading Nifty 50 prices..."):
    movers = load_movers(tuple(NIFTY50))

with tab1:
    if movers.empty:
        st.error("No price data came back. Check your connection or try again in a minute.")
    else:
        left, right = st.columns(2)
        top5 = movers.nlargest(5, "Change %").sort_values("Change %")
        bot5 = movers.nsmallest(5, "Change %").sort_values("Change %", ascending=False)
        for col, d, title, color in (
            (left, top5, "Top 5 gainers", GREEN),
            (right, bot5, "Bottom 5 losers", RED),
        ):
            fig = go.Figure(go.Bar(
                x=d["Change %"], y=d["Symbol"], orientation="h", marker_color=color,
                text=[f"{v:+.2f}%" for v in d["Change %"]], textposition="outside"))
            fig.update_layout(template=TEMPLATE, title=title, height=340,
                              margin=dict(l=10, r=40, t=50, b=10),
                              xaxis_title="Change vs previous close (%)")
            with col:
                show_chart(fig)
                st.dataframe(
                    d.sort_values("Change %", ascending=(color == RED))
                     [["Symbol", "Price", "Change %"]].round(2),
                    hide_index=True)

with tab2:
    if movers.empty:
        st.info("No data to show.")
    else:
        m = movers.copy()
        m["Size"] = 1
        fig = px.treemap(
            m, path=["Symbol"], values="Size", color="Change %",
            color_continuous_scale=[RED, "#2a2a2a", GREEN],
            color_continuous_midpoint=0, custom_data=["Price", "Change %"])
        fig.update_traces(
            texttemplate="%{label}<br>%{customdata[1]:+.2f}%",
            hovertemplate="%{label}<br>Price: %{customdata[0]:.2f}"
                          "<br>Change: %{customdata[1]:+.2f}%<extra></extra>")
        fig.update_layout(template=TEMPLATE, height=560,
                          margin=dict(l=0, r=0, t=10, b=0))
        show_chart(fig)

disclaimer()
