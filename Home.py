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

st.set_page_config(layout="wide")

# Tickers to read 
tickers = pd.read_csv('stocklist.csv')

# Get All ticker data of interest # 
@st.cache_data
def getTickerData():
    firstDate = '2001-01-01'
    lastDate = str(datetime.now().strftime('%Y-%m-%d'))
    for i, ticker in enumerate(tickers['ticker']):  
        print('Loading ' + ticker + ' data')
        try: 
            if i == 0:
                allData = yf.download(ticker, firstDate, lastDate)
                allData['ticker'] = ticker 
            else:
                tmpData = yf.download(ticker, firstDate, lastDate)
                tmpData['ticker'] = ticker 
                allData = pd.concat([allData,tmpData])
        except Exception as e: 
            st.write(ticker + " ticker not found: " + e)
        
    return allData

allData = getTickerData()

# Move ticker to first column 
column = allData.pop('ticker')
allData.insert(0, column.name, column)

# Create Custom Cols 
allData['High-Low'] = allData['High'] - allData['Low']  
# CHANGE THIS TO A LAG ON CLOSE NOT HIGH VS LOW (VOLATILITY IS ABS Otherwise)
allData['DailyVolatility_Perc'] = (allData['High'] - allData['Low']) * 100  / ((allData['High'] + allData['Low'])/ 2 )
allData = allData.reset_index()

# Create Customs SMA's
allData['5day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=5).mean())
allData['10day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=10).mean())
allData['30day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=30).mean())
allData['90day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=90).mean())
allData['360day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=360).mean())

# Create Customs Volatility Measures 
allData['5day_DailyVolPercAvg'] = allData.groupby('ticker')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=5).mean())
allData['10day_DailyVolPercAvg'] = allData.groupby('ticker')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=10).mean())
allData['30day_DailyVolPercAvg'] = allData.groupby('ticker')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=30).mean())
allData['90day_DailyVolPercAvg'] = allData.groupby('ticker')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=90).mean())
allData['360day_DailyVolPercAvg'] = allData.groupby('ticker')['DailyVolatility_Perc'].transform(lambda x: x.rolling(window=360).mean())


#---------------------------------------------#
#----------------- FRONT END -----------------#
#---------------------------------------------#

# Need 1 row per ticker grouping  
st.title("ALGO :diamond_shape_with_a_dot_inside:")
st.write('### Sorted Symbol Profiles')

# Show top KPI's 
topData = allData[allData['Date']==allData['Date'].max()]
topData = topData[['ticker','Close','5day_SMA','30day_SMA','360day_SMA','5day_DailyVolPercAvg','30day_DailyVolPercAvg','360day_DailyVolPercAvg']]
st.dataframe(topData, hide_index=True)

#---------------------------------------#
#---------- Compare Symbols ------------#
#---------------------------------------# 
st.write('### Compare Symbol History ')  

# Data Prep and filters
col1,col2,col3,col4 = st.columns(4) 
with col1:
    compare_symbols = st.multiselect('Filter symbols', tickers['ticker'])
    if len(compare_symbols) <= 0:
        comparedf = allData 
    else:   
        comparedf = allData[allData['ticker'].isin(compare_symbols)]
with col2: 
    # Convert Date inputs 
    date_ranges = ['10D','1M','6M','1Y','3Y','5Y','MAX']
    date_values = ['10','30','180','365','1095','1825','99999']
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
comparedf = comparedf[comparedf['Date'].astype(str) >= str(date_min)]
comparedf = comparedf[comparedf['Date'].astype(str) <= str(date_max)]

col1_compare, col2_compare, col3_compare = st.columns(3)
with col1_compare:
    comparefig = px.line(comparedf, x=comparedf['Date'], y=comparedf['Close'], color=comparedf['ticker'], title="Vol Dist ["+inspect_column+"]")
    st.plotly_chart(comparefig,sharing="streamlit",use_container_width=True)
with col2_compare:
    fig_hist2 = px.histogram(comparedf, x=inspect_column, color="ticker", marginal="box",title="Vol Dist ["+inspect_column+"]",
                    hover_data=comparedf.columns)
    st.plotly_chart(fig_hist2,sharing="streamlit",use_container_width=True)
with col3_compare:
    fig_box = px.box(comparedf, y=inspect_column, color="ticker",title="Vol Dist ["+inspect_column+"]")
    st.plotly_chart(fig_box,sharing="streamlit",use_container_width=True)



#---------- Singl ticker investigate ------------# 
st.write('### Symbol Analysis ')
# Data Prep and filters
symbol = st.selectbox(
    "Choose Stock to analyze:",
    (tickers['ticker'])
        )

# Apply filters 
plotdata = allData[allData['ticker'] == symbol]
plotdata = plotdata[plotdata['Date'].astype(str) >= str(date_min)]
plotdata = plotdata[plotdata['Date'].astype(str) <= str(date_max)]

col1_charts, col2_charts, col3_charts = st.columns(3) 
with col1_charts:
    #-- Construct SMA Plot Lne Charts --# 
    line0 = go.Scatter(x=plotdata['Date'], y=plotdata['Close'], mode='lines', name='Close',line=dict(width=2))
    line1 = go.Scatter(x=plotdata['Date'], y=plotdata['5day_SMA'], mode='lines', name='5day_SMA',line=dict(width=1))
    line2 = go.Scatter(x=plotdata['Date'], y=plotdata['10day_SMA'], mode='lines', name='10day_SMA',line=dict(width=1))
    line3 = go.Scatter(x=plotdata['Date'], y=plotdata['30day_SMA'], mode='lines', name='30day_SMA',line=dict(width=1))
    line4 = go.Scatter(x=plotdata['Date'], y=plotdata['90day_SMA'], mode='lines', name='90day_SMA',line=dict(width=1))

    lines = [line0, line1, line2, line3, line4]
    layout = go.Layout(title='$' + symbol + " Line Charts",
                    xaxis=dict(title='Date'),
                    yaxis=dict(title='$'),
                    legend=dict(title=''))
    fig = go.Figure(data=lines, layout=layout)
    st.plotly_chart(fig,sharing="streamlit",use_container_width=True)

with col2_charts:
    #-- Construct Volatility Plots Lne Charts --# 
    linebase = go.Scatter(x=plotdata['Date'], y=plotdata['DailyVolatility_Perc'], mode='lines', name='DailyVolatility_Perc',line=dict(width=1))
    line0 = go.Scatter(x=plotdata['Date'], y=plotdata['5day_DailyVolPercAvg'], mode='lines', name='5day_DailyVolPercAvg',line=dict(width=1))
    line1 = go.Scatter(x=plotdata['Date'], y=plotdata['30day_DailyVolPercAvg'], mode='lines', name='30day_DailyVolPercAvg',line=dict(width=1))
    line2 = go.Scatter(x=plotdata['Date'], y=plotdata['90day_DailyVolPercAvg'], mode='lines', name='90day_DailyVolPercAvg',line=dict(width=1))
    line3 = go.Scatter(x=plotdata['Date'], y=plotdata['360day_DailyVolPercAvg'], mode='lines', name='360day_DailyVolPercAvg',line=dict(width=1))

    lines = [linebase, line0, line1, line2, line3]
    # Create layout
    layout = go.Layout(title='$' + symbol + " Daily Vol Charts",
                    xaxis=dict(title='Date'),
                    yaxis=dict(title='$'),
                    legend=dict(title=''))
    fig = go.Figure(data=lines, layout=layout)
    st.plotly_chart(fig,sharing="streamlit",use_container_width=True)

with col3_charts:
    #----- Create volatility Chart ------# 
    import plotly.express as px
    fig_hist = px.histogram(plotdata, x=inspect_column, color="ticker", marginal="box",
                    hover_data=plotdata.columns, title='$' + symbol + " Vol Dist ["+inspect_column+"]")
    st.plotly_chart(fig_hist,sharing="streamlit",use_container_width=True)


# Display data from filters for drill down 
showalldata = st.radio('Show All Data',['Hide Data','Show Data'])
if showalldata=='Show Data':
    st.dataframe(plotdata)
