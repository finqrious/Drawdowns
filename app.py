import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import requests
from bs4 import BeautifulSoup

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
        
        # Fetch PE Ratio Data from Screener.in
        session = requests.Session()
        login_url = "https://www.screener.in/login/"
        response = session.get(login_url)
        soup = BeautifulSoup(response.text, "html.parser")
        csrf_token = session.cookies.get("csrftoken") or soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]

        credentials = {
            "username": "your_email@example.com",
            "password": "your_password",
            "csrfmiddlewaretoken": csrf_token
        }

        headers = {
            "Referer": login_url,
            "User-Agent": "Mozilla/5.0",
            "X-CSRFToken": csrf_token,
        }

        login_response = session.post(login_url, data=credentials, headers=headers)

        stock_id = "295"
        api_url = f"https://www.screener.in/api/company/{stock_id}/chart/"

        payload = {
            "q": "Price to Earning-Median PE-EPS",
            "days": 10000,
            "consolidated": True
        }

        headers.update({
            "Referer": f"https://www.screener.in/company/{stock_id}/",
            "X-CSRFToken": session.cookies.get("csrftoken"),
            "Cookie": f"csrftoken={session.cookies.get('csrftoken')}; sessionid={session.cookies.get('sessionid')}"
        })

        data_response = session.get(api_url, headers=headers, params=payload)

        if data_response.status_code == 200:
            data = data_response.json()
            datasets = data.get("datasets", [])
            stock_data_pe = []

            for dataset in datasets:
                metric = dataset.get("metric")
                values = dataset.get("values", [])

                df_pe = pd.DataFrame(values, columns=["Date", "Value"])
                df_pe["Metric"] = metric
                stock_data_pe.append(df_pe)

            final_pe_df = pd.concat(stock_data_pe)
            final_pe_df = final_pe_df.pivot(index="Date", columns="Metric", values="Value").reset_index()
            final_pe_df = final_pe_df[["Date", "Price to Earning"]]
            final_pe_df = final_pe_df.dropna(subset=["Price to Earning"])
            final_pe_df["Date"] = pd.to_datetime(final_pe_df["Date"])
            final_pe_df = final_pe_df.sort_values(by="Date")
        
        # Merge PE data with stock price data
        df = df.merge(final_pe_df, left_index=True, right_on="Date", how="left")

        # Create price & PE chart with Plotly
        fig = go.Figure()
        
        # Add stock price trace
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Close"],
            mode='lines',
            name="Closing Price",
            line=dict(color='blue'),
            yaxis="y1"
        ))
        
        # Add PE Ratio trace
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Price to Earning"],
            mode='lines',
            name="PE Ratio",
            line=dict(color='orange'),
            yaxis="y2"
        ))

        # Customize layout
        fig.update_layout(
            title=f"{ticker} Stock Price & PE Ratio",
            xaxis_title="Date",
            yaxis=dict(title="Stock Price (INR)", side="left", showgrid=False),
            yaxis2=dict(title="PE Ratio", side="right", overlaying="y", showgrid=False),
            legend=dict(x=0.02, y=0.98),
            xaxis_rangeslider_visible=False
        )

        # Show the Plotly chart
        st.plotly_chart(fig, use_container_width=True)
