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
import psycopg2.extras
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
    # get symbols of interest and their max date in dbo.symbol_quotes 
    query = """
    /* get symbol dates for */
    with maxdates as (
        select symbol, max(date) maxdate 
        from dbo.symbol_quotes
        group by symbol 
        )
    select s.symbol, cast(coalesce(maxdates.maxdate, '1980-01-01') as varchar) maxdate 
    from dbo.symbols s
    LEFT JOIN maxdates ON s.symbol = maxdates.symbol 
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df



# Get Ticker data from yahoo finance 
def getSymbolQuotes(mySymbols):
    lastDate = str(datetime.now().strftime('%Y-%m-%d'))  
    for i, symbol in enumerate(mySymbols['symbol']):  
        print('Loading ' + symbol + ' data')
        try: 
            if i == 0:
                allData = yf.download(symbol, mySymbols.iloc[i]['maxdate'], lastDate)
                allData['symbol'] = symbol 
            else:
                tmpData = yf.download(symbol, mySymbols.iloc[i]['maxdate'], lastDate)
                tmpData['symbol'] = symbol 
                allData = pd.concat([allData,tmpData])
        except Exception as e: 
            print('Error with: ' + symbol)
    return allData


# Now port allData into a new pg table (dbo.symbol_quotes_staging) (this schema will copy the schame from allData)
def loadQuotesToStaging(df):
    conn = psycopg2.connect(
        dbname=creds['austere-prod']['dbname'],
        user=creds['austere-prod']['user'],
        password=creds['austere-prod']['password'],
        host=creds['austere-prod']['host'],
        port=creds['austere-prod']['port']
    )
    # df is the dataframe
    if len(df) > 0:
        df.reset_index(inplace=True)
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        df_columns = list(df)
        # create (col1,col2,...)
        columns = ",".join(df_columns)
        # create VALUES('%s', '%s",...) one '%s' per column
        values = "VALUES({})".format(",".join(["%s" for _ in df_columns])) 
        #create INSERT INTO table (columns) VALUES('%s',...)
        insert_stmt = "INSERT INTO {} ({}) {}".format('dbo.symbol_quotes_staging', columns, values)
        cur = conn.cursor()
        psycopg2.extras.execute_batch(cur, insert_stmt, df.values)
        conn.commit()
        cur.close()
    else:
        print('No new symbol data available.')

def upsertToSymbolQuotesFromStaging():
    conn = psycopg2.connect(
        dbname=creds['austere-prod']['dbname'],
        user=creds['austere-prod']['user'],
        password=creds['austere-prod']['password'],
        host=creds['austere-prod']['host'],
        port=creds['austere-prod']['port']
    )
    sql = """
        /* upsert from staging into main table */ 
        INSERT INTO dbo.symbol_quotes (symbol, "date", "open", high, low, "close", adj_close, volume)
            select symbol, cast("date" as date) date , "open", high, low, "close", adj_close, volume
            from dbo.symbol_quotes_staging 
            on conflict 
            do nothing 
        ; """
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()


# RUN ALL 
def main():
    mySymbols = getSymbolList()
    allData = getSymbolQuotes(mySymbols)
    print('Pushing data to staging table dbo.symbol_quotes_staging.')
    loadQuotesToStaging(allData)
    print('Formatting/loading data into target table dbo.symbol_quotes.')
    upsertToSymbolQuotesFromStaging()

# UPDATE THIS CODE TO USE EXISTING MAX DATES TO PULL INCREMENTAL DATA! :) 

if __name__ == "__main__":
    main() 

