## Desc 
Streamlit app to identify and analyze stocks 

### To do
- loadSymbolDailies.py :  UPDATE THIS CODE TO USE EXISTING MAX DATES TO PULL INCREMENTAL DATA! (also change file name to loadSymbolQuotes to match schema)
- Explore yfinance api data availability 
- Replace volatility chart B with % change day by (need to create new field w lag() )
- Bollinger bands
- Replace pandasql operations with duckDB
- Add Last update Date to top of page 
#### NEW PAGE "Value Analysis" 
- Read in incomestatement / balance sheet history
    - i.e. Cash
- Read in Dividend yield history (Convert to % as well )
