import yfinance as yf

ilmn = yf.Ticker("ilmn")

# get all stock info
ilmn.info

# get historical market data
hist = ilmn.history(period="12mo")
hist[hist['Dividends'] > 0]

# show meta information about the history (requires history() to be called first)
ilmn.history_metadata

# show actions (dividends, splits, capital gains)
ilmn.actions # Pulls alll dividend days (can be used to left join on)
ilmn.dividends
ilmn.splits
ilmn.capital_gains  # only for mutual funds & etfs

# show share count
ilmn.get_shares_full(start="2022-01-01", end=None)

# show financials:
# - income statement
ilmn.income_stmt


# - balance sheet
ilmn.balance_sheet
ilmn.quarterly_balance_sheet
# - cash flow statement
ilmn.cashflow
ilmn.quarterly_cashflow
# see `Ticker.get_income_stmt()` for more options

# show holders
ilmn.major_holders
ilmn.institutional_holders
ilmn.mutualfund_holders
ilmn.insider_transactions
ilmn.insider_purchases
ilmn.insider_roster_holders

# show recommendations
ilmn.recommendations
ilmn.recommendations_summary
ilmn.upgrades_downgrades

# Show future and historic earnings dates, returns at most next 4 quarters and last 8 quarters by default. 
# Note: If more are needed use ilmn.get_earnings_dates(limit=XX) with increased limit argument.
ilmn.earnings_dates

# show ISIN code - *experimental*
# ISIN = International Securities Identification Number
ilmn.isin

# show options expirations
ilmn.options

# show news
ilmn.news

# get option chain for specific expiration
opt = ilmn.option_chain('YYYY-MM-DD')
# data available via: opt.calls, opt.puts