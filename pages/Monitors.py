import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

def get_stock_data(ticker_symbol, n_days):
    """
    Fetches the current price and historical data for a given stock ticker
    for the last N days.
    """
    stock_info = {}
    historical_data = pd.DataFrame()

    try:
        # Create a Ticker object
        stock = yf.Ticker(ticker_symbol)

        # Get current info, including real-time price
        info = stock.info
        current_price = info.get('regularMarketPrice')

        # Fallback for current price if 'regularMarketPrice' is not available
        if not current_price:
            hist_current_day = stock.history(period='1d')
            if not hist_current_day.empty:
                current_price = hist_current_day['Close'].iloc[-1]
            else:
                current_price = "N/A"

        stock_info['current_price'] = current_price
        stock_info['company_name'] = info.get('longName', ticker_symbol) # Get full company name

        # Fetch historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=n_days)
        historical_data = yf.download(ticker_symbol, start=start_date, end=end_date)

        # Add the current price to the historical data for plotting if applicable
        if isinstance(current_price, (int, float)) and current_price != "N/A":
            # Ensure the index is a DatetimeIndex
            current_price_series = pd.Series([current_price], index=[end_date])
            # Concatenate and remove potential duplicates (e.g., if market is closed and last
            # historical day is today)
            historical_data['Close'] = pd.concat([historical_data['Close'], current_price_series]).sort_index()
            historical_data = historical_data[~historical_data.index.duplicated(keep='last')]

    except Exception as e:
        st.error(f"Error fetching data for {ticker_symbol}: {e}. Please check the ticker symbol.")
        return None, None

    return stock_info, historical_data

def plot_stock_data(historical_data, ticker_symbol, company_name):
    """
    Generates a Plotly line chart for the stock's closing prices.
    """
    if historical_data.empty:
        st.warning("No historical data to plot.")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=historical_data.index, 
        y=historical_data['Close'], 
        mode='lines', 
        name=f'{ticker_symbol} Closing Price',
        line=dict(color='blue', width=2)
    ))

    fig.update_layout(
        title=f'{company_name} ({ticker_symbol}) Stock Price',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        hovermode="x unified", # Shows all y-values at a given x on hover
        template="plotly_white", # Clean white background
        xaxis_rangeslider_visible=True, # Add a range slider for easier navigation
        height=600 # Set a fixed height for better display in Streamlit
    )

    # Customize x-axis ticks for better readability
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=7, label="1w", step="day", stepmode="backward"),
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        ),
        type="date"
    )

    st.plotly_chart(fig, use_container_width=True)


# --- Streamlit App Layout ---
st.set_page_config(layout="centered", page_title="Stock Price Viewer", page_icon="📈")

st.title("📈 Stock Price Viewer")

st.markdown("""
This app retrieves current stock prices and plots historical closing prices
using `yfinance` for data and `Plotly` for interactive visualizations.
""")

# Sidebar for user inputs
st.sidebar.header("Input Parameters")
ticker_input = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL, MSFT, GOOGL)", "AAPL").upper()
num_days_input = st.sidebar.slider("Number of Historical Days to Show", 7, 365, 90)

if ticker_input:
    st.header(f"Data for {ticker_input}")

    # Fetch data
    stock_info, historical_data = get_stock_data(ticker_input, num_days_input)

    if stock_info and not historical_data.empty:
        st.subheader(f"Current Price: ${stock_info['current_price']:.2f}" if isinstance(stock_info['current_price'], (int, float)) else f"Current Price: {stock_info['current_price']}")
        
        st.subheader("Historical Price Chart")
        plot_stock_data(historical_data, ticker_input, stock_info['company_name'])
        
        st.subheader("Raw Historical Data")
        st.dataframe(historical_data[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10)) # Show last 10 rows

    elif stock_info is None and not historical_data:
        st.info("Please enter a valid ticker symbol.")
else:
    st.info("Please enter a stock ticker symbol to get started!")

st.markdown("---")
st.markdown("Developed by Gemini AI for stock data visualization.")