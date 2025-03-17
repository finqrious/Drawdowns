import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# Screener Login Function
def screener_login():
    session = requests.Session()
    login_url = "https://www.screener.in/login/"
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract CSRF token
    csrf_token = session.cookies.get("csrftoken") or soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]

    credentials = {
        "username": "psuyog142@gmail.com",  # Replace with your Screener login email
        "password": "Kalyan@123",  # Replace with your Screener password
        "csrfmiddlewaretoken": csrf_token
    }

    headers = {
        "Referer": login_url,
        "User-Agent": "Mozilla/5.0",
        "X-CSRFToken": csrf_token,
    }

    login_response = session.post(login_url, data=credentials, headers=headers)

    if "Invalid username" in login_response.text or login_response.status_code != 200:
        st.error("❌ Login failed! Check credentials.")
        return None

    return session

# Fetch Stock Data from Screener
def fetch_stock_data(stock_id, session):
    api_url = f"https://www.screener.in/api/company/{stock_id}/chart/"
    payload = {
        "q": "Price to Earning-Median PE-EPS",
        "days": 10000,  # Fetch max available data
        "consolidated": True
    }

    headers = {
        "Referer": f"https://www.screener.in/company/{stock_id}/",
        "X-CSRFToken": session.cookies.get("csrftoken"),
        "Cookie": f"csrftoken={session.cookies.get('csrftoken')}; sessionid={session.cookies.get('sessionid')}"
    }

    data_response = session.get(api_url, headers=headers, params=payload)

    if data_response.status_code == 200:
        data = data_response.json()
        datasets = data.get("datasets", [])
        stock_data = []

        for dataset in datasets:
            metric = dataset.get("metric")  # Extract metric (PE, EPS, etc.)
            values = dataset.get("values", [])  # Extract values

            df = pd.DataFrame(values, columns=["Date", "Value"])
            df["Metric"] = metric
            stock_data.append(df)

        final_df = pd.concat(stock_data)
        final_df = final_df.pivot(index="Date", columns="Metric", values="Value").reset_index()

        # Keep only Date, Price, and PE Ratio
        final_df = final_df[["Date", "Price to Earning"]]
        final_df = final_df.dropna(subset=["Price to Earning"])
        final_df["Date"] = pd.to_datetime(final_df["Date"])
        final_df = final_df.sort_values(by="Date")

        return final_df

    else:
        st.error(f"❌ Failed to fetch data! Status Code: {data_response.status_code}")
        return None

# Plot Stock Chart with PE Ratio
def plot_stock_chart(df, ticker_symbol):
    fig = go.Figure()

    # Stock Price Line
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Price to Earning"],  # Using Price to Earning as stock price
        mode='lines',
        name="Stock Price",
        line=dict(color='blue')
    ))

    # PE Ratio Line
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Price to Earning"],  # PE Ratio
        mode='lines',
        name="PE Ratio",
        yaxis="y2",  # Second y-axis
        line=dict(color='orange')
    ))

    # Update layout with dual y-axes
    fig.update_layout(
        title=f"{ticker_symbol} Stock Price & PE Ratio",
        xaxis_title="Date",
        yaxis_title="Stock Price",
        yaxis2=dict(
            title="PE Ratio",
            overlaying="y",
            side="right"
        ),
        xaxis_rangeslider_visible=False
    )

    # Show Plotly chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)

# Streamlit UI
st.title("Indian Stock/Index Analysis (Screener Data)")

user_input = st.text_input("Enter Screener Stock ID:", "").strip()

if user_input:
    session = screener_login()
    if session:
        with st.spinner("Fetching data..."):
            stock_data = fetch_stock_data(user_input, session)

        if stock_data is not None:
            st.success(f"✅ Data fetched for Stock ID: {user_input}")
            plot_stock_chart(stock_data, user_input)
