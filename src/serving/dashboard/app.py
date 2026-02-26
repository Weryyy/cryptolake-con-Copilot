"""
CryptoLake Dashboard — Streamlit App

Interactive dashboard for crypto market analytics.
"""

import os
import time
from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import requests
import streamlit as st
import streamlit.components.v1 as components

# Auto-refresh cada 30 segundos
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=300 * 1000, key="data_refresh")

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
        response = requests.get(
            f"{API_URL}/api/v1/analytics/market-overview", timeout=15)
        return response.json()
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return []


@st.cache_data(ttl=30)
def fetch_fear_greed():
    try:
        response = requests.get(
            f"{API_URL}/api/v1/analytics/fear-greed", timeout=15)
        return response.json()
    except Exception as e:
        st.error(f"Error fetching Fear & Greed: {e}")
        return {"value": 50, "classification": "Neutral"}


@st.cache_data(ttl=30)
def fetch_price_history(coin_id: str):
    try:
        response = requests.get(
            f"{API_URL}/api/v1/prices/{coin_id}", timeout=15)
        return response.json()
    except Exception as e:
        st.error(f"Error fetching prices: {e}")
        return []


def fetch_prediction():
    try:
        response = requests.get(
            f"{API_URL}/api/v1/analytics/prediction", timeout=15)
        return response.json()
    except Exception:
        return None


def fetch_dual_prediction():
    """Fetch predictions from both models (Legacy + Ensemble)."""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/analytics/dual-prediction", timeout=15)
        return response.json()
    except Exception:
        return None


def fetch_model_comparison():
    """Fetch accuracy comparison between both models."""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/analytics/model-comparison", timeout=15)
        return response.json()
    except Exception:
        return None


def fetch_prediction_accuracy():
    try:
        response = requests.get(
            f"{API_URL}/api/v1/analytics/prediction-accuracy", timeout=15)
        return response.json()
    except Exception:
        return None


@st.cache_data(ttl=30)
def fetch_fear_greed_history():
    """Fetch historical Fear & Greed data for bar chart."""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/analytics/fear-greed-history", timeout=15)
        return response.json()
    except Exception:
        return []


def fetch_realtime_ohlc(coin_id: str):
    """Fetch OHLC data — no cache, fragment already reruns every 30s."""
    try:
        url = f"{API_URL}/api/v1/analytics/realtime-ohlc/{coin_id}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


@st.cache_data(ttl=30)
def fetch_prediction_history(model: str = "ensemble", limit: int = 60):
    """Fetch historial de predicciones pasadas para graficar."""
    try:
        url = f"{API_URL}/api/v1/analytics/prediction-history/{model}"
        response = requests.get(url, params={"limit": limit}, timeout=15)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


def fetch_system_alerts():
    try:
        response = requests.get(
            f"{API_URL}/api/v1/analytics/system-alerts", timeout=15)
        return response.json()
    except Exception:
        return []


def fetch_dq_reports():
    try:
        response = requests.get(
            f"{API_URL}/api/v1/analytics/dq-reports", timeout=15)
        return response.json()
    except Exception:
        return []


def _render_plotly_html(fig, height=500, key="chart"):
    """Render a Plotly figure as native HTML to preserve zoom across refreshes."""
    html = pio.to_html(fig, full_html=False,
                       include_plotlyjs="cdn", config={"responsive": True})
    components.html(
        f'<div id="{key}">{html}</div>',
        height=height + 40,
        scrolling=False,
    )


def _compute_ema(prices, span=5):
    """Compute Exponential Moving Average for a list of prices."""
    s = pd.Series(prices)
    return s.ewm(span=span, adjust=False).mean().tolist()


@st.fragment(run_every=timedelta(seconds=30))
def realtime_chart_panel():
    """Auto-refreshing chart + accuracy panel — fragment preserves zoom."""
    chart_col, accuracy_col = st.columns([3, 1])

    with chart_col:
        # Controls row — line visibility toggles
        st.markdown("##### 📊 Líneas del gráfico")
        tog_cols = st.columns(4)
        with tog_cols[0]:
            show_legacy = st.checkbox(
                "🔵 Legacy TFT", value=True, key="show_legacy")
        with tog_cols[1]:
            show_ensemble = st.checkbox(
                "🟣 Ensemble", value=True, key="show_ensemble")
        with tog_cols[2]:
            show_ema = st.checkbox(
                "🟢 EMA Prediction", value=True, key="show_ema")
        with tog_cols[3]:
            show_pred_history = st.checkbox(
                "🟠 Historial predicciones", value=False, key="show_pred_hist"
            )

        # Candlestick Chart (Bitcoin by default for overview)
        try:
            ohlc_data = fetch_realtime_ohlc("bitcoin")
        except Exception as e:
            ohlc_data = []
            st.error(f"OHLC fetch error: {e}")

        if ohlc_data and len(ohlc_data) > 0:
            df_ohlc = pd.DataFrame(ohlc_data)
            df_ohlc["timestamp"] = pd.to_datetime(df_ohlc["timestamp"])

            fig_ohlc = go.Figure(
                data=[
                    go.Candlestick(
                        x=df_ohlc["timestamp"],
                        open=df_ohlc["open"],
                        high=df_ohlc["high"],
                        low=df_ohlc["low"],
                        close=df_ohlc["close"],
                        name="BTC Real-time",
                    )
                ]
            )

            # Dual Model Prediction Curves
            dual = fetch_dual_prediction()
            last_time = df_ohlc["timestamp"].iloc[-1]
            last_price = df_ohlc["close"].iloc[-1]

            # Legacy TFT prediction (single point - cyan line)
            if (
                show_legacy
                and dual
                and dual.get("legacy")
                and dual["legacy"].get("predicted_price", 0) > 0
            ):
                leg = dual["legacy"]
                pred_time_leg = last_time + pd.Timedelta(minutes=5)
                fig_ohlc.add_trace(
                    go.Scatter(
                        x=[last_time, pred_time_leg],
                        y=[last_price, leg["predicted_price"]],
                        mode="lines+markers",
                        name="Legacy TFT",
                        line=dict(color="cyan", width=3, dash="dashdot"),
                        marker=dict(size=10, symbol="star"),
                    )
                )

            # Ensemble prediction (multi-point curve - magenta)
            if show_ensemble and dual and dual.get("ensemble"):
                ens = dual["ensemble"]
                curve = ens.get("prediction_curve", [])
                if curve and len(curve) > 0:
                    curve_times = [last_time]
                    curve_prices = [last_price]
                    for pt in curve:
                        t = last_time + \
                            pd.Timedelta(seconds=pt["horizon_seconds"])
                        curve_times.append(t)
                        curve_prices.append(pt["predicted_price"])
                    fig_ohlc.add_trace(
                        go.Scatter(
                            x=curve_times,
                            y=curve_prices,
                            mode="lines+markers",
                            name="Ensemble Curve",
                            line=dict(color="magenta", width=2, dash="dot"),
                            marker=dict(size=6, symbol="diamond"),
                        )
                    )
                elif ens.get("predicted_price", 0) > 0:
                    pred_time_ens = last_time + pd.Timedelta(minutes=3)
                    fig_ohlc.add_trace(
                        go.Scatter(
                            x=[last_time, pred_time_ens],
                            y=[last_price, ens["predicted_price"]],
                            mode="lines+markers",
                            name="Ensemble",
                            line=dict(color="magenta", width=2, dash="dot"),
                            marker=dict(size=8, symbol="diamond"),
                        )
                    )

            # EMA-smoothed prediction line (green) — smooths noisy predictions
            if show_ema:
                pred_hist_ema = fetch_prediction_history("ensemble", limit=30)
                if pred_hist_ema and len(pred_hist_ema) > 2:
                    ema_times = []
                    ema_raw = []
                    for ph in pred_hist_ema:
                        ts = pd.to_datetime(
                            ph["timestamp"], unit="s", utc=True)
                        ema_times.append(ts)
                        ema_raw.append(ph["predicted_price"])
                    ema_values = _compute_ema(ema_raw, span=5)
                    fig_ohlc.add_trace(
                        go.Scatter(
                            x=ema_times,
                            y=ema_values,
                            mode="lines",
                            name="EMA Prediction",
                            line=dict(color="limegreen", width=2.5),
                        )
                    )

            # Prediction history (orange line - toggled by checkbox)
            if show_pred_history:
                pred_hist = fetch_prediction_history("ensemble", limit=60)
                if pred_hist and len(pred_hist) > 1:
                    hist_times = []
                    hist_prices = []
                    # Get OHLC time range to filter only relevant predictions
                    ohlc_start = df_ohlc['timestamp'].min()
                    for ph in pred_hist:
                        ts = pd.to_datetime(
                            ph['timestamp'], unit='s', utc=True)
                        # Only include predictions within OHLC time range
                        if ts >= ohlc_start:
                            hist_times.append(ts)
                            hist_prices.append(ph['predicted_price'])
                    if len(hist_times) > 1:
                        fig_ohlc.add_trace(go.Scatter(
                            x=hist_times,
                            y=hist_prices,
                            mode='lines+markers',
                            name='Pred. anteriores',
                            line=dict(color='orange', width=2,
                                      dash='solid'),
                            marker=dict(size=4, symbol='circle'),
                            opacity=0.8,
                        ))

            fig_ohlc.update_layout(
                title="Real-time BTC Candles & Dual AI Predictions",
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                height=500,
                uirevision="btc-ohlc-main",
            )
            # Render as native HTML to preserve zoom across auto-refreshes
            _render_plotly_html(fig_ohlc, height=500, key="ohlc_main")
        else:
            st.info("Esperando primer micro-batch de datos OHLC...")

    with accuracy_col:
        # -- Panel: Best Model of the Day --
        st.markdown("### 🏆 Best Model Today")
        comparison = fetch_model_comparison()
        acc = fetch_prediction_accuracy()

        # Determine best model from comparison data
        best_name = "Primary"
        best_acc = 0
        best_color = "cyan"

        if comparison:
            leg_acc = comparison.get("legacy")
            ens_acc = comparison.get("ensemble")
            leg_dir = (
                leg_acc.get("direction_accuracy", 0)
                if leg_acc and leg_acc.get("total_evaluated", 0) > 0
                else 0
            )
            ens_dir = (
                ens_acc.get("direction_accuracy", 0)
                if ens_acc and ens_acc.get("total_evaluated", 0) > 0
                else 0
            )
            if ens_dir >= leg_dir and ens_dir > 0:
                best_name = "Ensemble"
                best_acc = ens_dir
                best_color = "magenta"
            elif leg_dir > 0:
                best_name = "Legacy TFT"
                best_acc = leg_dir
                best_color = "cyan"

        if best_acc == 0 and acc and acc.get("total_evaluated", 0) > 0:
            best_acc = acc.get("direction_accuracy", 0)

        if best_acc > 0:
            fig_acc = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=best_acc,
                    domain={"x": [0, 1], "y": [0, 1]},
                    title={"text": f"{best_name} Direction %"},
                    number={"suffix": "%"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": best_color},
                        "steps": [
                            {"range": [0, 40], "color": "darkred"},
                            {"range": [40, 55], "color": "orange"},
                            {"range": [55, 70], "color": "gold"},
                            {"range": [70, 100], "color": "green"},
                        ],
                    },
                )
            )
            fig_acc.update_layout(
                template="plotly_dark",
                height=200,
                margin=dict(l=20, r=20, t=40, b=20),
                uirevision="accuracy-gauge",
            )
            st.plotly_chart(fig_acc, width="stretch")

        # Dual model comparison table
        if comparison:
            leg_acc = comparison.get("legacy")
            ens_acc = comparison.get("ensemble")

            if leg_acc or ens_acc:
                st.markdown("**Model Comparison**")
                comp_data = []
                if leg_acc and leg_acc.get("total_evaluated", 0) > 0:
                    comp_data.append(
                        {
                            "Model": "Legacy TFT",
                            "Dir %": f"{leg_acc.get('direction_accuracy', 0):.1f}%",
                            "MAE": f"${leg_acc.get('mae', 0):,.0f}",
                            "Evals": leg_acc.get("total_evaluated", 0),
                        }
                    )
                if ens_acc and ens_acc.get("total_evaluated", 0) > 0:
                    comp_data.append(
                        {
                            "Model": "Ensemble",
                            "Dir %": f"{ens_acc.get('direction_accuracy', 0):.1f}%",
                            "MAE": f"${ens_acc.get('mae', 0):,.0f}",
                            "Evals": ens_acc.get("total_evaluated", 0),
                        }
                    )
                if comp_data:
                    st.dataframe(pd.DataFrame(comp_data),
                                 hide_index=True, width="stretch")
        elif acc and acc.get("total_evaluated", 0) > 0:
            st.metric("MAE", f"${acc.get('mae', 0):,.2f}")
            st.metric("Evaluaciones", f"{acc.get('total_evaluated', 0)}")

        if best_acc == 0 and (not acc or acc.get("total_evaluated", 0) == 0):
            st.info("Recopilando datos de precision...")
            st.caption("Las metricas apareceran tras ~2 min de predicciones")


# -- ML Status Sidebar (Dual Model) --
_dual_sidebar = fetch_dual_prediction()
if _dual_sidebar:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 ML Status (Dual Model)")

    # Legacy info
    _leg = _dual_sidebar.get('legacy')
    if _leg and _leg.get('predicted_price', 0) > 0:
        _leg_diff = ((_leg['predicted_price'] - _leg['current_price']) /
                     _leg['current_price']) * 100 if _leg.get('current_price', 0) > 0 else 0
        _leg_icon = "🟢" if _leg_diff > 0 else "🔴"
        st.sidebar.info(f"🧠 Legacy TFT: {_leg_icon} {_leg_diff:+.3f}%")

    # Ensemble info
    _ens = _dual_sidebar.get('ensemble')
    if _ens and _ens.get('predicted_price', 0) > 0:
        _ens_diff = ((_ens['predicted_price'] - _ens['current_price']) /
                     _ens['current_price']) * 100 if _ens.get('current_price', 0) > 0 else 0
        _ens_icon = "🟢" if _ens_diff > 0 else "🔴"
        st.sidebar.success(f"🎯 Ensemble: {_ens_icon} {_ens_diff:+.3f}%")
        # Show ensemble model details
        _md = _ens.get('memory_details', {})
        if isinstance(_md, dict) and 'gb_prob' in _md:
            st.sidebar.caption(
                f"GB:{_md.get('gb_prob', 0):.0%} RF:{_md.get('rf_prob', 0):.0%} LSTM:{_md.get('lstm_prob', 0):.0%}"
            )

    st.sidebar.caption(
        f"Primary: **{_dual_sidebar.get('primary_model', 'N/A')}**")

st.title("🏔️ CryptoLake — Crypto Analytics Dashboard")
st.markdown("---")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "Market Overview",
        "Price Charts",
        "Coin Comparison",
        "Fear & Greed Index",
        "Trading Signals",
        "Logs & System Status",
    ],
)

# Navigation section descriptions
_nav_descriptions = {
    "Market Overview": "📊 Vista general del mercado: precios actuales, predicción AI en tiempo real, candlestick BTC y precisión del modelo.",
    "Price Charts": "📈 Gráficos de velas intradía (OHLC en tiempo real) y gráficos de precio histórico para cada criptomoneda.",
    "Coin Comparison": "⚖️ Compara dos criptomonedas lado a lado: precio normalizado, métricas y volumen.",
    "Fear & Greed Index": "😱 Índice de Miedo y Codicia del mercado cripto con gauge actual y gráfico de barras histórico.",
    "Trading Signals": "📡 Señales combinadas de trading: predicción AI, sentimiento de mercado y fiabilidad del modelo.",
    "Logs & System Status": "🛠️ Estado del sistema, reportes de calidad de datos (DQ) y alertas del sistema con fecha completa.",
}
st.sidebar.caption(_nav_descriptions.get(page, ""))

if page == "Market Overview":
    st.header("📊 Market Overview")
    st.info(
        "📊 **Market Overview** — Vista general del mercado cripto: precios principales, predicción AI del Consejo de Agentes, gráfico de velas BTC en tiempo real con onda de predicción, y panel de precisión del modelo."
    )

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
            st.metric("Fear & Greed", fg_data["value"])
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
                val_pred = (
                    f"${pred['predicted_price']:,.2f}"
                    if pred["predicted_price"] > 0
                    else "Calculando..."
                )
                st.metric("AI Target Price", val_pred)
            with p_col3:
                st.info(f"Market Bias: **{pred['sentiment_bias']}**")

            # -- Layout: Chart + Accuracy (auto-refreshing fragment) --
            realtime_chart_panel()

        st.subheader("🌍 All Assets Market Overview")
        df = pd.DataFrame(overview_data)
        if not df.empty:
            # Asegurar que no haya nulos antes de formatear
            df = df.fillna(0).infer_objects(copy=False)
            # Renombrar columnas para mejor visualización
            df_display = df.rename(
                columns={
                    "coin_id": "Asset",
                    "current_price": "Price (USD)",
                    "price_change_24h_pct": "24h %",
                    "market_cap_usd": "Market Cap",
                    "volume_24h_usd": "Volume 24h",
                }
            )
            # Formatear moneda y porcentajes
            st.dataframe(
                df_display.style.format(
                    {
                        "Price (USD)": "${:,.2f}",
                        "24h %": "{:+.2f}%",
                        "Market Cap": "${:,.0f}",
                        "Volume 24h": "${:,.0f}",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

elif page == "Price Charts":
    st.header("📈 Price Charts")
    st.info(
        "📈 **Price Charts** — Selecciona una criptomoneda para ver su gráfico de velas intradía (OHLC en tiempo real con predicción AI si disponible) y su precio histórico de los últimos 30 días."
    )

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
                df_ohlc["timestamp"] = pd.to_datetime(df_ohlc["timestamp"])

                fig_candlestick = go.Figure(
                    data=[
                        go.Candlestick(
                            x=df_ohlc["timestamp"],
                            open=df_ohlc["open"],
                            high=df_ohlc["high"],
                            low=df_ohlc["low"],
                            close=df_ohlc["close"],
                            name="Real-time",
                        )
                    ]
                )

                # Dual Model Prediction Curves
                if selected_coin == "bitcoin":
                    dual = fetch_dual_prediction()
                    last_time = df_ohlc["timestamp"].iloc[-1]
                    last_price = df_ohlc["close"].iloc[-1]

                    if dual and dual.get("legacy") and dual["legacy"].get("predicted_price", 0) > 0:
                        leg = dual["legacy"]
                        pred_time_leg = last_time + pd.Timedelta(minutes=5)
                        fig_candlestick.add_trace(
                            go.Scatter(
                                x=[last_time, pred_time_leg],
                                y=[last_price, leg["predicted_price"]],
                                mode="lines+markers",
                                name="Legacy TFT",
                                line=dict(color="cyan", width=3,
                                          dash="dashdot"),
                                marker=dict(size=10, symbol="star"),
                            )
                        )

                    if dual and dual.get("ensemble"):
                        ens = dual["ensemble"]
                        curve = ens.get("prediction_curve", [])
                        if curve:
                            ct = [last_time]
                            cp = [last_price]
                            for pt in curve:
                                ct.append(
                                    last_time + pd.Timedelta(seconds=pt["horizon_seconds"]))
                                cp.append(pt["predicted_price"])
                            fig_candlestick.add_trace(
                                go.Scatter(
                                    x=ct,
                                    y=cp,
                                    mode="lines+markers",
                                    name="Ensemble Curve",
                                    line=dict(color="magenta",
                                              width=2, dash="dot"),
                                    marker=dict(size=6, symbol="diamond"),
                                )
                            )
                else:
                    pred = fetch_prediction()
                    if (
                        pred
                        and pred["predicted_price"] > 0
                        and pred.get("coin_id") == selected_coin
                    ):
                        last_time = df_ohlc["timestamp"].iloc[-1]
                        last_price = df_ohlc["close"].iloc[-1]
                        pred_time = last_time + pd.Timedelta(seconds=30)
                        fig_candlestick.add_trace(
                            go.Scatter(
                                x=[last_time, pred_time],
                                y=[last_price, pred["predicted_price"]],
                                mode="lines+markers",
                                name="AI Prediction",
                                line=dict(color="cyan", width=3,
                                          dash="dashdot"),
                                marker=dict(size=10, symbol="star"),
                            )
                        )

                fig_candlestick.update_layout(
                    template="plotly_dark",
                    xaxis_rangeslider_visible=True,
                    height=500,
                    uirevision="detail-candlestick",
                )
                st.plotly_chart(fig_candlestick,
                                width="stretch", key="detail_candle")
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
                fig_line.update_layout(
                    template="plotly_dark", uirevision="history-line")
                st.plotly_chart(fig_line, width="stretch")

                # 3. Data Table
                st.subheader("Historical Data Table")
                st.dataframe(df_hist, width="stretch", hide_index=True)

elif page == "Coin Comparison":
    st.header("⚖️ Coin Comparison")
    st.info(
        "⚖️ **Coin Comparison** — Compara dos criptomonedas con precio normalizado (base 100), métricas lado a lado y gráfico de volumen comparativo."
    )

    overview_data = fetch_market_overview()
    if not overview_data or len(overview_data) < 2:
        st.warning("Need at least 2 coins in the lake. Run ingestion first.")
    else:
        coins = [c["coin_id"] for c in overview_data]
        comp_col1, comp_col2 = st.columns(2)
        with comp_col1:
            coin_a = st.selectbox("Coin A", coins, index=0)
        with comp_col2:
            coin_b = st.selectbox(
                "Coin B", coins, index=min(1, len(coins) - 1))

        if coin_a and coin_b:
            hist_a = fetch_price_history(coin_a)
            hist_b = fetch_price_history(coin_b)

            if hist_a and hist_b:
                df_a = pd.DataFrame(hist_a)
                df_b = pd.DataFrame(hist_b)
                df_a["price_date"] = pd.to_datetime(df_a["price_date"])
                df_b["price_date"] = pd.to_datetime(df_b["price_date"])

                # Normalized comparison (base 100)
                st.subheader("📊 Normalized Price Comparison (Base = 100)")
                if len(df_a) > 0 and len(df_b) > 0:
                    df_a["normalized"] = (
                        df_a["price_usd"] / df_a["price_usd"].iloc[0]) * 100
                    df_b["normalized"] = (
                        df_b["price_usd"] / df_b["price_usd"].iloc[0]) * 100

                    fig_comp = go.Figure()
                    fig_comp.add_trace(
                        go.Scatter(
                            x=df_a["price_date"],
                            y=df_a["normalized"],
                            name=coin_a.upper(),
                            mode="lines",
                            line=dict(color="#FF6B35", width=2),
                        )
                    )
                    fig_comp.add_trace(
                        go.Scatter(
                            x=df_b["price_date"],
                            y=df_b["normalized"],
                            name=coin_b.upper(),
                            mode="lines",
                            line=dict(color="#00D4FF", width=2),
                        )
                    )
                    fig_comp.update_layout(
                        template="plotly_dark",
                        yaxis_title="Normalized Price (Base 100)",
                        height=450,
                        uirevision="comparison-chart",
                    )
                    st.plotly_chart(fig_comp, width="stretch",
                                    key="comparison_chart")

                # Side-by-side metrics
                st.subheader("📋 Comparative Metrics")
                met_a = next(
                    (c for c in overview_data if c["coin_id"] == coin_a), {})
                met_b = next(
                    (c for c in overview_data if c["coin_id"] == coin_b), {})

                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    st.markdown("**Metric**")
                    st.write("Current Price")
                    st.write("24h Change")
                    st.write("Market Cap")
                    st.write("Volume 24h")
                with mc2:
                    st.markdown(f"**{coin_a.upper()}**")
                    st.write(f"${met_a.get('current_price', 0):,.2f}")
                    st.write(f"{met_a.get('price_change_24h_pct', 0):+.2f}%")
                    st.write(f"${met_a.get('market_cap_usd', 0):,.0f}")
                    st.write(f"${met_a.get('volume_24h_usd', 0):,.0f}")
                with mc3:
                    st.markdown(f"**{coin_b.upper()}**")
                    st.write(f"${met_b.get('current_price', 0):,.2f}")
                    st.write(f"{met_b.get('price_change_24h_pct', 0):+.2f}%")
                    st.write(f"${met_b.get('market_cap_usd', 0):,.0f}")
                    st.write(f"${met_b.get('volume_24h_usd', 0):,.0f}")

                # Volume comparison bar chart
                st.subheader("📊 Volume Comparison")
                if len(df_a) > 0 and len(df_b) > 0:
                    vol_a_col = "volume_24h_usd" if "volume_24h_usd" in df_a.columns else None
                    vol_b_col = "volume_24h_usd" if "volume_24h_usd" in df_b.columns else None
                    if vol_a_col and vol_b_col:
                        fig_vol = go.Figure()
                        fig_vol.add_trace(
                            go.Bar(
                                x=df_a["price_date"],
                                y=df_a[vol_a_col],
                                name=coin_a.upper(),
                                marker_color="#FF6B35",
                                opacity=0.7,
                            )
                        )
                        fig_vol.add_trace(
                            go.Bar(
                                x=df_b["price_date"],
                                y=df_b[vol_b_col],
                                name=coin_b.upper(),
                                marker_color="#00D4FF",
                                opacity=0.7,
                            )
                        )
                        fig_vol.update_layout(
                            template="plotly_dark",
                            barmode="group",
                            yaxis_title="Volume (USD)",
                            height=350,
                            uirevision="volume-comparison",
                        )
                        st.plotly_chart(fig_vol, width="stretch")
            else:
                st.info("Esperando datos históricos para ambas monedas...")

elif page == "Trading Signals":
    st.header("📡 Trading Signals")
    st.info(
        "📡 **Trading Signals** — Señales combinadas de trading basadas en predicción AI, sentimiento de mercado (Fear & Greed) y fiabilidad del modelo. Incluye matriz de señales para cada asset."
    )

    overview_data = fetch_market_overview()
    pred = fetch_prediction()
    fg = fetch_fear_greed()
    acc = fetch_prediction_accuracy()

    # Signal summary cards
    sig_col1, sig_col2, sig_col3 = st.columns(3)

    with sig_col1:
        st.markdown("### 🤖 AI Prediction")
        dual = fetch_dual_prediction()
        if dual:
            for label, key, _color_tag in [
                ("Legacy TFT", "legacy", "cyan"),
                ("Ensemble", "ensemble", "magenta"),
            ]:
                m = dual.get(key)
                if m and m.get("predicted_price", 0) > 0:
                    dp = (
                        ((m["predicted_price"] - m["current_price"]) /
                         m["current_price"]) * 100
                        if m.get("current_price", 0) > 0
                        else 0
                    )
                    icon = "🟢" if dp > 0 else "🔴"
                    st.metric(
                        f"{label}", f"${m['predicted_price']:,.2f}", delta=f"{dp:+.2f}%")
                    st.caption(f"{icon} {m.get('sentiment_bias', 'N/A')}")
            if dual.get("primary_model"):
                st.caption(f"Primary: **{dual['primary_model']}**")
        elif pred and pred.get("timestamp", 0) > 0:
            diff_pct = (
                ((pred["predicted_price"] - pred["current_price"]) /
                 pred["current_price"]) * 100
                if pred["current_price"] > 0
                else 0
            )
            color = "🟢" if diff_pct > 0 else "🔴"
            st.metric(
                "AI Target", f"${pred['predicted_price']:,.2f}", delta=f"{diff_pct:+.2f}%")
            st.write(f"{color} Bias: **{pred['sentiment_bias']}**")
        else:
            st.info("Esperando primera prediccion...")

    with sig_col2:
        st.markdown("### 😱 Market Sentiment")
        if fg:
            val = fg.get("value", 50)
            cls = fg.get("classification", "Neutral")
            if val < 25:
                signal = "🟢 POTENTIAL BUY (Extreme Fear)"
            elif val < 45:
                signal = "🟡 WATCH (Fear)"
            elif val < 55:
                signal = "⚪ NEUTRAL"
            elif val < 75:
                signal = "🟡 CAUTION (Greed)"
            else:
                signal = "🔴 POTENTIAL SELL (Extreme Greed)"
            st.metric("Fear & Greed", val)
            st.write(f"**{cls}**")
            st.write(signal)
        else:
            st.info("Sin datos de sentimiento")

    with sig_col3:
        st.markdown("### 🎯 Model Reliability")
        comp = fetch_model_comparison()
        if comp and (comp.get("legacy") or comp.get("ensemble")):
            for lbl, mk in [("Legacy", "legacy"), ("Ensemble", "ensemble")]:
                ma = comp.get(mk)
                if ma and ma.get("total_evaluated", 0) > 0:
                    da = ma.get("direction_accuracy", 0)
                    mp = ma.get("mape", 0)
                    rel = "🟢" if da >= 60 else ("🟡" if da >= 50 else "🔴")
                    st.metric(f"{lbl} Dir %", f"{da:.1f}%")
                    st.caption(f"MAE ${ma.get('mae', 0):,.0f} | {rel}")
        elif acc and acc.get("total_evaluated", 0) > 0:
            dir_acc = acc.get("direction_accuracy", 0)
            mape = acc.get("mape", 0)
            if dir_acc >= 60 and mape < 2:
                reliability = "🟢 HIGH"
            elif dir_acc >= 50 and mape < 5:
                reliability = "🟡 MEDIUM"
            else:
                reliability = "🔴 LOW"
            st.metric("Direction Accuracy", f"{dir_acc:.1f}%")
            st.metric("MAPE", f"{mape:.2f}%")
            st.write(f"Reliability: **{reliability}**")
        else:
            st.info("Recopilando metricas...")

    # Combined signal matrix
    st.markdown("---")
    st.subheader("📋 Combined Signal Matrix")
    if overview_data:
        signal_data = []
        for coin in overview_data:
            cid = coin["coin_id"]
            price = coin.get("current_price", 0)
            change = coin.get("price_change_24h_pct", 0)

            # Technical signal based on price change
            if change is None:
                change = 0
            if change < -5:
                tech_sig = "🔴 OVERSOLD"
            elif change < -2:
                tech_sig = "🟡 WEAK"
            elif change > 5:
                tech_sig = "🔴 OVERBOUGHT"
            elif change > 2:
                tech_sig = "🟢 STRONG"
            else:
                tech_sig = "⚪ NEUTRAL"

            # Sentiment overlay
            fg_val = fg.get("value", 50) if fg else 50
            if fg_val < 30 and change < -2:
                combined = "🟢 BUY SIGNAL"
            elif fg_val > 70 and change > 2:
                combined = "🔴 SELL SIGNAL"
            else:
                combined = "⚪ HOLD"

            signal_data.append(
                {
                    "Asset": cid.upper(),
                    "Price": f"${price:,.2f}",
                    "24h %": f"{change:+.2f}%",
                    "Technical": tech_sig,
                    "Sentiment": f"F&G {fg_val}",
                    "Combined": combined,
                }
            )

        st.dataframe(pd.DataFrame(signal_data),
                     hide_index=True, width="stretch")

elif page == "Logs & System Status":
    st.header("🛠️ System Status & Data Quality")
    st.info(
        "🛠️ **Logs & System Status** — Reportes de calidad de datos (Data Quality), alertas del sistema tipo Slack con fecha y hora completa, e información del hardware."
    )

    col_dq, col_alerts = st.columns([1, 2])

    with col_dq:
        st.subheader("✅ Data Quality (GX)")
        dq_data = fetch_dq_reports()
        if dq_data:
            for report in dq_data:
                color = "green" if report["success_rate"] > 0.9 else "orange"
                st.markdown(
                    f"""
                <div style="border-left: 5px solid {color}; padding-left: 10px; margin-bottom: 10px;">
                    <strong>Table: {report["table_name"]}</strong><br/>
                    Success Rate: {report["success_rate"] * 100:.1f}%<br/>
                    <small>Checks: {report["successful_expectations"]}/{report["total_expectations"]}</small>
                </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No hay reportes de DQ aún.")

    with col_alerts:
        st.subheader("🚨 System Alertas (Slack-style)")
        alerts = fetch_system_alerts()
        if isinstance(alerts, list) and alerts:
            for alert in alerts:
                if not isinstance(alert, dict):
                    continue
                lvl = alert.get("level", "INFO")
                lvl_emoji = "🔴" if lvl == "CRITICAL" else "⚠️"
                ts = alert.get("timestamp", time.time())
                ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
                st.markdown(f"""
                **{lvl_emoji} {lvl}** - {ts_str}
                `DAG: {alert.get("dag_id", "N/A")} | Task: {alert.get("task_id", "N/A")}`
                > {alert.get("message", "No message")}
                ---
                """)
        else:
            st.success("No hay alertas críticas en el sistema. Todo ok. ✅")

    st.markdown("---")
    st.subheader("⚙️ Hardware Accelerator")
    st.info(
        "Detected GPU: **NVIDIA Quadro K4200 (Kepler)** | CPU: **Intel Xeon E5-1620 v3**")
    st.caption(
        "Los agentes duales están optimizados para utilizar aceleración CUDA si está disponible."
    )

elif page == "Fear & Greed Index":
    st.header("😱 Fear & Greed Index")
    st.info(
        "😱 **Fear & Greed Index** — Indicador de sentimiento del mercado cripto. El gauge muestra el valor actual y el gráfico de barras histórico ayuda a entender la tendencia que ha llevado al índice a su estado actual."
    )
    fg_data = fetch_fear_greed()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Current Value", fg_data["value"])
        st.subheader(f"Status: {fg_data['classification']}")

    with col2:
        # Gauge chart for Fear & Greed
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=fg_data["value"],
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Market Sentiment"},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "white"},
                    "steps": [
                        {"range": [0, 25], "color": "darkred"},
                        {"range": [25, 45], "color": "red"},
                        {"range": [45, 55], "color": "gray"},
                        {"range": [55, 75], "color": "lightgreen"},
                        {"range": [75, 100], "color": "green"},
                    ],
                },
            )
        )
        fig_gauge.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_gauge, width="stretch")

    # ── Historical Fear & Greed Bar Chart ──
    st.markdown("---")
    st.subheader("📊 Histórico Fear & Greed Index")
    st.caption(
        "El gráfico de barras muestra la evolución del índice a lo largo del tiempo, permitiendo ver las tendencias de sentimiento que explican el valor actual."
    )

    fg_history = fetch_fear_greed_history()
    if fg_history:
        df_fg = pd.DataFrame(fg_history)

        # Color-code bars based on value ranges
        def fg_color(val):
            if val < 25:
                return "darkred"
            elif val < 45:
                return "red"
            elif val < 55:
                return "gray"
            elif val < 75:
                return "lightgreen"
            else:
                return "green"

        df_fg["color"] = df_fg["value"].apply(fg_color)

        fig_fg_hist = go.Figure()
        fig_fg_hist.add_trace(
            go.Bar(
                x=df_fg["date_str"],
                y=df_fg["value"],
                marker_color=df_fg["color"],
                text=df_fg["classification"],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Value: %{y}<br>%{text}<extra></extra>",
                name="Fear & Greed",
            )
        )

        # Add reference lines
        fig_fg_hist.add_hline(
            y=25,
            line_dash="dash",
            line_color="red",
            annotation_text="Extreme Fear",
            annotation_position="bottom right",
        )
        fig_fg_hist.add_hline(
            y=75,
            line_dash="dash",
            line_color="green",
            annotation_text="Extreme Greed",
            annotation_position="top right",
        )
        fig_fg_hist.add_hline(
            y=50,
            line_dash="dot",
            line_color="white",
            annotation_text="Neutral",
            annotation_position="bottom right",
            opacity=0.5,
        )

        fig_fg_hist.update_layout(
            template="plotly_dark",
            yaxis_title="Fear & Greed Value",
            xaxis_title="Date",
            yaxis=dict(range=[0, 105]),
            height=450,
            showlegend=False,
        )
        st.plotly_chart(fig_fg_hist, width="stretch")
    else:
        st.warning(
            "No hay datos históricos de Fear & Greed disponibles aún. Ejecuta la ingesta primero."
        )

    st.info(
        "The Fear & Greed Index provides a sentiment score from 0 (Extreme Fear) to 100 (Extreme Greed)."
    )
    st.markdown("""
    - **0-25**: Extreme Fear (Opportunity?)
    - **25-45**: Fear
    - **45-55**: Neutral
    - **55-75**: Greed
    - **75-100**: Extreme Greed (Risk?)
    """)
