import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
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
        
        # Simple way to get drawdown periods
        drawdown_periods = []
        in_drawdown = False
        start_date = None
        
        for date, value in df['In_Drawdown'].items():
            if value and not in_drawdown:
                # Start of a drawdown period
                in_drawdown = True
                start_date = date
            elif not value and in_drawdown:
                # End of a drawdown period
                in_drawdown = False
                drawdown_periods.append((start_date, date))
                start_date = None
        
        # If still in drawdown at the end
        if in_drawdown:
            drawdown_periods.append((start_date, df.index[-1]))
        
        # Create price chart with Matplotlib
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        
        # Plot price and ATH
        ax1.plot(df.index, df['Close'], label='Close Price', color='blue')
        ax1.plot(df.index, df['ATH'], label='All-Time High', color='green', linestyle='--')
        
        # Highlight drawdown periods
        for start, end in drawdown_periods:
            ax1.axvspan(start, end, alpha=0.2, color='red')
        
        # Set labels and title
        ax1.set_title(f"{ticker} Price and All-Time High")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Price")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Adjust layout
        plt.tight_layout()
        
        # Display the Matplotlib chart
        st.pyplot(fig1)
        
        # Create drawdown chart with Plotly
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
        
        # Add shaded regions for drawdown periods
        for start, end in drawdown_periods:
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
        
        # Display the Plotly chart
        st.plotly_chart(fig2, use_container_width=True)
        
        # Display drawdown statistics
        if drawdown_periods:
            st.subheader("Major Drawdown Periods (Below -25%)")
            
            # Create a list to store drawdown statistics
            stats_data = []
            
            for start, end in drawdown_periods:
                # Get data for this period
                mask = (df.index >= start) & (df.index <= end)
                period_df = df[mask]
                
                # Calculate statistics
                max_drawdown = period_df['Drawdown'].min() * 100
                duration = (end - start).days
                
                # Add to statistics
                stats_data.append({
                    "Start Date": start.strftime('%Y-%m-%d'),
                    "End Date": end.strftime('%Y-%m-%d') if end != df.index[-1] else "Ongoing",
                    "Max Drawdown": f"{max_drawdown:.2f}%",
                    "Duration": f"{duration} days"
                })
            
            # Display statistics as a table
            st.table(pd.DataFrame(stats_data))
