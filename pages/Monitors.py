# Custom monitoring page 
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime, timedelta

def get_stock_data_and_plot(ticker_symbol, n_days=30, plot_res_dpi=300):
    """
    Fetches the current price and historical data for the last N days,
    then plots the closing price with high resolution.

    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., "AAPL").
        n_days (int): The number of past days to retrieve historical data for.
        plot_res_dpi (int): Dots per inch for the plot, for high resolution.
    """
    
    # 1. Get the current price
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        current_price = info.get('regularMarketPrice') 
        
        if not current_price:
            # Fallback to the last closing price if regularMarketPrice isn't directly available
            hist_current_day = stock.history(period='1d')
            if not hist_current_day.empty:
                current_price = hist_current_day['Close'].iloc[-1]
            else:
                current_price = "N/A" # Indicate price couldn't be fetched
        
        print(f"Current price of {ticker_symbol}: ${current_price}")

    except Exception as e:
        print(f"Error fetching current price for {ticker_symbol}: {e}")
        current_price = "Error"

    # 2. Get historical data for the last N days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=n_days)

    try:
        hist_data = yf.download(ticker_symbol, start=start_date, end=end_date)
        if hist_data.empty:
            print(f"No historical data found for {ticker_symbol} in the last {n_days} days.")
            return
    except Exception as e:
        print(f"Error fetching historical data for {ticker_symbol}: {e}")
        return

    # 3. Prepare data for plotting
    # We only care about the 'Close' price for this plot
    plot_data = hist_data['Close']
    
    # Add the current price as the last data point if it's available and valid
    if isinstance(current_price, (int, float)) and current_price != "N/A":
        # Create a new index for the current price (today's date)
        # Use end_date as the index for the current price point
        current_price_series = pd.Series([current_price], index=[end_date])
        # Concatenate, dropping duplicates in case the last historical entry is for today
        plot_data = pd.concat([plot_data, current_price_series]).sort_index()
        plot_data = plot_data[~plot_data.index.duplicated(keep='last')]


    # 4. Plot the data
    plt.figure(figsize=(14, 7), dpi=plot_res_dpi) # Set figure size and DPI for high resolution
    plt.plot(plot_data.index, plot_data.values, label=f'{ticker_symbol} Closing Price', color='blue', linewidth=1.5)

    plt.title(f'{ticker_symbol} Stock Price - Last {n_days} Days', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Price (USD)', fontsize=12)
    
    # Format x-axis for better readability of dates
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.AutoLocator())
    plt.gcf().autofmt_xdate() # Auto-format date labels to prevent overlap

    plt.grid(True, linestyle='--', alpha=0.0) # Light grid for readability
    plt.legend()
    plt.tight_layout() # Adjust layout to prevent labels from being cut off
    plt.show()

# Example Usage:
ticker_symbol = "GOOGL"  # Google (Class A)
num_days = 90          # Last 90 days
plot_resolution = 300  # 300 DPI for high resolution

get_stock_data_and_plot(ticker_symbol, num_days, plot_resolution)

# Another example
ticker_symbol_2 = "AMZN" # Amazon
num_days_2 = 180
get_stock_data_and_plot(ticker_symbol_2, num_days_2)