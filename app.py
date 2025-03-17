import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import requests

# Set page config for wider layout
st.set_page_config(layout="wide")

# Expanded dictionary mapping for Indian indices
index_mapping = {
    "NIFTY50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "BSE SENSEX": "^BSESN"
}

# Function to fetch ticker suggestions from Yahoo Finance
@st.cache_data(ttl=300)  # Cache results for 5 minutes
def get_ticker_suggestions(query):
    if len(query) < 3:
        return []
        
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        suggestions = [(item["symbol"], item.get("shortname", "Unknown")) for item in data.get("quotes", [])]
        return suggestions
    except Exception as e:
        st.error(f"Error fetching suggestions: {e}")
        return []

st.title("Indian Stock/Index Drawdown Analysis")

# Initialize session state
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = ""
if 'selected_name' not in st.session_state:
    st.session_state.selected_name = ""
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# Function to handle stock selection
def select_stock(ticker, name):
    st.session_state.selected_ticker = ticker
    st.session_state.selected_name = name
    st.session_state.search_query = name

# Search input
user_input = st.text_input(
    "Search for stock or index:", 
    value=st.session_state.search_query,
    key="search_input"
)

# Auto-update search query in session state
if user_input != st.session_state.search_query:
    st.session_state.search_query = user_input

# Get suggestions if query is 3+ characters
suggestions = []
if len(user_input) >= 3:
    suggestions = get_ticker_suggestions(user_input)

# Display suggestions as clickable buttons
if suggestions:
    for i, (symbol, name) in enumerate(suggestions[:10]):  # Limit to top 10 results
        display_text = f"{name} ({symbol})"
        if st.button(display_text, key=f"suggestion_{i}", use_container_width=True):
            select_stock(symbol, name)

# Manual ticker input as a fallback
manual_ticker = st.text_input(
    "Or enter ticker symbol directly:", 
    value=st.session_state.selected_ticker,
    key="manual_input"
)

# Determine which ticker to use
final_ticker = ""
if st.session_state.selected_ticker:
    final_ticker = index_mapping.get(st.session_state.selected_ticker, st.session_state.selected_ticker)
elif manual_ticker:
    final_ticker = index_mapping.get(manual_ticker, manual_ticker)

# Add .NS suffix for Indian stocks if needed
if final_ticker and not any(x in final_ticker for x in ['.', '^']) and not final_ticker.endswith('.NS'):
    final_ticker += ".NS"

# Analysis button
col1, col2 = st.columns([1, 6])
with col1:
    analyze_button = st.button("Analyze", type="primary")

if analyze_button and final_ticker:
    ticker = final_ticker
    
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
        
        # Use the full width for charts
        st.write("### Price and Drawdown Analysis")
        
        # Create price chart with Plotly (instead of Matplotlib)
        fig1 = go.Figure()
        
        # Add price line
        fig1.add_trace(go.Scatter(
            x=df.index,
            y=df['Close'],
            mode='lines',
            name='Close Price',
            line=dict(color='blue')
        ))
        
        # Add ATH line
        fig1.add_trace(go.Scatter(
            x=df.index,
            y=df['ATH'],
            mode='lines',
            name='All-Time High',
            line=dict(color='green', dash='dash')
        ))
        
        # Add shaded regions for drawdown periods
        for start, end in drawdown_periods:
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
        
        # Update layout for price chart
        fig1.update_layout(
            title=f"{ticker} Price and All-Time High",
            xaxis_title=None,  # Remove x-axis title for better alignment
            yaxis_title="Price",
            legend_title="Legend",
            template="plotly_white",
            margin=dict(l=0, r=0, t=40, b=0),
            height=400
        )
        
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
            title=None,  # No title needed since it's aligned with chart above
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            legend_title="Legend",
            template="plotly_white",
            hovermode="x unified",
            margin=dict(l=0, r=0, t=0, b=30),
            height=300
        )
        
        # Ensure the charts are perfectly aligned by linking their x-axes
        fig1.update_layout(xaxis_range=[df.index.min(), df.index.max()])
        fig2.update_layout(xaxis_range=[df.index.min(), df.index.max()])
        
        # Display the charts one above the other
        st.plotly_chart(fig1, use_container_width=True)
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
