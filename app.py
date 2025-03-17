import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime
from fuzzywuzzy import process  # For smart ticker search

# Set Streamlit page config
st.set_page_config(page_title="Stock Drawdown Analysis", layout="wide")

# Load all available Indian stock & index tickers dynamically
@st.cache_data
def fetch_all_tickers():
    """Fetch all NSE & BSE tickers dynamically from Yahoo Finance"""
    try:
        nse_tickers = yf.Ticker("^NSEI").history(period="1d")  # Fetch Nifty tickers
        bse_tickers = yf.Ticker("^BSESN").history(period="1d")  # Fetch Sensex tickers
        
        # Dummy list for now (replace with API call to NSE/BSE tickers)
        stock_tickers = [
            "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", 
            "NIFTY50", "SENSEX", "MIDCAP.NS", "SMALLCAP.NS", "BANKNIFTY"
        ]
        return stock_tickers
    except Exception as e:
        st.error(f"Error fetching tickers: {e}")
        return []

# Get tickers
all_tickers = fetch_all_tickers()

# **Ticker Search Function**
def suggest_ticker(query):
    """Return best matching tickers from all_tickers list"""
    if not query:
        return []
    return process.extract(query.upper(), all_tickers, limit=5)

# **UI Elements**
st.title("📉 Stock Drawdown Analysis (India)")

# **Ticker Input with Smart Suggestions**
query = st.text_input("🔍 Enter Stock/Index Name (3+ chars for suggestions):").strip()

if query and len(query) >= 3:
    suggestions = suggest_ticker(query)
    if suggestions:
        selected_ticker = st.selectbox("🎯 Did you mean?", [s[0] for s in suggestions])
    else:
        st.error("⚠ No matching ticker found! Try again.")
else:
    selected_ticker = None

if selected_ticker:
    ticker = selected_ticker
    st.subheader(f"📊 Analyzing: {ticker}")

    # **Download Stock Data**
    with st.spinner(f"Fetching {ticker} data..."):
        stock_data = yf.download(ticker, period="max")

    if stock_data.empty:
        st.error("⚠ No data found for this ticker. Please try another one.")
    else:
        # **Create Drawdown DataFrame**
        df = stock_data[['Close']].copy()
        df['ATH'] = df['Close'].cummax()
        df['Drawdown'] = (df['Close'] - df['ATH']) / df['ATH']
        threshold = 0.25
        df['In_Drawdown'] = df['Drawdown'] <= -threshold
        df['Drawdown_Start'] = (df['In_Drawdown'] != df['In_Drawdown'].shift(1)) & df['In_Drawdown']
        df['Drawdown_End'] = (df['In_Drawdown'] != df['In_Drawdown'].shift(-1)) & df['In_Drawdown']

        drawdown_starts = df.index[df['Drawdown_Start']].tolist()
        drawdown_ends = df.index[df['Drawdown_End']].tolist()
        if len(drawdown_starts) > len(drawdown_ends):
            drawdown_ends.append(df.index[-1])

        # **Drawdown Summary Table**
        summary_data = []
        for i in range(min(len(drawdown_starts), len(drawdown_ends))):
            start_date = drawdown_starts[i]
            end_date = drawdown_ends[i]
            period_data = df.loc[start_date:end_date]
            max_drawdown = period_data['Drawdown'].min()
            duration = len(period_data)

            summary_data.append({
                'Start Date': start_date,
                'End Date': end_date,
                'Max Drawdown': f"{max_drawdown*100:.2f}%",
                'Duration (Days)': duration
            })

        summary_df = pd.DataFrame(summary_data)
        st.subheader("📉 Drawdown Summary")
        st.dataframe(summary_df)

        # **Plot Charts**
        st.subheader("📈 Price & Drawdown Analysis")

        fig, axes = plt.subplots(2, 1, figsize=(12, 8))

        # **Price Chart**
        axes[0].plot(df.index, df['Close'], label="Close Price", color="blue")
        axes[0].plot(df.index, df['ATH'], label="All-Time High", color="green", linestyle="--")
        for i in range(min(len(drawdown_starts), len(drawdown_ends))):
            axes[0].axvspan(drawdown_starts[i], drawdown_ends[i], color="red", alpha=0.2)
        axes[0].set_title(f"{ticker} Price & ATH")
        axes[0].legend()
        axes[0].grid(True)

        # **Drawdown Chart**
        axes[1].plot(df.index, df['Drawdown'] * 100, color="blue")
        axes[1].axhline(y=-threshold * 100, color="red", linestyle="--", label=f"Drawdown Threshold (-{threshold*100:.0f}%)")
        axes[1].fill_between(df.index, df['Drawdown'] * 100, 0, where=(df['Drawdown'] <= -threshold), color="red", alpha=0.3)
        axes[1].set_title(f"{ticker} Drawdowns from ATH")
        axes[1].set_ylabel("Drawdown (%)")
        axes[1].legend()
        axes[1].grid(True)

        plt.tight_layout()
        st.pyplot(fig)
