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

def plot_stock_chart(ticker_symbol, period="max"):
    """
    Fetches stock data for a given Indian stock ticker symbol and plots a simple line chart.

    Parameters:
        ticker_symbol (str): Stock ticker symbol (e.g., "TCS.NS" for NSE, "RELIANCE.BO" for BSE).
        period (str): Time period of the stock data (default is "max" to get all available data).
    """

    # Fetch stock data
    stock = yf.Ticker(ticker_symbol)
    data = stock.history(period=period)

    # Ensure 'Close' column is float
    data["Close"] = data["Close"].astype(float)

    # Create figure
    fig = go.Figure()
    
    # Add line trace for closing prices
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        mode='lines',
        name="Closing Price",
        line=dict(color='blue')
    ))

    # Customize layout
    fig.update_layout(
        title=f"{ticker_symbol} Stock Price History",
        xaxis_title="Date",
        yaxis_title="Stock Price (INR)",
        xaxis_rangeslider_visible=False
    )

    # Show the chart
    return fig

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
        
        # Identify drawdown periods
        drawdown_periods = []
        in_drawdown = False
        start_date = None
        
        for date, value in df['In_Drawdown'].items():
            if value and not in_drawdown:
                in_drawdown = True
                start_date = date
            elif not value and in_drawdown:
                in_drawdown = False
                drawdown_periods.append((start_date, date))
                start_date = None
        
        if in_drawdown:
            drawdown_periods.append((start_date, df.index[-1]))
        
        # Create stock price chart with Plotly
        fig1 = plot_stock_chart(ticker, "max")
        
        # Display the Plotly price chart
        st.plotly_chart(fig1, use_container_width=True)
        
        # Create drawdown chart with Plotly
        fig2 = go.Figure()
        
        # Add drawdown percentage trace
        fig2.add_trace(go.Scatter(
            x=df.index, y=df['Drawdown'] * 100, mode='lines', name='Drawdown (%)', line=dict(color='red')
        ))
        
        # Add threshold line
        fig2.add_trace(go.Scatter(
            x=df.index, y=[threshold * 100] * len(df), mode='lines', name='Threshold (-25%)', line=dict(color='red', dash='dash')
        ))
        
        # Highlight drawdown periods
        for start, end in drawdown_periods:
            fig2.add_vrect(
                x0=start, x1=end, fillcolor="red", opacity=0.1, layer="below", line_width=0
            )
        
        # Customize layout
        fig2.update_layout(
            title=f"{ticker} Drawdowns",
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            template="plotly_white",
            hovermode="x unified"
        )
        
        # Display the Plotly drawdown chart
        st.plotly_chart(fig2, use_container_width=True)
        
        # Display drawdown statistics
        if drawdown_periods:
            st.subheader("Major Drawdown Periods (Below -25%)")
            
            stats_data = []
            
            for start, end in drawdown_periods:
                mask = (df.index >= start) & (df.index <= end)
                period_df = df[mask]
                
                max_drawdown = period_df['Drawdown'].min() * 100
                duration = (end - start).days
                
                stats_data.append({
                    "Start Date": start.strftime('%Y-%m-%d'),
                    "End Date": end.strftime('%Y-%m-%d') if end != df.index[-1] else "Ongoing",
                    "Max Drawdown": f"{max_drawdown:.2f}%",
                    "Duration": f"{duration} days"
                })
            
            st.table(pd.DataFrame(stats_data))
