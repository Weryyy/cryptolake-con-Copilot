"""
CryptoLake Dashboard — Streamlit App

Interactive dashboard for crypto market analytics.
"""
import streamlit as st

st.set_page_config(
    page_title="CryptoLake Dashboard",
    page_icon="🏔️",
    layout="wide",
)

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
    st.info("Connect to the CryptoLake API to see live market data.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Bitcoin", "$67,432", "+2.3%")
    with col2:
        st.metric("Ethereum", "$3,501", "+1.8%")
    with col3:
        st.metric("Solana", "$150", "+5.2%")
    with col4:
        st.metric("Fear & Greed", "72", "Greed")

elif page == "Price Charts":
    st.header("📈 Price Charts")
    st.info("Select a cryptocurrency to view historical price data.")

elif page == "Fear & Greed Index":
    st.header("😱 Fear & Greed Index")
    st.info("Historical Fear & Greed Index data.")
