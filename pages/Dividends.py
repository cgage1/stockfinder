import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide", page_title="Dividend Ex-Date Price Analysis")

st.title("Stock Price Behavior Around Dividend Ex-Dates")

# Sidebar for user input
st.sidebar.header("Stock Selection")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL, MSFT)", "AAPL").upper()
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2010-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))

# Function to fetch data and perform analysis
@st.cache_data
def get_dividend_data(ticker, start, end):
    try:
        stock = yf.Ticker(ticker)
        
        # Get historical dividends
        dividends = stock.dividends
        # IMMEDIATELY remove timezone from dividend index upon fetching
        if not dividends.empty and dividends.index.tz is not None:
            dividends.index = dividends.index.tz_localize(None) 
        
        # Get historical stock prices (using 'Close' price)
        # Fetch a bit more data to ensure we have the day before the first ex-date
        # Convert start/end from datetime.date to naive pd.Timestamp for yfinance.history
        # This ensures yfinance receives naive Timestamps for its range
        start_ts_for_history = pd.Timestamp(start) - pd.Timedelta(days=7)
        end_ts_for_history = pd.Timestamp(end) + pd.Timedelta(days=1)
        
        # Fetch 'Open' and 'Close' prices
        price_data = stock.history(start=start_ts_for_history, end=end_ts_for_history, actions=False) # actions=False to not get dividend/stock split columns here
        
        # IMMEDIATELY remove timezone from price_data index upon fetching
        if not price_data.empty and price_data.index.tz is not None:
            price_data.index = price_data.index.tz_localize(None)

        # Now, use naive Timestamps for filtering the dividends DataFrame
        # Both dividends.index and the comparison dates (start_ts, end_ts) are now naive
        start_ts_filter = pd.Timestamp(start)
        end_ts_filter = pd.Timestamp(end)
        dividends = dividends[(dividends.index >= start_ts_filter) & (dividends.index <= end_ts_filter)]
        
        if dividends.empty:
            return None, "No dividend data found for the selected period."

        if price_data.empty:
            return None, "No price data found for the selected period."

        results = []
        for ex_date, dividend_amount in dividends.items():
            # 'ex_date' here is already a naive pd.Timestamp because dividends.index was localized
            
            # Calculate day before ex-date (will also be naive pd.Timestamp)
            day_before_ex_date = ex_date - pd.Timedelta(days=1)
            
            # Find the actual trading day before the ex-date if the day before is a weekend/holiday
            # Now, both day_before_ex_date and price_data.index are naive Timestamps, allowing direct comparison
            while day_before_ex_date not in price_data.index and day_before_ex_date >= price_data.index.min():
                day_before_ex_date -= pd.Timedelta(days=1)
            
            # Ensure the calculated dates actually exist in the price data index
            # Both are now naive Timestamps, so direct lookup should work
            if day_before_ex_date in price_data.index and ex_date in price_data.index:
                price_day_before_close = price_data.loc[day_before_ex_date]['Close']
                price_on_ex_date_open = price_data.loc[ex_date]['Open']
                price_on_ex_date_close = price_data.loc[ex_date]['Close']
                
                # Change based on previous day's close vs. ex-date open
                price_change_at_open = price_on_ex_date_open - price_day_before_close
                # Change based on previous day's close vs. ex-date close
                price_change_at_close = price_on_ex_date_close - price_day_before_close

                percentage_change_at_open = (price_change_at_open / price_day_before_close) * 100 if price_day_before_close != 0 else 0
                percentage_change_at_close = (price_change_at_close / price_day_before_close) * 100 if price_day_before_close != 0 else 0

                results.append({
                    "Ex-Dividend Date": ex_date.date(), # Store as plain Python date object for clarity in DataFrame
                    "Dividend Amount": dividend_amount,
                    "Price Day Before Close": price_day_before_close,
                    "Price On Ex-Date Open": price_on_ex_date_open,
                    "Price On Ex-Date Close": price_on_ex_date_close,
                    "Price Change Open (Absolute)": price_change_at_open,
                    "Price Change Close (Absolute)": price_change_at_close,
                    "Price Change Open (%)": percentage_change_at_open,
                    "Price Change Close (%)": percentage_change_at_close, # Corrected key
                    "Difference from Dividend (Open vs Dividend)": price_change_at_open + dividend_amount,
                    "Difference from Dividend (Close vs Dividend)": price_change_at_close + dividend_amount
                })
        
        if not results:
            return None, "Could not find corresponding price data for all ex-dividend dates within the selected range."

        df_results = pd.DataFrame(results)
        df_results.set_index("Ex-Dividend Date", inplace=True)
        return df_results, None
    except Exception as e:
        return None, f"Error fetching data: {e}"

df_dividend_analysis, error_message = get_dividend_data(ticker_symbol, start_date, end_date)

if error_message:
    st.error(error_message)
elif df_dividend_analysis is not None and not df_dividend_analysis.empty:
    st.subheader(f"Analysis for {ticker_symbol}")
    st.dataframe(df_dividend_analysis.style.format({
        "Dividend Amount": "{:.2f}",
        "Price Day Before Close": "{:.2f}",
        "Price On Ex-Date Open": "{:.2f}",
        "Price On Ex-Date Close": "{:.2f}",
        "Price Change Open (Absolute)": "{:.2f}",
        "Price Change Close (Absolute)": "{:.2f}",
        "Price Change Open (%)": "{:.2f}%",
        "Price Change Close (%)": "{:.2f}%",
        "Difference from Dividend (Open vs Dividend)": "{:.2f}",
        "Difference from Dividend (Close vs Dividend)": "{:.2f}"
    }))

    st.markdown("""
    **Explanation of 'Difference from Dividend'**:
    This metric measures how much the price change around the ex-dividend date deviates from the dividend amount itself.
    * A **positive** value indicates the stock price dropped *more* than the dividend amount (or even increased).
    * A **negative** value indicates the stock price dropped *less* than the dividend amount (or increased).
    * Ideally, in a perfectly efficient market, the price drop would equal the dividend amount, leading to a value close to zero.
    """)

    st.subheader("Distribution of Price Change vs. Dividend Payout")

    # Scatter plot: Dividend Amount vs. Price Change at Open vs. Close
    fig_scatter_open_close = px.scatter(
        df_dividend_analysis,
        x="Dividend Amount",
        y=["Price Change Open (Absolute)", "Price Change Close (Absolute)"],
        
        title="Dividend Amount vs. Absolute Price Change (Open vs. Close) Around Ex-Date",
        labels={
            "value": "Absolute Price Change ($)",
            "variable": "Price Change Type"
        }
    )
    fig_scatter_open_close.add_trace(go.Scatter(x=df_dividend_analysis["Dividend Amount"], y=-df_dividend_analysis["Dividend Amount"],
                                     mode='lines', name='Expected Price Drop (negative dividend)',
                                     line=dict(dash='dash', color='red')))
    st.plotly_chart(fig_scatter_open_close, use_container_width=True)
    st.markdown("The red dashed line represents the theoretical ideal scenario where the price drops exactly by the dividend amount.")

    st.subheader("Comparison of Price Change Distributions")
    c_col1,c_col2 = st.columns(2)
    # Histogram for Price Change at Open vs Dividend Difference
    fig_hist_open = px.histogram(
        df_dividend_analysis,
        x="Difference from Dividend (Open vs Dividend)",
        nbins=20,
        title="Distribution of Price Change (Open) Relative to Dividend Payout"
    )
    fig_hist_open.update_layout(xaxis_title="Price Change at Open - Dividend Amount")
    c_col1.plotly_chart(fig_hist_open, use_container_width=True)

    # Histogram for Price Change at Close vs Dividend Difference
    fig_hist_close = px.histogram(
        df_dividend_analysis,
        x="Difference from Dividend (Close vs Dividend)",
        nbins=20,
        title="Distribution of Price Change (Close) Relative to Dividend Payout"
    )
    fig_hist_close.update_layout(xaxis_title="Price Change at Close - Dividend Amount")
    c_col2.plotly_chart(fig_hist_close, use_container_width=True)

    st.subheader("Time Series of Price Changes and Dividend Payout")

    # Histogram for Price Change at Open vs Dividend Difference
    fig_hist_open = px.histogram(
        df_dividend_analysis,
        x="Price Change Open (Absolute)",
        nbins=20,
        title="Price Change Open (Absolute)"
    )
    fig_hist_open.update_layout(xaxis_title="Price Change at Open")
    c_col1.plotly_chart(fig_hist_open, use_container_width=True)

    fig_hist_open = px.histogram(
        df_dividend_analysis,
        x="Price Change Close (Absolute)",
        nbins=20,
        title="Price Change Close (Absolute)"
    )
    fig_hist_open.update_layout(xaxis_title="Price Change at Close")
    c_col2.plotly_chart(fig_hist_open, use_container_width=True)

    with c_col1:
        # Box plot for Price Change at Open (Absolute)
        fig_box_open = px.box(
            df_dividend_analysis,
            y="Price Change Open (Absolute)",
            title="Price Change at Open (Absolute) Distribution",
            points="all" # Show all data points as well
        )
        fig_box_open.update_layout(yaxis_title="Absolute Price Change ($)")
        st.plotly_chart(fig_box_open, use_container_width=True)

    with c_col2:
        # Box plot for Price Change at Close (Absolute)
        fig_box_close = px.box(
            df_dividend_analysis,
            y="Price Change Close (Absolute)",
            title="Price Change at Close (Absolute) Distribution",
            points="all" # Show all data points as well
        )
        fig_box_close.update_layout(yaxis_title="Absolute Price Change ($)")
        st.plotly_chart(fig_box_close, use_container_width=True)
    
    # Line chart: Absolute Price Changes (Open vs Close) and Dividend Amount Over Time
    ts_col1, ts_col2 = st.columns(2)
    fig_line_abs_combined = px.line(
        df_dividend_analysis,
        y=["Price Change Open (Absolute)", "Price Change Close (Absolute)", "Dividend Amount"],
        title="Absolute Price Changes (Open & Close) and Dividend Amount Over Time",
        labels={
            "value": "Amount ($)",
            "variable": "Metric"
        }
    )
    ts_col1.plotly_chart(fig_line_abs_combined, use_container_width=True)

    # Line chart: Percentage Price Changes (Open vs Close) Over Time
    fig_line_perc_combined = px.line(
        df_dividend_analysis,
        y=["Price Change Open (%)", "Price Change Close (%)"],
        title="Percentage Price Changes (Open & Close) Around Ex-Date Over Time",
        labels={
            "value": "Percentage Change (%)",
            "variable": "Price Change Type"
        }
    )
    ts_col2.plotly_chart(fig_line_perc_combined, use_container_width=True)

else:
    st.info("Enter a stock ticker and select a date range to see the dividend analysis.")

st.sidebar.markdown("---")
st.sidebar.markdown("Created by Gemini with Streamlit and yfinance")