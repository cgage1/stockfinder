#
# Home.py
# front page for evaluating/comparing elementary symbol patterns 
# 

# Next step: Bring in actual financials from yahoo finance 

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
import duckdb 

# Page configurations 
st.set_page_config(layout="wide")

# YAML FILE LOCATION: 
with open(config.creds_filepath, "r") as yaml_file:
    creds = yaml.safe_load(yaml_file)

# Get All Symbol data of interest # 
@st.cache_data
def getSymbolQuotes():
    conn = psycopg2.connect(
        dbname=creds['austere-prod']['dbname'],
        user=creds['austere-prod']['user'],
        password=creds['austere-prod']['password'],
        host=creds['austere-prod']['host'],
        port=creds['austere-prod']['port']
        )
    sql = """
    SELECT sq.symbol as Symbol, sq."date" as Date, 
    cast( sq."open" as float) as Open, 
    cast(sq.high as float) as High, 
    cast(sq.low as float) as Low, 
    cast(sq."close" as float) as Close, 
    cast(sq.volume as float) as Volume
    FROM dbo.symbol_quotes sq
    join dbo.symbols s on s.symbol = sq.symbol 
        and s.active = '1'
    """
    df = pd.read_sql(sql, conn)
    conn.close()
    return df

allData = getSymbolQuotes()

@st.cache_data
def getSymbols():
    conn = psycopg2.connect(
        dbname=creds['austere-prod']['dbname'],
        user=creds['austere-prod']['user'],
        password=creds['austere-prod']['password'],
        host=creds['austere-prod']['host'],
        port=creds['austere-prod']['port']
        )
    sql = """
    select * from dbo.symbols 
    """
    df = pd.read_sql(sql, conn)
    conn.close()
    return df

Symbols = getSymbols()

# Move Symbol to first column 
column = allData.pop('symbol')
allData.insert(0, column.name, column)

# Create Custom Cols 
allData['High-Low'] = allData['high'] - allData['low']  
allData['DailyVolatility_Perc'] = (allData['high'] - allData['low']) * 100  / ((allData['high'] + allData['low'])/ 2 )
allData['Close_lag'] = allData.groupby('symbol')['close'].shift(1)
#allData['CloseChange_Perc'] = ( allData.groupby('symbol')['close'] - allData.groupby('symbol')['close'].shift(1) ) / allData.groupby('symbol')['close'].shift(1)

# Transformations :(Close - lag(Close) over (partition by Symbol order by date) ) / lag(Close) over (partition by Symbol order by date) as CloseChange_Perc 
sql = """
select *,
case when lag(Close) over (partition by Symbol order by Date) is not null 
    then ( Close*1.0 - lag(Close) over (partition by Symbol order by Date) )*100 / lag(Close) over (partition by Symbol order by Date) end  as CloseChange_Perc 

from allData
"""
allData = ps.sqldf(sql, locals())
allData = allData.reset_index()

# Create Customs SMA's
allData['_5day_SMA'] = allData.groupby('symbol')['close'].transform(lambda x: x.rolling(window=5).mean())
allData['_10day_SMA'] = allData.groupby('symbol')['close'].transform(lambda x: x.rolling(window=10).mean())
allData['_30day_SMA'] = allData.groupby('symbol')['close'].transform(lambda x: x.rolling(window=30).mean())
allData['_90day_SMA'] = allData.groupby('symbol')['close'].transform(lambda x: x.rolling(window=90).mean())
allData['_360day_SMA'] = allData.groupby('symbol')['close'].transform(lambda x: x.rolling(window=360).mean())

# Create Customs Volatility Measures 
allData['_5day_DailyVolPercAvg'] = allData.groupby('symbol')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=5).mean())
allData['_10day_DailyVolPercAvg'] = allData.groupby('symbol')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=10).mean())
allData['_30day_DailyVolPercAvg'] = allData.groupby('symbol')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=30).mean())
allData['_90day_DailyVolPercAvg'] = allData.groupby('symbol')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=90).mean())
allData['_360day_DailyVolPercAvg'] = allData.groupby('symbol')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=360).mean())


#---------------------------------------------#
#----------------- FRONT END -----------------#
#---------------------------------------------#
# Need 1 row per Symbol grouping  
st.title("Austere - Basic Analysis :diamond_shape_with_a_dot_inside:")
st.write('### Sorted Symbol Profiles')

# Show top KPI's 
def getTopData():
    con = duckdb.connect(database=':memory:')
    allDataTmp = allData 
    con.register('allDataTmp', allData)
    sql = """
        SELECT 
        a.symbol, a.close, _5day_SMA, _30day_SMA, _360day_SMA, _5day_DailyVolPercAvg, 
        _30day_DailyVolPercAvg, _360day_DailyVolPercAvg, keys.maxdate
        FROM allData a
        INNER JOIN (
            select symbol, max(date) maxdate
            from allDataTmp 
            group by symbol 
            ) keys on a.symbol = keys.symbol 
            and a.date = keys.maxdate
        """
    topData = con.execute(sql).fetchdf()
    st.dataframe(topData, hide_index=True)

getTopData()


#---------------------------------------#
#---------- Compare Symbols ------------#
#---------------------------------------# 
st.write('### Compare Symbol History ')  

# Data Prep and filters
col1,col2,col3,col4 = st.columns(4) 
with col1:
    compare_symbols = st.multiselect('Filter symbols', Symbols['symbol'])
    if len(compare_symbols) <= 0:
        comparedf = allData 
    else:   
        comparedf = allData[allData['symbol'].isin(compare_symbols)]
with col2: 
    # Convert Date inputs 
    date_ranges = ['10D','1M','3m', '6M', '1Y' ,'2Y', '3Y',  '4Y',   '5Y',   'MAX']
    date_values = ['10', '30','90', '180','365','730','1095','1460' ,'1825','99999']
    date_back = st.selectbox('Choose date range:', date_ranges, index=4)
    numdays = date_values[date_ranges.index(date_back)]
    date_min = datetime.now() - timedelta(days = int(numdays) )
    date_min = date_min.strftime('%Y-%m-%d')
with col3:
    date_max = st.date_input("Max Date")
with col4:
    alldata_cols = list(allData.columns)
    inspect_column = st.selectbox("Inspect distribution", allData.columns,index = alldata_cols.index('DailyVolatility_Perc') ) 

# Apply filters 
comparedf = comparedf[comparedf['date'].astype(str) >= str(date_min)]
comparedf = comparedf[comparedf['date'].astype(str) <= str(date_max)]

col1_compare, col2_compare, col3_compare = st.columns(3)
with col1_compare:
    comparefig = px.line(comparedf, x=comparedf['date'], y=comparedf['close'], color=comparedf['symbol'], title="Close by Date")
    st.plotly_chart(comparefig,sharing="streamlit",use_container_width=True)
with col2_compare:
    #comparedf['CloseChange_Perc_cum'] = comparedf.groupby('symbol')['CloseChange_Perc'].cumsum()  
    #comparedf['CloseChange_Perc_cum'] = comparedf.groupby('symbol')['close'] / comparedf.groupby('symbol')['close'].first()
    # Transformations :(Close - lag(Close) over (partition by Symbol order by date) ) / lag(Close) over (partition by Symbol order by date) as CloseChange_Perc 
    sql = """
    select *,
    Close*100 / first_value(Close) over (partition by Symbol order by Date) as CloseChange_Perc_cum
    from comparedf
    """
    comparedf = ps.sqldf(sql, locals())

    comparefig_perc = px.line(comparedf, x=comparedf['date'], y=comparedf['CloseChange_Perc_cum'], color=comparedf['symbol'], title="% Since Origin")
    st.plotly_chart(comparefig_perc, sharing="streamlit", use_container_width=True)
with col3_compare:
    fig_box = px.box(comparedf, x=inspect_column, color="symbol",title="Vol Dist ["+inspect_column+"]")
    st.plotly_chart(fig_box,sharing="streamlit",use_container_width=True)



#---------- Single Symbol investigate ------------# 
st.write('### Symbol Analysis ')
# Data Prep and filters
symbol = st.selectbox(
    "Choose Stock to analyze:",
    (Symbols['symbol'])
        )

# Apply filters 
plotdata = allData[allData['symbol'] == symbol]
plotdata = plotdata[plotdata['date'].astype(str) >= str(date_min)]
plotdata = plotdata[plotdata['date'].astype(str) <= str(date_max)]

col1_charts, col2_charts, col3_charts = st.columns(3) 
with col1_charts:
    #-- Construct SMA Plot Lne Charts --# 
    line0 = go.Scatter(x=plotdata['date'], y=plotdata['close'], mode='lines', name='close',line=dict(width=2))
    line1 = go.Scatter(x=plotdata['date'], y=plotdata['_5day_SMA'], mode='lines', name='5day_SMA',line=dict(width=1))
    line2 = go.Scatter(x=plotdata['date'], y=plotdata['_10day_SMA'], mode='lines', name='10day_SMA',line=dict(width=1))
    line3 = go.Scatter(x=plotdata['date'], y=plotdata['_30day_SMA'], mode='lines', name='30day_SMA',line=dict(width=1))
    line4 = go.Scatter(x=plotdata['date'], y=plotdata['_90day_SMA'], mode='lines', name='90day_SMA',line=dict(width=1))

    lines = [line0, line1, line2, line3, line4]
    layout = go.Layout(title='$' + symbol + " Line Charts",
                    xaxis=dict(title='date'),
                    yaxis=dict(title='$'),
                    legend=dict(title=''))
    fig = go.Figure(data=lines, layout=layout)
    st.plotly_chart(fig,sharing="streamlit",use_container_width=True)

with col2_charts:
    #-- Construct Volatility Plots Lne Charts --# 
    linebase = go.Scatter(x=plotdata['date'], y=plotdata['DailyVolatility_Perc'], mode='lines', name='DailyVolatility_Perc',line=dict(width=1))
    line0 = go.Scatter(x=plotdata['date'], y=plotdata['_5day_DailyVolPercAvg'], mode='lines', name='5day_DailyVolPercAvg',line=dict(width=1))
    line1 = go.Scatter(x=plotdata['date'], y=plotdata['_30day_DailyVolPercAvg'], mode='lines', name='30day_DailyVolPercAvg',line=dict(width=1))
    line2 = go.Scatter(x=plotdata['date'], y=plotdata['_90day_DailyVolPercAvg'], mode='lines', name='90day_DailyVolPercAvg',line=dict(width=1))
    line3 = go.Scatter(x=plotdata['date'], y=plotdata['_360day_DailyVolPercAvg'], mode='lines', name='360day_DailyVolPercAvg',line=dict(width=1))

    lines = [linebase, line0, line1, line2, line3]
    # Create layout
    layout = go.Layout(title='$' + symbol + " Daily Vol Charts",
                    xaxis=dict(title='date'),
                    yaxis=dict(title='$'),
                    legend=dict(title=''))
    fig = go.Figure(data=lines, layout=layout)
    st.plotly_chart(fig,sharing="streamlit",use_container_width=True)

with col3_charts:
    #----- Create volatility Chart ------# 
    import plotly.express as px
    fig_hist = px.histogram(plotdata, x=inspect_column, color="symbol", marginal="box",
                    hover_data=plotdata.columns, title='$' + symbol + " Vol Dist ["+inspect_column+"]")
    st.plotly_chart(fig_hist,sharing="streamlit",use_container_width=True)

col1_charts1, col1_charts2 = st.columns(2)
# BOLLINGER # 
with col1_charts1:
    # Calculate rolling mean and standard deviation
    window_size = st.slider('Window Size', 0,40,20)  # You can adjust this window size as needed
    rolling_mean = plotdata['close'].rolling(window=window_size).mean()
    rolling_std = plotdata['close'].rolling(window=window_size).std()

    # Compute upper and lower Bollinger Bands
    upper_band = rolling_mean + (2 * rolling_std)
    lower_band = rolling_mean - (2 * rolling_std)

    # Create traces for the plot
    trace_close = go.Scatter(x=plotdata['date'], y=plotdata['close'], mode='lines', name='Closing Price')
    trace_mean = go.Scatter(x=plotdata['date'], y=rolling_mean, mode='lines', name='Rolling Mean')
    trace_upper_band = go.Scatter(x=plotdata['date'], y=upper_band, mode='lines', name='Upper Bollinger Band', line=dict(dash='dash'))
    trace_lower_band = go.Scatter(x=plotdata['date'], y=lower_band, mode='lines', name='Lower Bollinger Band', line=dict(dash='dash'))

    # Combine traces into a figure  
    layout = go.Layout(title='$' + symbol + ' Bollinger Bands',
                    xaxis_title='date',
                    yaxis_title='Price')
    fig = go.Figure(data=[trace_close, trace_mean, trace_upper_band, trace_lower_band], layout=layout)
    st.plotly_chart(fig,sharing="streamlit",use_container_width=True)


# Display data from filters for drill down 
showalldata = st.radio('Show All Data',['Hide Data','Show Data'])
if showalldata=='Show Data':
    st.dataframe(plotdata)
