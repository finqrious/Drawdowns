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
        
        # Process the data
        df = stock_data[['Close']].copy()
        close_series = df['Close'].squeeze()
        df['ATH'] = close_series.cummax()
        df['Drawdown'] = (close_series - df['ATH']) / df['ATH']
        
        # Define drawdown threshold
        threshold = -0.25
        df['In_Drawdown'] = df['Drawdown'] <= threshold
        
        # Find drawdown periods
        df['Drawdown_Start'] = df['In_Drawdown'] & ~df['In_Drawdown'].shift(1, fill_value=False)
        df['Drawdown_End'] = ~df['In_Drawdown'] & df['In_Drawdown'].shift(1, fill_value=False)
        
        # Extract drawdown periods
        drawdown_periods = []
        start_idx = None
        
        # Using boolean indexing instead of iterating
        drawdown_starts = df.index[df['Drawdown_Start']].tolist()
        drawdown_ends = df.index[df['Drawdown_End']].tolist()
        
        # Handle the case where a drawdown is ongoing
        if len(drawdown_starts) > len(drawdown_ends):
            # Find where the last drawdown starts
            last_drawdown_start = drawdown_starts[-1]
            # Add the last date as the end of this drawdown
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
            # Create a polygon shape for the drawdown area
            fig.add_shape(
                type="rect",
                x0=start, x1=end,
                y0=df.loc[start:end, 'Close'].min() * 0.95,  # Add some padding
                y1=df.loc[start:end, 'ATH'].max() * 1.05,  # Add some padding
                fillcolor="rgba(255, 0, 0, 0.2)",
                line=dict(width=0),
                layer="below"
            )
            
            # Add a trace for the legend (invisible but needed for the legend)
            if i == 0:  # Only add to legend once
                fig.add_trace(
                    go.Scatter(
                        x=[None], y=[None],
                        mode='lines',
                        line=dict(color="rgba(255, 0, 0, 0.2)", width=10),
                        name="Drawdown Period",
                        showlegend=True
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
