import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# Set Streamlit page configuration
st.set_page_config(layout="wide", page_title="Stock Comparator")

st.title("Stock Comparison Dashboard")
st.markdown("""
This application allows you to compare multiple stock tickers.

Here's what you'll see:
1.  **Current P/E Ratio:** The trailing P/E ratio based on the latest available data.
2.  **Historical Closing Prices:** A chart showing how the stock prices have moved over time.
3.  **Historical P/E Ratios:** A chart showing the P/E ratio over time, calculated by dividing the daily closing price by the Trailing Twelve Months (TTM) Earnings Per Share (EPS). The TTM EPS is derived from quarterly financial reports, so the P/E value will update only when new earnings are released.
""")

# User input for stock tickers
st.header("Enter Stock Tickers")
ticker_input = st.text_area(
    "Enter stock tickers separated by commas (e.g., AAPL, MSFT, GOOGL)",
    "AAPL, MSFT, GOOGL"
)

# Convert input string to a list of tickers, removing whitespace
tickers = [ticker.strip().upper() for ticker in ticker_input.split(',') if ticker.strip()]

if tickers:
    st.subheader("Fetching Data...")

    # Dictionary to store current P/E ratios
    current_pe_ratios = {}
    # DataFrame to store historical closing prices
    historical_prices_df = pd.DataFrame()
    # DataFrame to store historical P/E ratios
    historical_pe_df = pd.DataFrame()

    for ticker_symbol in tickers:
        try:
            # Create a Ticker object
            ticker = yf.Ticker(ticker_symbol)

            # --- Fetch Current P/E Ratio ---
            info = ticker.info
            if 'trailingPE' in info:
                current_pe_ratios[ticker_symbol] = info['trailingPE']
            else:
                current_pe_ratios[ticker_symbol] = "N/A"
                st.warning(f"Could not find current P/E for {ticker_symbol}. It might not be available or the ticker is invalid.")

            # --- Fetch Historical Price Data ---
            # Fetch historical data (e.g., last 2 years to ensure enough EPS data)
            hist_data = ticker.history(period="2y")
            if hist_data.empty:
                st.warning(f"No historical price data found for {ticker_symbol}. Please check the ticker symbol.")
                continue # Skip to next ticker if no price data

            # Prepare historical prices for merging
            hist_data_close = hist_data[['Close']].reset_index()
            hist_data_close['Date'] = pd.to_datetime(hist_data_close['Date'])
            hist_data_close.rename(columns={'Close': ticker_symbol}, inplace=True)

            if historical_prices_df.empty:
                historical_prices_df = hist_data_close
            else:
                historical_prices_df = pd.merge(historical_prices_df, hist_data_close, on='Date', how='outer')


            # --- Calculate Historical P/E Ratio ---
            # Fetch quarterly financial statements (Income Statement)
            # This is often more reliable for EPS than quarterly_earnings
            quarterly_financials = ticker.quarterly_financials
            
            if quarterly_financials is not None and not quarterly_financials.empty:
                # Ensure 'Date' is datetime and sort by date descending
                # The index of quarterly_financials is usually the date
                quarterly_financials = quarterly_financials.T # Transpose to make dates the index
                quarterly_financials.index = pd.to_datetime(quarterly_financials.index)
                quarterly_financials = quarterly_financials.sort_index(ascending=False) # Sort by date descending

                # Try to get 'Basic EPS' or 'Diluted EPS'
                eps_data = None
                if 'Basic EPS' in quarterly_financials.columns:
                    eps_data = quarterly_financials['Basic EPS']
                elif 'Diluted EPS' in quarterly_financials.columns:
                    eps_data = quarterly_financials['Diluted EPS']
                
                if eps_data is not None and not eps_data.empty:
                    # Create a DataFrame for TTM EPS
                    ttm_eps_list = []
                    for i in range(len(eps_data)):
                        current_period_date = eps_data.index[i]
                        # Sum the EPS for the current quarter and the three preceding ones
                        # Ensure we have at least 4 quarters
                        if i + 4 <= len(eps_data):
                            ttm_eps = eps_data.iloc[i:i+4].sum()
                            ttm_eps_list.append({'Date': current_period_date, 'TTM_EPS': ttm_eps})
                    
                    ttm_eps_df = pd.DataFrame(ttm_eps_list)
                    ttm_eps_df['Date'] = pd.to_datetime(ttm_eps_df['Date'])
                    ttm_eps_df = ttm_eps_df.sort_values(by='Date').set_index('Date') # Sort ascending for merging
                    
                    # Merge historical prices with TTM EPS
                    # Use the index of hist_data (which is Date) for merging
                    merged_data = hist_data.reset_index()
                    # Ensure the 'Date' column is timezone-naive for consistent merging
                    merged_data['Date'] = pd.to_datetime(merged_data['Date']).dt.tz_localize(None) 
                    merged_data = pd.merge_asof(merged_data.sort_values('Date'), 
                                                ttm_eps_df.reset_index().sort_values('Date'), 
                                                on='Date', direction='backward')
                    
                    # Forward fill TTM_EPS so it holds constant between earnings reports
                    merged_data['TTM_EPS'] = merged_data['TTM_EPS'].ffill()
                    
                    # Calculate P/E ratio
                    # Avoid division by zero or negative EPS
                    merged_data[f'{ticker_symbol}_PE'] = merged_data.apply(
                        lambda x: x['Close'] / x['TTM_EPS'] if x['TTM_EPS'] is not None and x['TTM_EPS'] > 0 else None,
                        axis=1
                    )
                    
                    # Select only Date and the calculated P/E
                    pe_data_for_ticker = merged_data[['Date', f'{ticker_symbol}_PE']]
                    
                    if historical_pe_df.empty:
                        historical_pe_df = pe_data_for_ticker
                    else:
                        historical_pe_df = pd.merge(historical_pe_df, pe_data_for_ticker, on='Date', how='outer')
                else:
                    st.warning(f"Could not find 'Basic EPS' or 'Diluted EPS' in quarterly financials for {ticker_symbol}.")
            else:
                st.warning(f"No quarterly financial statements found for {ticker_symbol} to calculate historical P/E.")

        except Exception as e:
            st.error(f"Error fetching or processing data for {ticker_symbol}: {e}")

    # Display Current P/E Ratios
    if current_pe_ratios:
        st.header("Current P/E Ratios")
        pe_df = pd.DataFrame.from_dict(current_pe_ratios, orient='index', columns=['Trailing P/E'])
        st.dataframe(pe_df)

    # Display Historical Price Chart
    if not historical_prices_df.empty:
        st.header("Historical Closing Prices Comparison (Last 2 Years)")

        # Melt the DataFrame for Plotly Express to plot multiple lines
        historical_prices_df['Date'] = pd.to_datetime(historical_prices_df['Date'])
        value_vars_prices = [col for col in historical_prices_df.columns if col != 'Date']
        melted_prices_df = historical_prices_df.melt(id_vars=['Date'], value_vars=value_vars_prices, var_name='Ticker', value_name='Closing Price')

        fig_prices = px.line(
            melted_prices_df,
            x="Date",
            y="Closing Price",
            color="Ticker",
            title="Historical Closing Prices",
            labels={"Date": "Date", "Closing Price": "Closing Price ($)"},
            hover_data={"Date": "|%Y-%m-%d", "Closing Price": ":.2f", "Ticker": True}
        )
        fig_prices.update_xaxes(rangeslider_visible=True)
        fig_prices.update_layout(hovermode="x unified")
        st.plotly_chart(fig_prices, use_container_width=True)
    else:
        st.info("Enter valid stock tickers above to see data.")

    # Display Historical P/E Ratio Chart
    if not historical_pe_df.empty:
        # Drop rows where all P/E values are None (e.g., if no data for any ticker on that date)
        historical_pe_df.dropna(how='all', subset=[col for col in historical_pe_df.columns if col != 'Date'], inplace=True)
        
        if not historical_pe_df.empty:
            st.header("Historical P/E Ratios Comparison (Last 2 Years)")

            # Melt the DataFrame for Plotly Express to plot multiple lines
            historical_pe_df['Date'] = pd.to_datetime(historical_pe_df['Date'])
            value_vars_pe = [col for col in historical_pe_df.columns if col != 'Date']
            melted_pe_df = historical_pe_df.melt(id_vars=['Date'], value_vars=value_vars_pe, var_name='Ticker', value_name='P/E Ratio')

            fig_pe = px.line(
                melted_pe_df,
                x="Date",
                y="P/E Ratio",
                color="Ticker",
                title="Historical P/E Ratios",
                labels={"Date": "Date", "P/E Ratio": "P/E Ratio"},
                hover_data={"Date": "|%Y-%m-%d", "P/E Ratio": ":.2f", "Ticker": True}
            )
            fig_pe.update_xaxes(rangeslider_visible=True)
            fig_pe.update_layout(hovermode="x unified")
            st.plotly_chart(fig_pe, use_container_width=True)
        else:
            st.info("No sufficient historical P/E data found for the selected tickers.")
    else:
        st.info("No historical P/E data could be calculated for the selected tickers.")

else:
    st.info("Please enter at least one stock ticker to get started.")

