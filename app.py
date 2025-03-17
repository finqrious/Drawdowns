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
        
        # Handle the case where drawdown is ongoing
        if len(drawdown_starts) > len(drawdown_ends):
            drawdown_ends.append(df.index[-1])
            
        # Create price chart
        fig1 = go.Figure()
        
        # Add price and ATH to price chart
        fig1.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price', line=dict(color='blue')))
        fig1.add_trace(go.Scatter(x=df.index, y=df['ATH'], mode='lines', name='All-Time High', line=dict(color='green', dash='dash')))
        
        # Add shaded regions for drawdown periods
        for i, (start, end) in enumerate(zip(drawdown_starts, drawdown_ends)):
            fig1.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                fillcolor="rgba(255, 0, 0, 0.1)",
                line=dict(width=0),
                layer="below"
            )
            
        # Add an invisible trace for legend
        fig1.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='lines',
            line=dict(width=10, color='rgba(255, 0, 0, 0.1)'),
            name='Drawdown Period'
        ))
        
        # Update layout for price chart
        fig1.update_layout(
            title=f"{ticker} Price and All-Time High",
            xaxis_title="Date",
            yaxis_title="Price",
            legend_title="Legend",
            template="plotly_white",
            hovermode="x unified"
        )
        
        # Create drawdown chart
        fig2 = go.Figure()
        
        # Add drawdown percentage
        fig2.add_trace(go.Scatter(
            x=df.index, 
            y=df['Drawdown'] * 100, 
            mode='lines', 
            name='Drawdown (%)', 
            line=dict(color='red')
        ))
        
        # Add threshold line
        fig2.add_trace(go.Scatter(
            x=df.index, 
            y=[threshold * 100] * len(df), 
            mode='lines', 
            name='Threshold (-25%)', 
            line=dict(color='red', dash='dash')
        ))
        
        # Add shaded regions for drawdown periods (same as in price chart)
        for i, (start, end) in enumerate(zip(drawdown_starts, drawdown_ends)):
            fig2.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                fillcolor="rgba(255, 0, 0, 0.1)",
                line=dict(width=0),
                layer="below"
            )
        
        # Update layout for drawdown chart
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
        
        # Display drawdown statistics in a simplified way
        if drawdown_starts:
            st.subheader("Major Drawdown Periods (Below -25%)")
            
            # Create a list to store drawdown statistics
            drawdown_stats = []
            
            for i, (start, end) in enumerate(zip(drawdown_starts, drawdown_ends)):
                # Calculate duration in days
                duration = (end - start).days
                
                # Find the maximum drawdown in this period
                period_mask = (df.index >= start) & (df.index <= end)
                max_drawdown = df.loc[period_mask, 'Drawdown'].min() * 100
                
                # Determine if the drawdown is ongoing
                is_ongoing = end == df.index[-1] and df.loc[end, 'In_Drawdown']
                
                # Add to statistics
                drawdown_stats.append({
                    "Start Date": start.strftime('%Y-%m-%d'),
                    "End Date": "Ongoing" if is_ongoing else end.strftime('%Y-%m-%d'),
                    "Max Drawdown": f"{max_drawdown:.2f}%",
                    "Duration": f"{duration} days"
                })
            
            # Display statistics as a table
            st.table(pd.DataFrame(drawdown_stats))
