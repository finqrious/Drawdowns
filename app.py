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
        drawdown_starts = df.index[df['Drawdown_Start']].tolist()
        drawdown_ends = df.index[df['Drawdown_End']].tolist()
        
        # Handle the case where a drawdown is ongoing
        if len(drawdown_starts) > len(drawdown_ends):
            drawdown_ends.append(df.index[-1])
        
        # Create two separate figures
        # Figure 1: Price and ATH
        fig1 = go.Figure()
        
        # Add price and ATH
        fig1.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price', line=dict(color='blue')))
        fig1.add_trace(go.Scatter(x=df.index, y=df['ATH'], mode='lines', name='All-Time High', line=dict(color='green', dash='dash')))
        
        # Highlight drawdown periods in the price chart
        for i, (start, end) in enumerate(zip(drawdown_starts, drawdown_ends)):
            # Add shaded area for drawdown period
            fig1.add_shape(
                type="rect",
                x0=start, x1=end,
                y0=0,  # From bottom of chart
                y1=1,   # To top of chart
                xref="x", yref="paper",
                fillcolor="rgba(255, 0, 0, 0.1)",
                line=dict(width=0),
                layer="below"
            )
        
        # Add a trace for the legend (invisible but needed for the legend)
        fig1.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='lines',
                line=dict(color="rgba(255, 0, 0, 0.2)", width=10),
                name="Drawdown Period",
                showlegend=True
            )
        )
        
        # Update layout for figure 1
        fig1.update_layout(
            title=f"{ticker} Price and All-Time High",
            xaxis_title="Date",
            yaxis_title="Price",
            legend_title="Legend",
            template="plotly_white",
            hovermode="x unified"
        )
        
        # Figure 2: Drawdowns
        fig2 = go.Figure()
        
        # Add drawdown percentage
        fig2.add_trace(go.Scatter(x=df.index, y=df['Drawdown'] * 100, mode='lines', name='Drawdown (%)', line=dict(color='red')))
        
        # Add threshold line
        fig2.add_trace(go.Scatter(x=df.index, y=[threshold * 100] * len(df), mode='lines', name='Threshold (-25%)', 
                      line=dict(color='red', dash='dash')))
        
        # Highlight drawdown periods in the drawdown chart
        for i, (start, end) in enumerate(zip(drawdown_starts, drawdown_ends)):
            # Add shaded area for drawdown period
            fig2.add_shape(
                type="rect",
                x0=start, x1=end,
                y0=0,  # From bottom of chart
                y1=1,   # To top of chart
                xref="x", yref="paper",
                fillcolor="rgba(255, 0, 0, 0.1)",
                line=dict(width=0),
                layer="below"
            )
        
        # Update layout for figure 2
        fig2.update_layout(
            title=f"{ticker} Drawdowns",
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            legend_title="Legend",
            template="plotly_white",
            hovermode="x unified"
        )
        
        # Display both charts
        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
        
        # Display drawdown statistics
        if drawdown_starts:
            st.subheader("Major Drawdown Periods (Below -25%)")
            drawdown_stats = []
            
            for i, (start, end) in enumerate(zip(drawdown_starts, drawdown_ends)):
                period_df = df.loc[start:end]
                max_drawdown = period_df['Drawdown'].min() * 100
                duration = (end - start).days
                
                recovery = "Ongoing" if end == df.index[-1] and period_df.iloc[-1]['Drawdown'] <= threshold else f"{duration} days"
                
                drawdown_stats.append({
                    "Start": start.strftime('%Y-%m-%d'),
                    "End": end.strftime('%Y-%m-%d') if end != df.index[-1] or period_df.iloc[-1]['Drawdown'] > threshold else "Ongoing",
                    "Max Drawdown": f"{max_drawdown:.2f}%",
                    "Duration": recovery
                })
            
            st.table(pd.DataFrame(drawdown_stats))
