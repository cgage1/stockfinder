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

# Create Custom Cols 
allData['High-Low'] = allData['High'] - allData['Low']  
allData['DailyVolatility_Perc'] = (allData['High'] - allData['Low'])  / ((allData['High'] + allData['Low'])/ 2 )
allData = allData.reset_index()

# Create Customs SMA's
allData['5day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=5).mean())
allData['10day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=10).mean())
allData['30day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=30).mean())
allData['90day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=90).mean())
allData['360day_SMA'] = allData.groupby('ticker')['Close'].transform(lambda x: x.rolling(window=360).mean())


#------------------------------------#
#------------ FRONT END -------------#
#------------------------------------#

# Need 1 row per ticker grouping  
st.title("STONKS")
st.write('# Identify volatile stocks of interest')
st.write('some analysois stuff that compares some metrics that i care about ')

# Arbirtrage Check plot 
# Another idea: What if you had a chart that normalizes the line charts/ overlays 
#   # add parameter here to make it so u can choose what line is being shown 

st.write('# Evaluate stock of interest # ')

# Apply filters 
col1,col2,col3 = st.columns(3) 
with col1:
    symbol = st.selectbox(
    "Choose Stock to analyze:",
    (tickers['ticker'])
        )
with col2: 
    date_min = st.date_input("Min Date")
with col3:
    date_max = st.date_input("Max Date")

plotdata = allData[allData['ticker'] == symbol]


# Construct SMA Plot 
line0 = go.Scatter(x=plotdata['Date'], y=plotdata['Close'], mode='lines', name='Close',line=dict(width=2))
line1 = go.Scatter(x=plotdata['Date'], y=plotdata['5day_SMA'], mode='lines', name='5day_SMA',line=dict(width=1))
line2 = go.Scatter(x=plotdata['Date'], y=plotdata['10day_SMA'], mode='lines', name='10day_SMA',line=dict(width=1))
line3 = go.Scatter(x=plotdata['Date'], y=plotdata['30day_SMA'], mode='lines', name='30day_SMA',line=dict(width=1))

# Combine traces into a list
lines = [line0, line1, line2, line3]

# Create layout
layout = go.Layout(title='$' + symbol + " Line Charts",
                   xaxis=dict(title='Date'),
                   yaxis=dict(title='$'),
                   legend=dict(title=''))

# Create figure with traces and layout
fig = go.Figure(data=lines, layout=layout)


st.plotly_chart(fig,sharing="streamlit")

