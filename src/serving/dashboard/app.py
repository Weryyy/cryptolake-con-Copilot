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


@st.cache_data(ttl=30)
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


def fetch_system_alerts():
    try:
        response = requests.get(f"{API_URL}/api/v1/analytics/system-alerts")
        return response.json()
    except:
        return []


def fetch_dq_reports():
    try:
        response = requests.get(f"{API_URL}/api/v1/analytics/dq-reports")
        return response.json()
    except:
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
    ["Market Overview", "Price Charts", "Fear & Greed Index", "Logs & System Status"],
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
            st.metric("Fear & Greed", fg_data['value'])
            st.caption(f"Sentiment: {fg_data['classification']}")

        # Real-time Prediction Section
        st.markdown("---")
        st.subheader("🔮 AI Prediction Council")
        pred = fetch_prediction()

        if pred and pred["timestamp"] > 0:
            st.info(
                f"Analyzing Target: **{pred.get('coin_id', 'Unknown').upper()}**")
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

                # Solo agregar línea si la predicción es válida (Predicted Wave)
                if pred['predicted_price'] > 0:
                    # Crear una "ola" o línea que conecte el último precio real con la predicción
                    last_time = df_ohlc['timestamp'].iloc[-1]
                    last_price = df_ohlc['close'].iloc[-1]
                    pred_time = last_time + pd.Timedelta(minutes=5)

                    fig_ohlc.add_trace(go.Scatter(
                        x=[last_time, pred_time],
                        y=[last_price, pred['predicted_price']],
                        mode='lines+markers',
                        name='AI WAVE Prediction',
                        line=dict(color='cyan', width=3, dash='dashdot'),
                        marker=dict(size=10, symbol='star')
                    ))

                    st.sidebar.success(
                        f"🎯 AI Prediction Wave: ${pred['predicted_price']:,.2f}")

                fig_ohlc.update_layout(
                    title="Real-time BTC Candles & AI Prediction",
                    xaxis_rangeslider_visible=False,
                    template="plotly_dark",
                    height=500
                )
                st.plotly_chart(fig_ohlc, width='stretch')
            else:
                st.info("⌛ Esperando primer micro-batch de datos OHLC...")

        st.subheader("🌍 All Assets Market Overview")
        df = pd.DataFrame(overview_data)
        if not df.empty:
            # Renombrar columnas para mejor visualización
            df_display = df.rename(columns={
                "coin_id": "Asset",
                "current_price": "Price (USD)",
                "price_change_24h_pct": "24h %",
                "market_cap_usd": "Market Cap",
                "volume_24h_usd": "Volume 24h"
            })
            # Formatear moneda y porcentajes
            st.dataframe(df_display.style.format({
                "Price (USD)": "${:,.2f}",
                "24h %": "{:+.2f}%",
                "Market Cap": "${:,.0f}",
                "Volume 24h": "${:,.0f}"
            }), width='stretch', hide_index=True)

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

                # Add AI Prediction Wave if available for this coin
                pred = fetch_prediction()
                if pred and pred['predicted_price'] > 0 and pred.get('coin_id') == selected_coin:
                    last_time = df_ohlc['timestamp'].iloc[-1]
                    last_price = df_ohlc['close'].iloc[-1]
                    pred_time = last_time + pd.Timedelta(seconds=30)

                    fig_candlestick.add_trace(go.Scatter(
                        x=[last_time, pred_time],
                        y=[last_price, pred['predicted_price']],
                        mode='lines+markers',
                        name='AI WAVE Prediction',
                        line=dict(color='cyan', width=3, dash='dashdot'),
                        marker=dict(size=10, symbol='star')
                    ))

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

                # 3. Data Table
                st.subheader("Historical Data Table")
                st.dataframe(df_hist, width='stretch', hide_index=True)

elif page == "Logs & System Status":
    st.header("🛠️ System Status & Data Quality")

    col_dq, col_alerts = st.columns([1, 2])

    with col_dq:
        st.subheader("✅ Data Quality (GX)")
        dq_data = fetch_dq_reports()
        if dq_data:
            for report in dq_data:
                color = "green" if report['success_rate'] > 0.9 else "orange"
                st.markdown(f"""
                <div style="border-left: 5px solid {color}; padding-left: 10px; margin-bottom: 10px;">
                    <strong>Table: {report['table_name']}</strong><br/>
                    Success Rate: {report['success_rate']*100:.1f}%<br/>
                    <small>Checks: {report['successful_expectations']}/{report['total_expectations']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay reportes de DQ aún.")

    with col_alerts:
        st.subheader("🚨 System Alertas (Slack-style)")
        alerts = fetch_system_alerts()
        if isinstance(alerts, list) and alerts:
            for alert in alerts:
                if not isinstance(alert, dict):
                    continue
                lvl = alert.get('level', 'INFO')
                lvl_emoji = "🔴" if lvl == "CRITICAL" else "⚠️"
                ts = alert.get('timestamp', time.time())
                st.markdown(f"""
                **{lvl_emoji} {lvl}** - {time.strftime('%H:%M:%S', time.localtime(ts))}  
                `DAG: {alert.get('dag_id', 'N/A')} | Task: {alert.get('task_id', 'N/A')}`  
                > {alert.get('message', 'No message')}
                ---
                """)
        else:
            st.success("No hay alertas críticas en el sistema. Todo ok. ✅")

    st.markdown("---")
    st.subheader("⚙️ Hardware Accelerator")
    st.info(
        "Detected GPU: **NVIDIA Quadro K4200 (Kepler)** | CPU: **Intel Xeon E5-1620 v3**")
    st.caption(
        "Los agentes duales están optimizados para utilizar aceleración CUDA si está disponible.")

elif page == "Fear & Greed Index":
    st.header("😱 Fear & Greed Index")
    fg_data = fetch_fear_greed()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Current Value", fg_data['value'])
        st.subheader(f"Status: {fg_data['classification']}")

    with col2:
        # Gauge chart for Fear & Greed
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fg_data['value'],
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Market Sentiment"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "white"},
                'steps': [
                    {'range': [0, 25], 'color': "darkred"},
                    {'range': [25, 45], 'color': "red"},
                    {'range': [45, 55], 'color': "gray"},
                    {'range': [55, 75], 'color': "lightgreen"},
                    {'range': [75, 100], 'color': "green"}
                ],
            }
        ))
        fig_gauge.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)

    st.info("The Fear & Greed Index provides a sentiment score from 0 (Extreme Fear) to 100 (Extreme Greed).")
    st.markdown("""
    - **0-25**: Extreme Fear (Opportunity?)
    - **25-45**: Fear
    - **45-55**: Neutral
    - **55-75**: Greed
    - **75-100**: Extreme Greed (Risk?)
    """)
