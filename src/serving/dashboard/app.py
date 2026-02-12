"""
CryptoLake Dashboard — Streamlit App

Interactive dashboard for crypto market analytics.
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time

# Auto-refresh cada 30 segundos
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=30 * 1000, key="data_refresh")

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="CryptoLake Dashboard",
    page_icon="🏔️",
    layout="wide",
)


@st.cache_data(ttl=30)
def fetch_market_overview():
    try:
        response = requests.get(f"{API_URL}/api/v1/analytics/market-overview")
        return response.json()
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return []


@st.cache_data(ttl=30)
def fetch_fear_greed():
    try:
        response = requests.get(f"{API_URL}/api/v1/analytics/fear-greed")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching Fear & Greed: {e}")
        return {"value": 50, "classification": "Neutral"}


@st.cache_data(ttl=30)
def fetch_price_history(coin_id: str):
    try:
        response = requests.get(f"{API_URL}/api/v1/prices/{coin_id}")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching prices: {e}")
        return []


def fetch_prediction():
    try:
        response = requests.get(f"{API_URL}/api/v1/analytics/prediction")
        return response.json()
    except Exception as e:
        return None


def fetch_realtime_ohlc(coin_id: str):
    try:
        url = f"{API_URL}/api/v1/analytics/realtime-ohlc/{coin_id}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.sidebar.error(f"Error OHLC: {e}")
        return []


pred = fetch_prediction()
if pred:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 ML Status (Dual Memory)")

    bias_color = "🟢" if pred['sentiment_bias'] == "Bullish" else "🔴"
    st.sidebar.write(f"{bias_color} Bias: **{pred['sentiment_bias']}**")

    if 'memory_details' in pred and pred['memory_details']:
        hist = pred['memory_details'].get('historical', 0)
        recent = pred['memory_details'].get('recent', 0)

        # Mostrar influencia en modo barra de progreso o texto
        st.sidebar.info(f"🏛️ Historical: {hist:.4f}")
        st.sidebar.success(f"⚡ Recent: {recent:.4f}")
        st.sidebar.caption("Ensamble: 70% Recent | 30% Hist")

st.title("🏔️ CryptoLake — Crypto Analytics Dashboard")
st.markdown("---")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Market Overview", "Price Charts", "Fear & Greed Index"],
)

if page == "Market Overview":
    st.header("📊 Market Overview")

    overview_data = fetch_market_overview()
    fg_data = fetch_fear_greed()

    if not overview_data:
        st.warning("No data available in the lake. Run ingestion scripts first.")
    else:
        # Top Metrics
        # Search for major coins
        def get_coin_metric(data, cid):
            for c in data:
                if c["coin_id"] == cid:
                    return c
            return None

        btc = get_coin_metric(overview_data, "bitcoin")
        eth = get_coin_metric(overview_data, "ethereum")
        sol = get_coin_metric(overview_data, "solana")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if btc:
                st.metric("Bitcoin", f"${btc['current_price']:,.0f}")
        with col2:
            if eth:
                st.metric("Ethereum", f"${eth['current_price']:,.2f}")
        with col3:
            if sol:
                st.metric("Solana", f"${sol['current_price']:,.2f}")
        with col4:
            st.metric("Fear & Greed",
                      fg_data['value'], fg_data['classification'])

        # Real-time Prediction Section
        st.markdown("---")
        st.subheader("🔮 AI Prediction Council")
        pred = fetch_prediction()

        if pred and pred["timestamp"] > 0:
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                st.metric("Current Price (Ref)",
                          f"${pred['current_price']:,.2f}")
            with p_col2:
                # Mostrar N/A si la predicción es absurda (negativa)
                val_pred = f"${pred['predicted_price']:,.2f}" if pred['predicted_price'] > 0 else "Calculando..."
                st.metric("AI Target Price", val_pred)
            with p_col3:
                st.info(f"Market Bias: **{pred['sentiment_bias']}**")

            # Candlestick Chart (Bitcoin by default for overview)
            ohlc_data = fetch_realtime_ohlc("bitcoin")
            if ohlc_data:
                df_ohlc = pd.DataFrame(ohlc_data)
                df_ohlc['timestamp'] = pd.to_datetime(df_ohlc['timestamp'])

                fig_ohlc = go.Figure(data=[go.Candlestick(
                    x=df_ohlc['timestamp'],
                    open=df_ohlc['open'],
                    high=df_ohlc['high'],
                    low=df_ohlc['low'],
                    close=df_ohlc['close'],
                    name='BTC Real-time'
                )])

                # Solo agregar línea si la predicción es válida
                if pred['predicted_price'] > 0:
                    fig_ohlc.add_hline(
                        y=pred['predicted_price'],
                        line_dash="dash",
                        line_color="cyan",
                        annotation_text="AI TARGET",
                        annotation_position="top right"
                    )

                fig_ohlc.update_layout(
                    title="Real-time BTC Candles & AI Prediction",
                    xaxis_rangeslider_visible=False,
                    template="plotly_dark",
                    height=500
                )
                st.plotly_chart(fig_ohlc, width='stretch')
            else:
                st.info("⌛ Esperando primer micro-batch de datos OHLC...")

        st.subheader("All Assets")
        df = pd.DataFrame(overview_data)
        st.dataframe(df, width='stretch')

elif page == "Price Charts":
    st.header("📈 Price Charts")

    overview_data = fetch_market_overview()
    if not overview_data:
        st.warning("No data available.")
    else:
        coins = [c["coin_id"] for c in overview_data]
        selected_coin = st.selectbox("Select Cryptocurrency", coins)

        if selected_coin:
            # 1. Real-time OHLC Chart (Stock style)
            st.subheader(f"🕯️ Intraday Candles: {selected_coin.upper()}")
            ohlc_data = fetch_realtime_ohlc(selected_coin)

            if ohlc_data:
                df_ohlc = pd.DataFrame(ohlc_data)
                df_ohlc['timestamp'] = pd.to_datetime(df_ohlc['timestamp'])

                fig_candlestick = go.Figure(data=[go.Candlestick(
                    x=df_ohlc['timestamp'],
                    open=df_ohlc['open'],
                    high=df_ohlc['high'],
                    low=df_ohlc['low'],
                    close=df_ohlc['close'],
                    name='Real-time'
                )])
                fig_candlestick.update_layout(
                    template="plotly_dark",
                    xaxis_rangeslider_visible=True,
                    height=500
                )
                st.plotly_chart(fig_candlestick, width='stretch')
            else:
                st.info(
                    f"No hay datos de velas en tiempo real para {selected_coin} todavía.")

            # 2. Historical Line Chart
            st.subheader(f"📊 Historical Price: {selected_coin.upper()}")
            history = fetch_price_history(selected_coin)
            if history:
                df_hist = pd.DataFrame(history)
                df_hist["price_date"] = pd.to_datetime(df_hist["price_date"])

                fig_line = px.line(df_hist, x="price_date", y="price_usd")
                fig_line.update_layout(template="plotly_dark")
                st.plotly_chart(fig_line, width='stretch')

                st.subheader("Historical Data Table")
                st.dataframe(df_hist, width='stretch')

elif page == "Fear & Greed Index":
    st.header("😱 Fear & Greed Index")
    fg_data = fetch_fear_greed()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current Value", fg_data['value'])
    with col2:
        st.metric("Classification", fg_data['classification'])

    st.info("The Fear & Greed Index provides a sentiment score from 0 (Extreme Fear) to 100 (Extreme Greed).")
