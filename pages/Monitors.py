import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import bin.alerts as alerts  
import pytz 

# Session vars: (these are preserved between runs)
if 'active_alerts' not in st.session_state:
    active_alerts = {
        key: value for key, value in alerts.stock_alerts_dict.items()
        if value.get('active') == 1
        }
    st.session_state.active_alerts = active_alerts


def get_stock_data_high_resolution(ticker_symbol, n_days, interval='1m'):
    """
    Fetches high-resolution historical data and the current price for a given stock ticker.

    Args:
        ticker_symbol (str): The ticker symbol of the stock (e.g., 'AAPL').
        n_days (int): The number of days for which to fetch historical data.
                      Note: For intraday intervals, yfinance has limitations on the
                      maximum historical period available.
        interval (str): The interval of the data points.
                        Common options: '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d'.
                        - '1m' supports a maximum period of 7 days.
                        - '2m', '5m', '15m', '30m' support a maximum period of 60 days.
                        - '60m', '1h' support a maximum period of 2 years (approx. 730 days).
                        - '1d' (daily) supports the maximum available history.

    Returns:
        tuple: A tuple containing:
            - dict: Stock information including 'current_price' and 'company_name'.
            - pandas.DataFrame: Historical data with the specified resolution.
                                The index of the DataFrame will be datetime objects.
    """
    stock_info = {}
    historical_data = pd.DataFrame()


    # Create a Ticker object
    stock = yf.Ticker(ticker_symbol)

    # Get current info, including real-time price
    # 'regularMarketPrice' is generally the most up-to-date price
    info = stock.info
    current_price = info.get('regularMarketPrice')

    # Fallback for current price if 'regularMarketPrice' is not available
    if not current_price:
        # Try to get the latest intraday close for the current day
        hist_current_day = stock.history(period='1d', interval=interval)
        if hist_current_day.empty:
            # If intraday for today is empty, fall back to daily close
            hist_current_day = stock.history(period='1d', interval='1d')
        if not hist_current_day.empty:
            current_price = hist_current_day['Close'].iloc[-1]
        else:
            current_price = "N/A" # If no data can be fetched

    stock_info['current_price'] = current_price
    # Get the full company name, falling back to ticker symbol if not found
    stock_info['company_name'] = info.get('longName', ticker_symbol)

    # Determine the appropriate 'period' string for yfinance based on n_days and interval.
    # yfinance's 'period' argument is generally more reliable for intraday data
    # than explicit start/end dates.
    if interval == '1m':
        # Max 7 days for 1-minute data
        period_str = f"{min(n_days, 7)}d"
    elif interval in ['2m', '5m', '15m', '30m']:
        # Max 60 days for these intraday intervals
        period_str = f"{min(n_days, 60)}d"
    elif interval in ['60m', '1h']:
        # Max 2 years (approx. 730 days) for hourly data
        period_str = f"{min(n_days, 730)}d"
    else: # For daily ('1d') or other intervals, allow longer periods
        if n_days <= 30: period_str = '1mo'
        elif n_days <= 90: period_str = '3mo'
        elif n_days <= 180: period_str = '6mo'
        elif n_days <= 365: period_str = '1y'
        elif n_days <= 730: period_str = '2y'
        elif n_days <= 1825: period_str = '5y'
        elif n_days <= 3650: period_str = '10y'
        else: period_str = 'max' # Fetch maximum available history

    # Fetch historical data with the specified interval and period
    historical_data = yf.download(ticker_symbol, period=period_str, interval=interval)
    # Remove weird column headers 
    if isinstance(historical_data.columns, pd.MultiIndex):
        # This handles cases where yfinance might return (Ticker, Column_Name)
        # We want to keep only the Column_Name
        historical_data.columns = [col[0] if isinstance(col, tuple) else col for col in historical_data.columns]
    
    # Optionally, add the current price to the historical data.
    # For high-resolution data, the last entry in historical_data should be very close
    # to the current price. We only add a new row if there's a significant difference
    # or if the historical data is empty.
    if isinstance(current_price, (int, float)) and current_price != "N/A":
        if historical_data.empty or abs(historical_data['Close'].iloc[-1] - current_price) > 0.01:
            # Create a new row for the current price with the current timestamp
            current_timestamp = datetime.now()
            # Ensure the new timestamp has the same timezone as the DataFrame's index if it exists
            if not historical_data.empty and historical_data.index.tz is not None:
                current_timestamp = current_timestamp.astimezone(historical_data.index.tz)

            new_row = pd.DataFrame([{
                'Open': current_price,
                'High': current_price,
                'Low': current_price,
                'Close': current_price,
                'Adj Close': current_price,
                'Volume': 0 # Volume is 0 for a single price point
            }], index=[current_timestamp])

            # Concatenate the new row and remove any potential duplicates (e.g., if data for
            # the exact current timestamp already exists from the last fetched interval)
            historical_data = pd.concat([historical_data, new_row]).sort_index()
            historical_data = historical_data[~historical_data.index.duplicated(keep='last')]

    return stock_info, historical_data

def plot_stock_data(historical_data, ticker_symbol, company_name, lower_limit, upper_limit):
    """
    Generates a Plotly line chart for the stock's closing prices.
    looks for lower limits and upper limits to add as lines in the chart 
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

    # Add lower_limit horizontal line if not None
    if lower_limit is not None:
        fig.add_hline(
            y=lower_limit, 
            line_dash="dot", 
            line_color="green", 
            annotation_text=f"Lower Limit: {lower_limit}", 
            annotation_position="bottom right"
        )

    # Add upper_limit horizontal line if not None
    if upper_limit is not None:
        fig.add_hline(
            y=upper_limit, 
            line_dash="dot", 
            line_color="red", 
            annotation_text=f"Upper Limit: {upper_limit}", 
            annotation_position="top right"
        )

    fig.update_layout(
        title=f'{company_name} ({ticker_symbol}) Stock Price',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        hovermode="x unified", # Shows all y-values at a given x on hover
        template="plotly_white", # Clean white background
        xaxis_rangeslider_visible=False, # Add a range slider for easier navigation
        height=300 # Set a fixed height for better display in Streamlit
    )

    # Customize x-axis ticks for better readability
    # fig.update_xaxes(
    #     rangeselector=dict(
    #         buttons=list([
    #             dict(count=7, label="1w", step="day", stepmode="backward"),
    #             dict(count=1, label="1m", step="month", stepmode="backward"),
    #             dict(count=3, label="3m", step="month", stepmode="backward"),
    #             dict(count=6, label="6m", step="month", stepmode="backward"),
    #             dict(count=1, label="1y", step="year", stepmode="backward"),
    #             dict(step="all")
    #         ])
    #     ),
    #     type="date"
    # )

    st.plotly_chart(fig, use_container_width=True)

def retrieve_alert_details(ticker_input):
    """Returns a dict if alerts exist for this ticker"""
    try:
        alert_dict = alerts.stock_alerts_dict[ticker_input.upper()]
        
        return alert_dict
    except Exception as e:
        st.write(e)
        return None 

def convert_date_to_tz(datetime_value):
    """Inputs datetime value from pandas and output date time in pst"""
    timestamp_str_utc_naive = str(datetime_value)[:19].replace('+00:00','')
    dt_naive_utc = datetime.strptime(timestamp_str_utc_naive, '%Y-%m-%d %H:%M:%S')
    utc_tz = pytz.utc
    dt_utc_aware = utc_tz.localize(dt_naive_utc)
    pst_tz = pytz.timezone('America/Los_Angeles') # Handles PST/PDT transitions
    return dt_utc_aware.astimezone(pst_tz)

def check_alert_value(ticker_input, current_price):
    """Checks single stock input and returns notification if out of bounds"""
    alert_data = retrieve_alert_details(ticker_input)
    if current_price > alert_data['upper_limit']:
        differential = current_price - alert_data['upper_limit']
        return f'**{ticker_input}** : Upper bound alert ~ Price: **{round(current_price,2)}**, Upper limit: **{alert_data['upper_limit']}**, **@${round(differential,2)}** diff '
    elif current_price > alert_data['upper_limit']:
        return f'**{ticker_input}** : Lower bound alert'
    else: 
        return None 

def get_all_current_alerts():
    for ticker in st.session_state.active_alerts:
        alert_string = check_alert_value(ticker, st.session_state.active_alerts[ticker.upper()]['current_price'])
        if alert_string is not None:
            st.info(alert_string)
                
# uncomment this for production reruns 
@st.fragment(run_every=60) 
def create_monitor_card(ticker_input):
    with st.container(border=True):
        if ticker_input:
            # Fetch data
            stock_info, historical_data = get_stock_data_high_resolution(ticker_input, num_days_input)

            # Cache current price for alerts: 
            st.session_state.active_alerts[ticker_input.upper()]['current_price'] = stock_info['current_price']


            # Check for any alerts 
            alert_data = retrieve_alert_details(ticker_input)
            lower_limit         = None if alert_data is None else alert_data['lower_limit']
            lower_limit_delta   = None if alert_data is None else round(lower_limit - stock_info['current_price'],2)
            upper_limit         = None if alert_data is None else alert_data['upper_limit']
            upper_limit_delta   = None if alert_data is None else round(upper_limit - stock_info['current_price'],2)

            if stock_info and not historical_data.empty:
                mc0,mc1,mc2,mc3 = st.columns(4, vertical_alignment='top')
                # Timestamp convert  
                dt_pst = convert_date_to_tz(max(historical_data.index))

                # column data    
                mc0.write(f"**{ticker_input}**<br> {dt_pst} ", unsafe_allow_html=True)
                mc1.metric("Current Price", f"${stock_info['current_price']:.2f}", border=False)
                if alert_data is not None: # show alerts if they exist 
                    mc2.metric("Lower Alert", f"${lower_limit:.2f}", border=False, delta = lower_limit_delta, delta_color='normal')
                    mc3.metric("Upper Alert", f"${upper_limit:.2f}", border=False, delta = upper_limit_delta, delta_color='inverse')
                plot_stock_data(historical_data, ticker_input, stock_info['company_name'], lower_limit, upper_limit)

            elif stock_info is None and not historical_data:
                st.info("Please enter a valid ticker symbol.")
        else:
            st.info("Please enter a stock ticker symbol to get started!")


#------------------------------------------------------------------------------#
#------------------------------------------------------------------------------#
#------------------------------------------------------------------------------#
# --- MAIN 
#------------------------------------------------------------------------------#
#------------------------------------------------------------------------------#
st.set_page_config(layout="wide", page_title="Stock Price Viewer", page_icon="📈")

st.title("📈 Stock Price Viewer + Alerting")


# Sidebar for user inputs
st.sidebar.header("Input Parameters")
#ticker_input = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL, MSFT, GOOGL)", "MSTY").upper()
#ticker_input = st.sidebar.text_input("Enter Stock Ticker2 (e.g., AAPL, MSFT, GOOGL)", "MSTY").upper()
num_days_input = st.sidebar.slider("Number of Historical Days to Show", 1, 90, 5)

# Loop through and display ACTIVE alerts only 
top_row,top_row_c2 = st.columns(2)
main_col1, main_col2 = st.columns(2)
for i, ticker in enumerate(st.session_state.active_alerts):
    if i % 2 == 0:  # Even index, put in main_col1
        with main_col1:
            create_monitor_card(ticker)
    else:  # Odd index, put in main_col2
        with main_col2:
            create_monitor_card(ticker)
with top_row:
    get_all_current_alerts()

