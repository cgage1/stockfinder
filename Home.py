#
#
# start streamlit app:  cd C:\Users\colto\Documents\stockfinder\
#    python -m streamlit run C:\Users\colto\Documents\stockfinder\Home.py
#   
 
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
    firstDate = '2023-01-01'
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
st.write('### Sorted Ticker Profiles')

# Show top KPI's 
topData = allData[allData['Date']==allData['Date'].max()]
topData = topData[['ticker','Close','5day_SMA','30day_SMA','360day_SMA','5day_DailyVolPercAvg','30day_DailyVolPercAvg','360day_DailyVolPercAvg']]
st.dataframe(topData, hide_index=True)

allData.info() 
# Arbirtrage Check plot 
# Another idea: What if you had a chart that normalizes the line charts/ overlays 
#   # add parameter here to make it so u can choose what line is being shown 

st.write('### Ticker Analysis ')

# Data Prep and filters
col1,col2,col3 = st.columns(3) 
with col1:
    symbol = st.selectbox(
    "Choose Stock to analyze:",
    (tickers['ticker'])
        )
with col2: 
    date_min = st.date_input("Min Date",value=date.today()- timedelta(days=365))
with col3:
    date_max = st.date_input("Max Date")

plotdata = allData[allData['ticker'] == symbol]
plotdata = plotdata[plotdata['Date'].astype(str) >= str(date_min)]
plotdata = plotdata[plotdata['Date'].astype(str) <= str(date_max)]


col1_charts,col2_charts = st.columns(2) 
with col1_charts:
    #-- Construct SMA Plot Lne Charts --# 
    line0 = go.Scatter(x=plotdata['Date'], y=plotdata['Close'], mode='lines', name='Close',line=dict(width=2))
    line1 = go.Scatter(x=plotdata['Date'], y=plotdata['5day_SMA'], mode='lines', name='5day_SMA',line=dict(width=1))
    line2 = go.Scatter(x=plotdata['Date'], y=plotdata['10day_SMA'], mode='lines', name='10day_SMA',line=dict(width=1))
    line3 = go.Scatter(x=plotdata['Date'], y=plotdata['30day_SMA'], mode='lines', name='30day_SMA',line=dict(width=1))

    lines = [line0, line1, line2, line3]
    # Create layout
    layout = go.Layout(title='$' + symbol + " Line Charts",
                    xaxis=dict(title='Date'),
                    yaxis=dict(title='$'),
                    legend=dict(title=''))
    fig = go.Figure(data=lines, layout=layout)
    st.plotly_chart(fig,sharing="streamlit")

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
    st.plotly_chart(fig,sharing="streamlit")
