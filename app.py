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
@st.cache_data(ttl=60)
def get_ticker_suggestions(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        suggestions = []
        for item in data.get("quotes", []):
            name = item.get("shortname", "Unknown")
            symbol = item["symbol"]
            
            if symbol.endswith(".NS") or symbol.endswith(".BO") or symbol.startswith("^"):
                suggestions.append((symbol, name))
        return suggestions
    except Exception as e:
        return []

# Custom CSS for better suggestion display
st.markdown("""
<style>
.suggestion-box {
    margin-bottom: 4px;
    padding: 5px;
    border-radius: 4px;
}
.stButton button {
    width: 100%;
    text-align: left;
    background-color: #1E1E1E;
    color: white;
    border: 1px solid #333;
    padding: 8px 12px;
    font-size: 14px;
}
.stButton button:hover {
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

# Function to handle stock selection
def select_stock(ticker, name):
    st.session_state.selected_ticker = ticker
    st.session_state.selected_name = name
    st.session_state.search_query = name
    st.session_state.suggestions = []  # Clear suggestions after selection

# Function to update suggestions
def update_suggestions():
    query = st.session_state.search_query
    if len(query) >= 3 and time.time() - st.session_state.last_update > 0.5:
        st.session_state.suggestions = get_ticker_suggestions(query)
        st.session_state.last_update = time.time()
    elif len(query) < 3:
        st.session_state.suggestions = []

# Search input with callback
st.text_input(
    "Search for stock or index:", 
    value=st.session_state.search_query,
    key="search_query",
    on_change=update_suggestions
)

# Display suggestions dynamically
if st.session_state.suggestions:
    st.write("**Suggestions:**")
    for i, (symbol, name) in enumerate(st.session_state.suggestions[:10]):  # Limit to top 10 results
        if st.button(name, key=f"suggestion_{i}"):
            select_stock(symbol, name)

# Manual ticker input as a fallback
manual_ticker = st.text_input(
    "Or enter ticker symbol directly:", 
    value=st.session_state.selected_ticker,
    key="manual_input"
)
