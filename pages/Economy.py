

from fredapi import Fred

# Replace 'YOUR_API_KEY' with your actual FRED API key
api_key = 'YOUR_API_KEY'
fred = Fred(api_key=api_key)

# Example 1: Retrieve information about a specific series
series_id = 'GDPC1'  # Real Gross Domestic Product, 1 Decimal
data = fred.get_series_info(series_id)
print("Information about series '{}'".format(series_id))
print(data)
print()

# Example 2: Retrieve historical data for a series
start_date = '2020-01-01'
end_date = '2021-12-31'
data = fred.get_series(series_id, start_date=start_date, end_date=end_date)
print("Historical data for series '{}' from {} to {}".format(series_id, start_date, end_date))
print(data)