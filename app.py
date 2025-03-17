import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import requests
import time

# Expanded dictionary mapping for Indian indices
index_mapping = {
    "NIFTY50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "BSE SENSEX": "^BSESN"
}

# Function to fetch ticker suggestions from Yahoo Finance
@st.cache_data(ttl=60)  # Cache results for 1 minute - shorter to be more responsive
def get_ticker_suggestions(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        # Filter to only include Indian stocks (.NS, .BO) and indices (^)
        suggestions = []
        for item in data.get("quotes", []):
            symbol = item["symbol"]
            name = item.get("shortname", "Unknown")
            if symbol.endswith(".NS") or symbol.endswith(".BO") or symbol.startswith("^"):
                suggestions.append((symbol, name))
        return suggestions
    except Exception as e:
        st.error(f"Error fetching suggestions: {e}")
        return []

# Function to analyze stock data
def analyze_stock(ticker):
    st.write(f"**Using Ticker:** {ticker}")
    
    with st.spinner("Downloading data..."):
        stock_data = yf.download(ticker, period="max")
    
    if stock_data.empty:
        st.error("Error: Invalid ticker or no data available.")
        return
    
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

# Custom CSS for better suggestion display
st.markdown("""
<style>
.suggestion-item {
    cursor: pointer;
    padding: 8px 12px;
    background-color: #1E1E1E;
    color: white;
    border: 1px solid #333;
    border-radius: 4px;
    margin-bottom: 4px;
    transition: background-color 0.2s;
}
.suggestion-item:hover {
    background-color: #2E2E2E;
    border-color: #555;
}
</style>
""", unsafe_allow_html=True)

st.title("Indian Stock/Index Drawdown Analysis")

# Initialize session state
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = ""
if 'selected_name' not in st.session_state:
    st.session_state.selected_name = ""
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'suggestions' not in st.session_state:
    st.session_state.suggestions = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0
if 'analyze_flag' not in st.session_state:
    st.session_state.analyze_flag = False

# Function to handle stock selection
def select_stock(ticker, name):
    st.session_state.selected_ticker = ticker
    st.session_state.selected_name = name
    st.session_state.search_query = name
    st.session_state.suggestions = []  # Clear suggestions after selection
    st.session_state.analyze_flag = True  # Set flag to trigger analysis

# Create a container for the search and suggestions
search_container = st.container()

with search_container:
    # Search input
    search_input = st.text_input(
        "Search for stock or index:", 
        value=st.session_state.search_query,
        key="search_input"
    )
    
    # Update search query in session state
    if search_input != st.session_state.search_query:
        st.session_state.search_query = search_input
        # Only fetch suggestions if query has 3+ characters
        if len(search_input) >= 3:
            st.session_state.suggestions = get_ticker_suggestions(search_input)
        else:
            st.session_state.suggestions = []
    
    # Display suggestions
    if st.session_state.suggestions:
        suggestion_container = st.container()
        with suggestion_container:
            for i, (symbol, name) in enumerate(st.session_state.suggestions[:10]):  # Limit to top 10 results
                if st.button(name, key=f"suggestion_{i}", use_container_width=True):
                    select_stock(symbol, name)

# Manual ticker input as a fallback
manual_ticker = st.text_input(
    "Or enter ticker symbol directly:", 
    value=st.session_state.selected_ticker,
    key="manual_input"
)

if manual_ticker and manual_ticker != st.session_state.selected_ticker:
    st.session_state.selected_ticker = manual_ticker
    st.session_state.analyze_flag = True

# Determine which ticker to use
final_ticker = ""
if st.session_state.selected_ticker:
    final_ticker = index_mapping.get(st.session_state.selected_ticker, st.session_state.selected_ticker)
elif manual_ticker:
    final_ticker = index_mapping.get(manual_ticker, manual_ticker)

# Add .NS suffix for Indian stocks if needed
if final_ticker and not any(x in final_ticker for x in ['.', '^']) and not final_ticker.endswith('.NS'):
    final_ticker += ".NS"

# Analysis section
analysis_container = st.container()

# Check if we should analyze
if st.session_state.analyze_flag and final_ticker:
    with analysis_container:
        analyze_stock(final_ticker)
        st.session_state.analyze_flag = False  # Reset flag after analysis
