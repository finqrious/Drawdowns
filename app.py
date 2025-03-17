import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
        df['Drawdown_End'] = ~df['In_Drawdown'] & df['In_Drawdown'].shift(1, fill_value=False)
        
        drawdown_starts = df.index[df['Drawdown_Start']].tolist()
        drawdown_ends = []
        
        # Find end dates for each drawdown period
        current_start = None
        for i, row in df.iterrows():
            if row['Drawdown_Start']:
                current_start = i
            elif current_start is not None and not row['In_Drawdown']:
                drawdown_ends.append(i)
                current_start = None
        
        # If a drawdown period hasn't ended yet
        if len(drawdown_starts) > len(drawdown_ends):
            drawdown_ends.append(df.index[-1])
        
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add price and ATH to primary y-axis
        fig.add_trace(
            go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price', line=dict(color='blue')),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['ATH'], mode='lines', name='All-Time High', line=dict(color='green', dash='dash')),
            secondary_y=False
        )
        
        # Highlight drawdown periods
        for i, (start, end) in enumerate(zip(drawdown_starts, drawdown_ends)):
            mask = (df.index >= start) & (df.index <= end)
            period_df = df[mask]
            
            # Shade area for drawdown period
            fig.add_trace(
                go.Scatter(
                    x=period_df.index,
                    y=period_df['Close'],
                    mode='lines',
                    line=dict(width=0),
                    showlegend=i==0,
                    name='Drawdown Area',
                    fillcolor='rgba(255, 0, 0, 0.2)',
                    fill='tozeroy'
                ),
                secondary_y=False
            )
        
        # Add drawdown percentage to secondary y-axis
        fig.add_trace(
            go.Scatter(x=df.index, y=df['Drawdown'] * 100, mode='lines', name='Drawdown (%)', line=dict(color='red')),
            secondary_y=True
        )
        
        # Add threshold line to secondary y-axis
        fig.add_trace(
            go.Scatter(x=df.index, y=[threshold * 100] * len(df), mode='lines', name='Threshold (-25%)', 
                      line=dict(color='red', dash='dash')),
            secondary_y=True
        )
        
        # Update layout and axes titles
        fig.update_layout(
            title=f"{ticker} Price, ATH & Drawdowns",
            legend_title="Legend",
            template="plotly_white",
            hovermode="x unified"
        )
        
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Price", secondary_y=False)
        fig.update_yaxes(title_text="Drawdown (%)", secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)
