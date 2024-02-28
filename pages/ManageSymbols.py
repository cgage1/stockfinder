
# Page for viewing existig symbols and adding new ones 

import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd 
from datetime import datetime 
import plotly.graph_objs as go
import plotly 
import plotly.express as px
from datetime import date, timedelta
import pandasql as ps 
import psycopg2
import yaml
import config

# Page configurations 
st.set_page_config(layout="wide")

# YAML FILE LOCATION: 
with open(config.creds_filepath, "r") as yaml_file:
    creds = yaml.safe_load(yaml_file)


# Load existing symbols 
def getSymbols():
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
        SELECT symbol, "type", subtype, exchange, category, description, "comment", active
        FROM dbo.symbols;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def is_valid_symbol(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")  # Fetch data for one day
        return not data.empty
    except ValueError:
        return False

def insertSymbolToDatabase(symbol, desc, comment, type):
    if is_valid_symbol(symbol):
        conn = psycopg2.connect(
            dbname=creds['austere-prod']['dbname'],
            user=creds['austere-prod']['user'],
            password=creds['austere-prod']['password'],
            host=creds['austere-prod']['host'],
            port=creds['austere-prod']['port']
        )
        sql = f"""
            INSERT INTO dbo.symbols (symbol, description, comment, type)
                select '{symbol}', '{desc}', '{comment}', '{type}'
            ; """
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        conn.close()
        st.write(f'${symbol} written to database.')
    else: 
        st.write(symbol + ' is not valid, only yahoo finance symbols are valid.')


######## PAGE START 
st.title('Manage Symbols')

symbols = getSymbols()
# Create a form
with st.form("Enter Symbol"):
    inputcol1,inputcol2,inputcol3 = st.columns(3)
    symbol_input = inputcol1.text_input("Enter Yahoo trading symbol:" )
    type_input = inputcol2.selectbox("Symbol type:",symbols['type'].unique() )
    desc_input = inputcol1.text_input("Shortname for symbol:", '')
    comment_input = inputcol2.text_input("Comment:",'')
    submitted = st.form_submit_button("Submit symbol entry")

# Check if the form was submitted
if submitted:
    if symbol_input is not None:
        insertSymbolToDatabase(symbol_input, desc_input, comment_input, type_input)
    else: 
        st.write('Symbol is required.')


if st.button("Refresh all data [Admin Only functionality]"):
    from ETL import load_dbo_symbol_quotes
    load_dbo_symbol_quotes.main()
    st.write('All symbols refreshed:')
    st.dataframe(load_dbo_symbol_quotes.getSymbolList())


