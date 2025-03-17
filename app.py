import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

from datetime import datetime

# Expanded dictionary mapping for Indian indices
index_mapping = {
    "NIFTY50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "BSE SENSEX": "^BSESN"
}

st.title("Indian Stock/Index Drawdown Analysis")

user_input = st.text_input("Enter Ticker Name:", "").strip().upper()

if user_input:
    ticker = index_mapping.get(user_input, user_input + ".NS")
    
    st.write(f"**Using Ticker:** {ticker}")
    
    with st.spinner("Downloading data..."):
        stock_data = yf.download(ticker, period="max")
    
    if stock_data.empty:
        st.error("Error: Invalid ticker or no data available.")
    else:
        st.success(f"Downloaded {len(stock_data)} rows of data.")
        
        df = stock_data[['Close']].copy()
        close_series = df['Close'].squeeze()
        df['ATH'] = close_series.cummax()
        df['Drawdown'] = (close_series - df['ATH']) / df['ATH']
        
        threshold = -0.25
        df['In_Drawdown'] = df['Drawdown'] <= threshold
        df['Drawdown_Start'] = df['In_Drawdown'] & ~df['In_Drawdown'].shift(1, fill_value=False)
        df['Drawdown_End'] = ~df['In_Drawdown'] & df['In_Drawdown'].shift(-1, fill_value=False)
        
        drawdown_starts = df.index[df['Drawdown_Start']].tolist()
        drawdown_ends = df.index[df['Drawdown_End']].tolist()
        
        if len(drawdown_starts) > len(drawdown_ends):
            drawdown_ends.append(df.index[-1])
        
        fig = go.Figure()
        
        # Price and ATH plot
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df.index, y=df['ATH'], mode='lines', name='All-Time High', line=dict(color='green', dash='dash')))
        
        # Drawdown area
        for start, end in zip(drawdown_starts, drawdown_ends):
            fig.add_trace(go.Scatter(x=[start, end, end, start, start],
                                     y=[df.loc[start, 'Close'], df.loc[end, 'Close'], df.loc[end, 'ATH'], df.loc[start, 'ATH'], df.loc[start, 'Close']],
                                     fill='toself',
                                     fillcolor='rgba(255, 0, 0, 0.2)',
                                     line=dict(width=0),
                                     name='Drawdown Area'))
        
        # Drawdown plot
        fig.add_trace(go.Scatter(x=df.index, y=df['Drawdown'] * 100, mode='lines', name='Drawdown (%)', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=df.index, y=[threshold * 100] * len(df), mode='lines', name='Threshold (-25%)', line=dict(color='red', dash='dash')))
        
        fig.update_layout(title=f"{ticker} Price, ATH & Drawdowns",
                          xaxis_title="Date",
                          yaxis_title="Price / Drawdown (%)",
                          legend_title="Legend",
                          template="plotly_white")
        
        st.plotly_chart(fig)
