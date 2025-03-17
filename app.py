import streamlit as st                   # For building the web app UI
import yfinance as yf                    # For downloading financial data
import pandas as pd                      # For data manipulation and analysis
import plotly.graph_objects as go        # For interactive charts
from datetime import datetime            # For working with dates

# Expanded dictionary mapping for known Indian indices.
index_mapping = {
    "NIFTY50": "^NSEI",               # Nifty 50 index on NSE
    "NIFTY BANK": "^NSEBANK",          # Nifty Bank index on NSE
    "NIFTY NEXT 50": "^NSEI50",        # Nifty Next 50 index (verify if available)
    "NIFTY MIDCAP 100": "^NSEMCAP100",  # Nifty Midcap 100 index (verify if available)
    "NIFTY SMALLCAP 100": "^NSESMLCAP100",  # Nifty Smallcap 100 index (verify if available)
    "BSE SENSEX": "^BSESN",            # SENSEX on BSE
    "BSE 100": "^BSE100",              # BSE 100 index (verify if available)
    "BSE MIDCAP": "^BSEMIDCAP",        # BSE Midcap index (verify if available)
    "BSE SMALLCAP": "^BSESMLCAP"       # BSE Smallcap index (verify if available)
}

st.title("Indian Stock/Index Drawdown Analysis")
st.write("Enter a ticker name (e.g., TCS, INFY, NIFTY50, BSE SENSEX). "
         "For individual NSE stocks, the app will append '.NS' automatically.")

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
        
        df = stock_data[['Close']].copy()
        close_series = df['Close'].squeeze()
        df['ATH'] = close_series.cummax()
        df['Drawdown'] = (close_series - df['ATH']) / df['ATH']
        threshold = 0.25
        df['In_Drawdown'] = df['Drawdown'] <= -threshold
        df['Drawdown_Start'] = (df['In_Drawdown'] != df['In_Drawdown'].shift(1)) & df['In_Drawdown']
        df['Drawdown_End'] = (df['In_Drawdown'] != df['In_Drawdown'].shift(-1)) & df['In_Drawdown']
        
        drawdown_starts = df.index[df['Drawdown_Start']].tolist()
        drawdown_ends = df.index[df['Drawdown_End']].tolist()
        if len(drawdown_starts) > len(drawdown_ends):
            drawdown_ends.append(df.index[-1])
        
        st.write(f"Found **{len(drawdown_starts)}** significant drawdown periods (>= 25%).")
        
        summary_data = []
        for start, end in zip(drawdown_starts, drawdown_ends):
            period_data = df.loc[start:end]
            max_drawdown = period_data['Drawdown'].min()
            summary_data.append({
                'Start_Date': start,
                'End_Date': end,
                'Max_Drawdown': f"{max_drawdown*100:.2f}%",
                'Duration_Days': len(period_data)
            })
        
        st.subheader("Drawdown Summary")
        st.dataframe(pd.DataFrame(summary_data))
        
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price', line=dict(color='blue')))
        fig1.add_trace(go.Scatter(x=df.index, y=df['ATH'], mode='lines', name='All-Time High', line=dict(color='green', dash='dash')))
        for start, end in zip(drawdown_starts, drawdown_ends):
            fig1.add_vrect(x0=start, x1=end, fillcolor="red", opacity=0.2, line_width=0)
        fig1.update_layout(title=f"{ticker} Price and All-Time Highs", xaxis_title="Date", yaxis_title="Price", hovermode="x unified", template="plotly_white")
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df.index, y=df['Drawdown'] * 100, mode='lines', name='Drawdown (%)', line=dict(color='blue')))
        fig2.add_trace(go.Scatter(x=df.index, y=[-threshold * 100] * len(df.index), mode='lines', 
                                  name=f"Threshold (-{threshold*100:.0f}%)", line=dict(color='red', dash='dash')))
        fig2.add_trace(go.Scatter(x=df.index, y=df['Drawdown'] * 100, fill='tozeroy', 
                                  fillcolor='rgba(255,0,0,0.3)', mode='none', name="Drawdown Area"))
        fig2.update_layout(title=f"{ticker} Drawdowns from All-Time Highs", xaxis_title="Date", yaxis_title="Drawdown (%)", hovermode="x unified", template="plotly_white")
        
        st.subheader("Interactive Drawdown Analysis Plot")
        st.plotly_chart(fig1)
        st.plotly_chart(fig2)
