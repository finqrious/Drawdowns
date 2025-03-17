import streamlit as st                   # For building the web app UI
import yfinance as yf                    # For downloading financial data
import pandas as pd                      # For data manipulation and analysis
import matplotlib.pyplot as plt          # For plotting
from datetime import datetime            # For working with dates

# Expanded dictionary mapping for known Indian indices.
# If any ticker is not working, verify on Yahoo Finance and update accordingly.
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

# Set up the Streamlit app title and description.
st.title("Indian Stock/Index Drawdown Analysis")
st.write("Enter a ticker name (e.g., TCS, INFY, NIFTY50, BSE SENSEX). "
         "For individual NSE stocks, the app will append '.NS' automatically.")

# Sidebar for user input.
user_input = st.text_input("Enter Ticker Name:", "").strip().upper()

# Only proceed if user has entered something.
if user_input:
    # Map the input to the correct ticker symbol:
    # If the input matches a known index, use its mapped ticker; else, assume it's an NSE stock.
    if user_input in index_mapping:
        ticker = index_mapping[user_input]
    else:
        ticker = user_input + ".NS"
    
    st.write(f"**Using Ticker:** {ticker}")
    
    # Download data from Yahoo Finance
    with st.spinner("Downloading data..."):
        stock_data = yf.download(ticker, period="max")
    
    if stock_data.empty:
        st.error("Error: Invalid ticker or no data available.")
    else:
        st.success(f"Downloaded {len(stock_data)} rows of data.")
        
        # Create a DataFrame with only the 'Close' price.
        df = stock_data[['Close']].copy()
        
        # Convert 'Close' to a Series for arithmetic operations.
        close_series = df['Close'].squeeze()
        
        # Calculate the All-Time High (ATH) for each point.
        ath_series = close_series.cummax()
        df['ATH'] = ath_series
        
        # Calculate drawdown percentage relative to the ATH.
        df['Drawdown'] = (close_series - ath_series) / ath_series
        
        # Define drawdown threshold (25% drop).
        threshold = 0.25
        
        # Mark periods where drawdown exceeds the threshold.
        df['In_Drawdown'] = df['Drawdown'] <= -threshold
        
        # Identify the start (transition from False to True) of a drawdown period.
        df['Drawdown_Start'] = (df['In_Drawdown'] != df['In_Drawdown'].shift(1)) & df['In_Drawdown']
        # Identify the end (transition from True to False) of a drawdown period.
        df['Drawdown_End'] = (df['In_Drawdown'] != df['In_Drawdown'].shift(-1)) & df['In_Drawdown']
        
        # Extract the list of start and end dates.
        drawdown_starts = df.index[df['Drawdown_Start']].tolist()
        drawdown_ends = df.index[df['Drawdown_End']].tolist()
        
        # If still in a drawdown at the end, append the last date.
        if len(drawdown_starts) > len(drawdown_ends):
            drawdown_ends.append(df.index[-1])
        
        st.write(f"Found **{len(drawdown_starts)}** significant drawdown periods (>= 25%).")
        
        # Build a summary list for the drawdown periods.
        summary_data = []
        for i in range(min(len(drawdown_starts), len(drawdown_ends))):
            start_date = drawdown_starts[i]
            end_date = drawdown_ends[i]
            period_data = df.loc[start_date:end_date]
            max_drawdown = period_data['Drawdown'].min()
            duration = len(period_data)
            summary_data.append({
                'Start_Date': start_date,
                'End_Date': end_date,
                'Max_Drawdown': f"{max_drawdown*100:.2f}%",
                'Duration_Days': duration
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        st.subheader("Drawdown Summary")
        st.dataframe(summary_df)
        
        # Plotting the data with matplotlib.
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Top plot: Price and All-Time High.
        ax1.plot(df.index, df['Close'], label='Close Price', color='blue')
        ax1.plot(df.index, df['ATH'], label='All-Time High', color='green', linestyle='--')
        for i in range(min(len(drawdown_starts), len(drawdown_ends))):
            ax1.axvspan(drawdown_starts[i], drawdown_ends[i], color='red', alpha=0.2)
        ax1.set_title(f"{ticker} Price and All-Time Highs")
        ax1.set_ylabel("Price")
        ax1.legend()
        ax1.grid(True)
        
        # Bottom plot: Drawdown percentage.
        ax2.plot(df.index, df['Drawdown'] * 100, color='blue')
        ax2.axhline(y=-threshold * 100, color='red', linestyle='--', label=f"Threshold (-{threshold*100:.0f}%)")
        ax2.fill_between(df.index, df['Drawdown'] * 100, 0, where=(df['Drawdown'] <= -threshold), color='red', alpha=0.3)
        ax2.set_title(f"{ticker} Drawdowns from All-Time Highs")
        ax2.set_ylabel("Drawdown (%)")
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        
        st.subheader("Drawdown Analysis Plot")
        st.pyplot(fig)
