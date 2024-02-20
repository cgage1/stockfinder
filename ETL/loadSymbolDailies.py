#
# ETL To get Stock ticker data and load into database table 
# Convert to incremental 
#

import yfinance as yf
import pandas as pd 
from datetime import datetime 
import pandasql as ps 
import config
import psycopg2
import yaml 


# YAML FILE LOCATION: 
with open(config.creds_filepath, "r") as yaml_file:
    creds = yaml.safe_load(yaml_file)

def getSymbolList():
    # Establish a connection to the PostgreSQL database
    conn = psycopg2.connect(
        dbname=creds['austere-prod']['dbname'],
        user=creds['austere-prod']['user'],
        password=creds['austere-prod']['password'],
        host=creds['austere-prod']['host'],
        port=creds['austere-prod']['port']
    )
    # get symbols of interest and their max date in dbo.symbol_dailies 
    query = "select symbol from dbo.symbols where active = bool(1)"
    # Execute the query and load data into a Pandas DataFrame
    df = pd.read_sql(query, conn)
    # Close the connection
    conn.close()
    return df 



mySymbols = getSymbolList()


# Get Ticker data from yahoo finance 
def getTickerData():
    firstDate = '2001-01-01' # this will be changed to pull dynamically from pg 
    lastDate = str(datetime.now().strftime('%Y-%m-%d'))
    for i, symbol in enumerate(mySymbols['symbol']):  
        print('Loading ' + symbol + ' data')
        try: 
            if i == 0:
                allData = yf.download(symbol, firstDate, lastDate)
                allData['symbol'] = symbol 
            else:
                tmpData = yf.download(symbol, firstDate, lastDate)
                tmpData['ticker'] = symbol 
                allData = pd.concat([allData,tmpData])
        except Exception as e: 
            print('Error with: ' + symbol)
    return allData

allData = getTickerData()

# Now port allData into a new pg table (dbo.symbol_quotes) (this schema will copy the schame from allData)
allData.info() 
allData.head() 
