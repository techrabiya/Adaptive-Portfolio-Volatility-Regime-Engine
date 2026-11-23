import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Adaptive Portfolio Volatility Regime Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1B2631 0%, #2E4053 100%);
        border-right: 2px solid #5DADE2;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #ECF0F1 !important;
        font-weight: 600;
    }
    div[data-testid="metric-container"] {
        background-color: #F4F6F7;
        border-left: 5px solid #2874A6;
        padding: 14px;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("⚡ Adaptive Portfolio Volatility Regime Engine")
st.subheader("Market Shock Stress-Tester, Rolling Volatility & Dynamic Risk Allocation Lab")
st.markdown("---")

st.sidebar.header("🎛️ Regime & Risk Controls")
initial_capital = st.sidebar.number_input("Initial Capital (₹)", min_value=50000, max_value=10000000, value=500000, step=25000)
rolling_window = st.sidebar.slider("Rolling Volatility Window (Days)", 5, 40, 14, 1)
vol_threshold = st.sidebar.slider("High Volatility Alert Threshold (%)", 1.0, 8.0, 3.2, 0.2)
shock_severity = st.sidebar.slider("Market Shock Severity", 0.0, 3.0, 1.5, 0.1)
base_drift_pct = st.sidebar.slider("Daily Drift Bias (%)", -0.30, 0.60, 0.08, 0.02)

try:
    np.random.seed(42)
    n_days = 180
    days = np.arange(1, n_days + 1)

    base_vol = 0.012
    returns = np.random.normal(loc=base_drift_pct / 100.0, scale=base_vol, size=n_days)

    returns[55:85] += np.random.normal(loc=-0.004 * shock_severity, scale=0.022 * shock_severity, size=30)
    returns[125:142] += np.random.normal(loc=-0.012 * shock_severity, scale=0.032 * shock_severity, size=17)

    clean_returns = np.clip(returns, -0.25, 0.25)

    df = pd.DataFrame({
        "Day": days,
        "Daily_Return_Pct": clean_returns * 100.0
    })

    df["Rolling_Vol_Pct"] = (
        df["Daily_Return_Pct"]
        .rolling(window=rolling_window, min_periods=1)
        .std()
        .fillna(0.0)
    )

    df["Regime"] = np.where(
        df["Rolling_Vol_Pct"] > vol_threshold,
        "HIGH_VOL_ALERT",
        "NORMAL_REGIME"
    )

    df["Risk_Exposure"] = np.where(
        df["Rolling_Vol_Pct"] > vol_threshold,
        np.clip(vol_threshold / np.maximum(df["Rolling_Vol_Pct"], 0.1), 0.25, 1.0),
        1.0
    )

    df["Adaptive_Return_Pct"] = df["Daily_Return_Pct"] * df["Risk_Exposure"]
    df["Static_Equity"] = initial_capital * np.cumprod(1.0 + df["Daily_Return_Pct"] / 100.0)
    df["Adaptive_Equity"] = initial_capital * np.cumprod(1.0 + df["Adaptive_Return_Pct"] / 100.0)

    running_peak = np.maximum.accumulate(df["Adaptive_Equity"])
    drawdown_pct = ((df["Adaptive_Equity"] - running_peak) / np.maximum(running_peak, 1.0)) * 100.0
    max_drawdown_pct = float(np.min(drawdown_pct))

    var_95_pct = float(np.percentile(df["Adaptive_Return_Pct"], 5))
    final_adaptive_val = float(df["Adaptive_Equity"].iloc[-1])
    final_static_val = float(df["Static_Equity"].iloc[-1])
    high_vol_days = int((df["Regime"] == "HIGH_VOL_ALERT").sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="💼 Adaptive Ending Capital",
            value=f"₹{final_adaptive_val:,.0f}",
            delta=f"vs Static: ₹{final_adaptive_val - final_static_val:,.0f}"
        )
    with c2:
        st.metric(
            label="📉 Max Drawdown (Adaptive)",
            value=f"{max_drawdown_pct:.2f}%"
        )
    with c3:
        st.metric(
            label="🛡️ 95% Daily VaR",
            value=f"{var_95_pct:.2f}%"
        )
    with c4:
        st.metric(
            label="🚨 High-Vol Alert Days",
            value=f"{high_vol_days} / {n_days}"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    left_chart, right_chart = st.columns(2)

    with left_chart:
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            x=df["Day"],
            y=df["Adaptive_Equity"],
            mode="lines",
            name="Adaptive Risk Equity (₹)",
            line=dict(color="#1F618D", width=3)
        ))
        fig_eq.add_trace(go.Scatter(
            x=df["Day"],
            y=df["Static_Equity"],
            mode="lines",
            name="Unfiltered Static Equity (₹)",
            line=dict(color="#B03A2E", width=2, dash="dash")
        ))
        fig_eq.update_layout(
            title="Equity Curve: Adaptive Risk vs. Unfiltered Static",
            xaxis_title="Trading Day",
            yaxis_title="Portfolio Value (₹)",
            template="plotly_white",
            hovermode="x unified",
            height=390
        )
        st.plotly_chart(fig_eq, use_container_width=True)

    with right_chart:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(
            x=df["Day"],
            y=df["Rolling_Vol_Pct"],
            mode="lines",
            name="Rolling Volatility (%)",
            line=dict(color="#D35400", width=2.5)
        ))
        fig_vol.add_hline(
            y=vol_threshold,
            line_dash="dot",
            line_color="#C0392B",
            annotation_text=f"Alert Threshold ({vol_threshold:.1f}%)",
            annotation_position="top left"
        )
        fig_vol.update_layout(
            title="Rolling Volatility & Regime Threshold Trigger",
            xaxis_title="Trading Day",
            yaxis_title="Volatility (%)",
            template="plotly_white",
            hovermode="x unified",
            height=390
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    with st.expander("📊 Inspect Regime Log, Exposure & Drawdown Data"):
        st.dataframe(df.round(3), use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Engine Execution Error: {e}")
    st.info("Tune the sidebar controls and run the simulation again.")
