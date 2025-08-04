import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from plotly.subplots import make_subplots
import db.stock_lists as stock_lists
import io 
 # Often useful for more granular control

st.set_page_config(layout="wide", page_title="Dividend Ex-Date Price Analysis")

st.title("Stock Price Behavior Around Dividend Ex-Dates")

# Sidebar for user input
st.sidebar.header("Stock Selection")
ticker_symbol = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL, MSFT)", "MSTY").upper()
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2020-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))

# Function to fetch data and perform analysis
@st.cache_data(ttl='1 hour')
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
        price_data = stock.history(start=start_ts_for_history, end=end_ts_for_history, actions=False, auto_adjust=False) # actions=False to not get dividend/stock split columns here
        
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
        # Some custom calcs 
        df_results["inv(Dividend Amount)"] =  df_results["Dividend Amount"]*(-1) 

        # Set index 
        df_results.set_index("Ex-Dividend Date", inplace=True)
        return df_results, None
    except Exception as e:
        return None, f"Error fetching data: {e}"

# BOX PLOTS FOr absolute Price Change at Open vs Close
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # Import graph_objects for adding traces
import streamlit as st
import io
from scipy.stats import t, shapiro # Import t for Student's t-distribution calculations

def box_plot_compare(df, col1, col2, title):
    """
    Generates a box plot comparing two columns and their difference,
    and calculates normal distribution metrics for each, displaying them
    directly on the plot. It also adds the cumulative probability of a
    value being greater than 0, assuming a Student's t-distribution,
    and the results of the Shapiro-Wilk test for normality.
    The +/- standard deviation points are now based on the Student's t-distribution's
    properties (scaled by the sample standard deviation).
    The plot is rendered directly using Streamlit.

    Args:
        df (pd.DataFrame): The input DataFrame.
        col1 (str): The name of the first column for comparison (e.g., 'At Open').
        col2 (str): The name of the second column for comparison (e.g., 'At Close').
        title (str): The title for the plotly chart.
    """
    # Calculate the 'Difference' column
    df['Difference'] = df[col2] - df[col1]

    # Melt the DataFrame for plotting
    df_melted = df.melt(
        value_vars=[col1, col2, 'Difference'],
        var_name="Metric",
        value_name="Price Change ($)"
    )
    # Rename the 'Metric' values for better readability on the plot
    metric_labels = {
        col1: "At Open",
        col2: "At Close",
        "Difference": "Close - Open Difference"
    }
    df_melted["Metric"] = df_melted["Metric"].replace(metric_labels)

    # Create the box plot
    fig = px.box(
        df_melted,
        x="Metric",
        y="Price Change ($)",
        title=title,
        points="all", # Show all individual data points
        color="Metric" # Differentiate the box plots by color
    )
    fig.update_layout(
        yaxis_title="Price Change ($)", # Consistent y-axis title
        showlegend=True # Legend is redundant when 'x' and 'color' are the same
    )
    # Add a horizontal line at y=0
    fig.add_hline(y=0, line_dash="dot", line_color="red", annotation_text="", opacity=0.25, annotation_position="bottom right")

    # --- Calculate and Add Normal Distribution Metrics to the Plot ---
    metrics_to_analyze = {
        "At Open": df[col1],
        "At Close": df[col2],
        "Close - Open Difference": df['Difference']
    }

    for original_col_name, data_series in metrics_to_analyze.items():
        # Get the corresponding label used in the plot
        metric_label = metric_labels[original_col_name] if original_col_name in metric_labels else original_col_name

        mean_val = data_series.mean()
        std_val = data_series.std() # Sample standard deviation

        # Find the x-axis position for the current metric label
        x_pos = metric_label # Use the label directly as x-coordinate for categorical axis

        # Add mean marker
        fig.add_trace(
            go.Scatter(
                x=[x_pos],
                y=[mean_val],
                mode='markers',
                marker=dict(symbol='star', size=12, color='black'),
                name=f'{metric_label} Mean',
                showlegend=True
            )
        )

        # Determine the standard deviation to use for plotting the +/- sigma points.
        # This will be the sample standard deviation, potentially scaled if n-1 > 2
        # to reflect the wider tails of a t-distribution.
        std_for_sigma_points = std_val # Default to sample standard deviation

        n = len(data_series)
        if n - 1 > 2: # Degrees of freedom must be > 2 for the t-distribution variance to be finite
            df_for_std_calc = n - 1
            # The variance of a standard t-distribution is df / (df - 2).
            # We scale the *sample* standard deviation by the ratio of the
            # theoretical t-distribution's standard deviation (sqrt(df/(df-2)))
            # to the standard deviation of a standard normal distribution (1).
            # This makes the displayed sigma points wider for smaller sample sizes (smaller df),
            # reflecting the heavier tails of the t-distribution.
            t_dist_scale_factor = ((df_for_std_calc) / (df_for_std_calc - 2))**0.5
            std_for_sigma_points = std_val * t_dist_scale_factor

        # Add standard deviation markers using std_for_sigma_points
        std_dev_points = [
            mean_val - 3 * std_for_sigma_points, mean_val - 2 * std_for_sigma_points, mean_val - std_for_sigma_points,
            mean_val + std_for_sigma_points, mean_val + 2 * std_for_sigma_points, mean_val + 3 * std_for_sigma_points
        ]
        std_dev_labels = [
            '-3σ', '-2σ', '-1σ',
            '+1σ', '+2σ', '+3σ'
        ]

        for i, val in enumerate(std_dev_points):
            fig.add_trace(
                go.Scatter(
                    x=[x_pos],
                    y=[val],
                    mode='markers',
                    marker=dict(symbol='circle', size=8, color='grey', line=dict(width=1, color='DarkSlateGrey')),
                    name=f'{metric_label} {std_dev_labels[i]}',
                    showlegend=True
                )
            )

        # --- Calculate and Add Cumulative Probability (P(X > 0)) using Student's t-distribution ---
        prob_greater_than_zero_text = ""
        if std_val > 0 and n > 1: # Ensure std_dev is not 0 and enough data for df > 0
            df_t = n - 1 # Degrees of freedom for t-distribution
            std_err = std_val / (n**0.5) # Standard error of the mean

            if std_err == 0: # Handle cases where std_err might be 0 (e.g., if std_val was tiny)
                if mean_val > 0:
                    prob_greater_than_zero = 1.0
                else:
                    prob_greater_than_zero = 0.0
            else:
                t_statistic = (0 - mean_val) / std_val # std error means that X is the mean not X bar, use std_val for predictive statistics 
                prob_greater_than_zero = 1 - t.cdf(t_statistic, df=df_t)

            prob_greater_than_zero_text = f'P(X > 0) (t-dist): {prob_greater_than_zero:.2%}'
        else:
            # Handle cases where std_dev is 0 or not enough data for t-dist (n <= 1)
            if mean_val > 0:
                prob_greater_than_zero_text = 'P(X > 0): 100.00%'
            elif mean_val == 0:
                prob_greater_than_zero_text = 'P(X > 0): 0.00%'
            else:
                prob_greater_than_zero_text = 'P(X > 0): 0.00%'

        # Add P(X > 0) annotation
        fig.add_annotation(
            x=x_pos,
            y=df_melted["Price Change ($)"].max() * 1.05, # Position slightly above the max y-value of the data
            text=prob_greater_than_zero_text,
            showarrow=False,
            yshift=10, # Shift up slightly
            font=dict(size=10, color="darkblue"),
            bgcolor="rgba(255, 255, 255, 0.7)", # Semi-transparent background
            bordercolor="darkblue",
            borderwidth=1,
            borderpad=4,
            xref="x",
            yref="y"
        )

        # --- Add Shapiro-Wilk Test for Normality ---
        shapiro_test_text = ""
        if n >= 3: # Shapiro-Wilk test requires at least 3 data points
            try:
                shapiro_stat, shapiro_p = shapiro(data_series)
                shapiro_test_text = f'Shapiro-Wilk: p={shapiro_p:.3f}'
            except Exception as e:
                shapiro_test_text = f'Shapiro-Wilk: Error ({e})'
        else:
            shapiro_test_text = 'Shapiro-Wilk: N < 3'

        # Add Shapiro-Wilk annotation
        fig.add_annotation(
            x=x_pos,
            y=df_melted["Price Change ($)"].min() * 1.05, # Same y-position as P(X>0) initially
            text=shapiro_test_text,
            showarrow=False,
            yshift=-5, # Shift down from the P(X>0) annotation
            font=dict(size=10, color="darkgreen"),
            bgcolor="rgba(255, 255, 255, 0.7)",
            bordercolor="darkgreen",
            borderwidth=1,
            borderpad=4,
            xref="x",
            yref="y"
        )


    # Display the plot directly within the function
    st.plotly_chart(fig, use_container_width=True)

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

@st.cache_data(ttl='6 hours')
def get_intraday_stock_data(ticker: str, start_date, end_date, interval: str = "60m") -> pd.DataFrame:
    try:
        # Convert date strings to datetime objects
        start_dt = start_date # Assuming start_date is already a datetime object
        end_dt = end_date # Assuming end_date is already a datetime object

        # Calculate the difference in days
        delta = end_dt - start_dt
        period_days = delta.days + 1

        if interval == "1m" and period_days > 7:
            print(f"Warning: For '1m' interval, yfinance typically provides data for the last 7 days only.")
            print(f"Adjusting period to 7 days from {end_date}.")
            adjusted_start_dt = end_dt - timedelta(days=6)
            # Ensure adjusted_start_dt is not before the original start_dt
            if adjusted_start_dt < start_dt:
                adjusted_start_dt = start_dt
            start_date_yf = adjusted_start_dt.strftime("%Y-%m-%d")
        elif interval in ["5m", "15m", "30m", "60m", "90m", "1h"] and period_days > 60:
            print(f"Warning: For '{interval}' interval, yfinance typically provides data for up to 60 days.")
            print(f"Adjusting period to 60 days from {end_date}.")
            adjusted_start_dt = end_dt - timedelta(days=59)
            if adjusted_start_dt < start_dt:
                adjusted_start_dt = start_dt
            start_date_yf = adjusted_start_dt.strftime("%Y-%m-%d")
        else:
            start_date_yf = start_date.strftime("%Y-%m-%d") # Ensure this is a string for yfinance

        # Fetch data
        data = yf.download(
            ticker,
            start=start_date_yf,
            end=(end_dt + timedelta(days=1)).strftime("%Y-%m-%d"), # yfinance `end` is exclusive
            interval=interval,
            auto_adjust=True  # Automatically adjust Open, High, Low, Close for dividends and splits
        )
        if isinstance(data.columns, pd.MultiIndex):
            # This handles cases where yfinance might return (Ticker, Column_Name)
            # We want to keep only the Column_Name
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
        
        if data.empty:
            print(f"No data found for {ticker} from {start_date} to {end_date} with interval {interval}.")
            return pd.DataFrame()
        
        # --- Add the new column for relative difference ---
        if 'Open' in data.columns and not data['Open'].empty:
            first_open_value = data['Open'].iloc[0]
            data['Open_Relative_to_Start'] = data['Open'] - first_open_value
        else:
            print(f"Warning: 'Open' column not found or is empty, cannot calculate relative difference.")
            data['Open_Relative_to_Start'] = float('nan') # Add a column of NaNs if 'Open' is missing
        # --- End of new column addition ---

        return data
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame()

def generate_multi_line_plot(df_high_res, yfield='Open'):
    if not df_high_res.empty:
        fig = px.line( # Using line for time series, scatter is also an option
            df_high_res,
            color='date_color', # Column name in df_high_res for coloring
            x='sort_field',           # Column name in df_high_res for x-axis
            y=yfield,           # Column name in df_high_res for y-axis
            title=f'{ticker_symbol} Intraday Trends Around Ex-Dividend Dates',
            hover_data=[yfield, 'Date', 'Time'] 
        )
        # --- 3. Calculate division points and add vertical lines ---

        # Get the min and max of the x-axis ('sort_field')
        x_min = df_high_res['sort_field'].min()
        x_max = df_high_res['sort_field'].max()
        x_range = x_max - x_min
        section_size = x_range / 3
        # Calculate the x-coordinates for the two vertical lines
        line1_x = x_min + section_size
        line2_x = x_min + (section_size * 2)

        # Add the first vertical line
        fig.add_vline(
            x=line1_x,
            line_dash="dot",
            opacity=0.5,
            line_color="grey", # Using red to distinguish from previous example
            annotation_text="Ex Day Start", # Optional annotation
            annotation_position="top left"
        )
        # Add the second vertical line
        fig.add_vline(
            x=line2_x,
            line_dash="dot",
            opacity=0.5,
            line_color="grey", # Using green
            annotation_text="Ex Day End", # Optional annotation
            annotation_position="top right"
        )
        # Update layout for better readability
        st.plotly_chart(fig)
    else:
        st.write("Cannot display chart: No high-resolution data available.")


import pandas as pd
import plotly.graph_objects as go
import plotly.express as px # Still useful for colors
from datetime import datetime, timedelta
import streamlit as st # Assuming you are using Streamlit based on ts_col1
import numpy as np # For adding noise to sample data

def generate_hourly_daily_distribution_plot(df_high_res, yfield='Open_Relative_to_Start', ticker_symbol="STOCK"):
    if not df_high_res.empty:
        # Initialize an empty Figure object
        fig = go.Figure()

        # Ensure 'Date' column is a string for consistent grouping and naming
        if pd.api.types.is_datetime64_any_dtype(df_high_res['Date']):
            df_high_res['Date'] = df_high_res['Date'].dt.strftime('%Y-%m-%d')


        # Extract hour directly from the datetime.time object
        df_high_res['Hour'] = df_high_res['Time'].apply(lambda t: t.hour)

        # Get unique dates for consistent coloring (now guaranteed to be strings)
        unique_dates_for_coloring = sorted(df_high_res['Date'].unique())
        
        # Add a placeholder trace for the legend if you want to show date colors
        for i, date_str in enumerate(unique_dates_for_coloring):
            color = px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
            fig.add_trace(go.Scatter(
                x=[None], # No actual data, just for legend entry
                y=[None],
                mode='lines',
                line=dict(color=color, width=2),
                name=str(date_str), # <--- Changed this line: Convert to string
                showlegend=True
            ))

        # Iterate through each date and then each hour within that date
        for date_str in unique_dates_for_coloring:
            df_day = df_high_res[df_high_res['Date'] == date_str].copy() # Use .copy() to avoid SettingWithCopyWarning
            
            # Calculate the mean sort_field for each hour within this specific day
            hourly_mean_sort_field_for_day = df_day.groupby('Hour')['sort_field'].mean()

            # Determine the color for this specific date (consistent with original line plot idea)
            color_index = unique_dates_for_coloring.index(date_str)
            current_day_color = px.colors.qualitative.Plotly[color_index % len(px.colors.qualitative.Plotly)]

            for hour in sorted(df_day['Hour'].unique()):
                df_hour_on_day = df_day[df_day['Hour'] == hour]
                
                # Check if there's data for this hour on this day
                if not df_hour_on_day.empty:
                    box_x_position = hourly_mean_sort_field_for_day.loc[hour]

                    # Add Violin plot (or go.Box for box plots)
                    fig.add_trace(go.Violin(
                        y=df_hour_on_day[yfield],
                        x=[box_x_position] * len(df_hour_on_day), # Single x-position for the violin/box
                        name=f'{str(date_str)} - {hour:02d}:00', # Convert to string here too for consistency
                        box_visible=True, # Show the box inside the violin
                        meanline_visible=True, # Show the mean line
                        line_color=current_day_color, # Outline color for the violin/box
                        fillcolor=f'rgba{px.colors.hex_to_rgb(current_day_color) + (0.3,)}', # Semi-transparent fill
                        opacity=0.8, # Overall opacity of the violin/box
                        points='all', # Show all data points
                        jitter=0.3, # Spread out points for better visibility
                        marker=dict(color=current_day_color, size=3), # Color of individual points
                        scalemode='width', # 'width' or 'count'
                        scalegroup='hour', # Groups violins/boxes by hour so they are scaled relatively
                        showlegend=False # Don't show individual violin/box legends
                    ))

        # Add vertical lines (calculated from the full df_high_res)
        x_min = df_high_res['sort_field'].min()
        x_max = df_high_res['sort_field'].max()
        x_range = x_max - x_min
        section_size = x_range / 3
        line1_x = x_min + section_size
        line2_x = x_min + (section_size * 2)

        fig.add_vline(
            x=line1_x,
            line_dash="dot",
            opacity=0.5,
            line_color="grey",
            annotation_text="Ex Day Start",
            annotation_position="top left"
        )
        fig.add_vline(
            x=line2_x,
            line_dash="dot",
            opacity=0.5,
            line_color="grey",
            annotation_text="Ex Day End",
            annotation_position="top right"
        )
        
        # Update layout
        fig.update_layout(
            title_text=f'{ticker_symbol} Intraday Distribution by Hour and Day',
            xaxis_title="Time Offset (sort_field)",
            yaxis_title=f"{yfield}",
            hovermode="x unified",
            xaxis_showgrid=True, # Show grid for x-axis
            yaxis_showgrid=True, # Show grid for y-axis
            violinmode='overlay', # 'group' or 'overlay'. 'overlay' is good here.
        )

        st.plotly_chart(fig)





#------------------------------------------------------------#
#--------------------------- MAIN ---------------------------#
#------------------------------------------------------------#

tab_single, tab_multi = st.tabs(['Single Stock Analysis', 'Dividend Lists'])

with tab_single:
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

        # Scatter plot: Dividend Amount vs. Price Change at Open vs. Close (Percentage)
        st.subheader("Comparison of Price Change Distributions")
        c_col1,c_col2 = st.columns(2)
    

        box_plot_compare(df_dividend_analysis, "Difference from Dividend (Open vs Dividend)", 
                        "Difference from Dividend (Close vs Dividend)", 
                        "Comparison of Price Change + Dividend at Open vs. Close")
        box_plot_compare(df_dividend_analysis, "Price Change Open (Absolute)", "Price Change Close (Absolute)", "Comparison of Absolute Price Change at Open vs. Close")

        #---------------------------------------------------------------#
        # Line chart: Absolute Price Changes (Open vs Close) and Dividend Amount Over Time
        ts_col1, ts_col2 = st.columns(2)
        fig_line_abs_combined = px.line(
            df_dividend_analysis,
            y=["Price Change Open (Absolute)", "Price Change Close (Absolute)", "Dividend Amount","inv(Dividend Amount)"],
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
            y=["Difference from Dividend (Open vs Dividend)","Difference from Dividend (Close vs Dividend)"],
            title="Difference from Dividend over Time"
        )
        ts_col2.plotly_chart(fig_line_perc_combined, use_container_width=True)

 
        # ----------- Get high resolution trends --------------- #
        # 3. Filter the list
        ex_dates_list = sorted(df_dividend_analysis.index.tolist(), reverse=True)
        current_date = datetime.today().date()

        # Calculate two_years_ago as a datetime.datetime, then extract its date part
        two_years_ago = (current_date - timedelta(days=2 * 365))

        # Filter the list: Assuming 'date' in ex_dates_list is already a datetime.date object,
        # compare it directly with the 'two_years_ago' date.
        ex_dates_list = [date for date in ex_dates_list if date >= two_years_ago]

        # Initialize an empty list to store DataFrames
        all_high_res_dfs = []

        for sdate_ts in ex_dates_list: # sdate_ts will be a Timestamp object
            sdate_str = sdate_ts  #.strftime('%Y-%m-%d') 
            
            try:
                df_high_res_i = get_intraday_stock_data(ticker_symbol, sdate_str + timedelta(days=-1), sdate_str + timedelta(days=1))
                df_high_res_i['sort_field'] = range(len(df_high_res_i))  # Add a sort field for consistent ordering


                if not df_high_res_i.empty:
                    # Add 'date_color' column using the original Timestamp object for better grouping/coloring
                    # The Timestamp will be useful for plotting as well
                    df_high_res_i['date_color'] = sdate_ts 
                    
                    # Reset index to make the 'Datetime' index a regular column, useful for plotting 'x' axis
                    df_high_res_i = df_high_res_i.reset_index() 
                    df_high_res_i.rename(columns={'Datetime': 'Date'}, inplace=True) # Rename for clarity
                    
                    all_high_res_dfs.append(df_high_res_i)
                else:
                    print(f"No data found for {ticker_symbol} on {sdate_str}. Skipping.")
            except Exception as e: # Catch a more specific exception or at least log the error
                print(f"An error occurred while fetching data for {sdate_str}: {e}")
                continue
        
        # Concatenate all collected DataFrames into one
        if all_high_res_dfs: # Check if the list is not empty
            df_high_res = pd.concat(all_high_res_dfs, ignore_index=True) # ignore_index=True resets the index
        else:
            df_high_res = pd.DataFrame() # Create an empty DataFrame if no data was collected
            print("No intraday data was retrieved for any of the dividend ex-dates.")

        # --- Plotting the high-resolution trends ---
        # create time column:
        df_high_res['Time'] = df_high_res['Date'].dt.time
        with ts_col1:
            generate_multi_line_plot(df_high_res, yfield='Open_Relative_to_Start') # This will plot the new column we added
        with ts_col2:
            generate_multi_line_plot(df_high_res, yfield='Open')
        
        
        # generate_hourly_daily_distribution_plot(df_high_res, yfield='Open_Relative_to_Start', ticker_symbol=ticker_symbol)

    else:
        st.info("Enter a stock ticker and select a date range to see the dividend analysis.")

with tab_multi:
    choose_stock_list = st.selectbox('Select list of interest',stock_lists.nav_erosion_stocks.keys(), index=0)
    selected_stocks = stock_lists.nav_erosion_stocks[choose_stock_list]
    lc1,lc2,lc3 = st.columns([1,1,2])
    if lc1.button("Analyze Selected Stocks"):
        for stock in selected_stocks:
            df_dividend_analysis, error_message = get_dividend_data(stock, start_date, end_date)
            if error_message:
                st.error(f"Error for {stock}: {error_message}")
            elif df_dividend_analysis is not None and not df_dividend_analysis.empty:
                box_plot_compare(df_dividend_analysis, "Difference from Dividend (Open vs Dividend)", 
                            "Difference from Dividend (Close vs Dividend)", 
                            f"[{stock}]Comparison of Price Change + Dividend at Open vs. Close")
            else:
                st.info(f"No dividend data found for {stock} in the selected period.")
    lc2.link_button("Go to Yield Max Schedule", "https://www.yieldmaxetfs.com/distribution-schedule/") 
