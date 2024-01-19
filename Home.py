#
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


# Tickers to read 
tickers = pd.read_csv('stocklist.csv')

# Get All ticker data of interest # 
firstDate = '2023-12-01'
lastDate = str(datetime.now().strftime('%Y-%m-%d'))
for i, ticker in enumerate(tickers['ticker']):  
    print('Loading ' + ticker + ' data')
    if i == 0:
        allData = yf.download(ticker, firstDate, lastDate)
        allData['ticker'] = ticker 
    else:
        tmpData = yf.download(ticker,'2024-01-10','2024-01-18')
        allData = pd.concat([allData,tmpData])

# Create Custom Cols 
allData['High-Low'] = allData['High'] - allData['Low']  
allData['DailyVolatility_Perc'] = (allData['High'] - allData['Low'])  / ((allData['High'] + allData['Low'])/ 2 )
allData = allData.reset_index()

# Create Customs SMA's
allData['5day_SMA'] = allData['Close'].rolling(window=5).mean()
allData['10day_SMA'] = allData['Close'].rolling(window=10).mean()
allData['30day_SMA'] = allData['Close'].rolling(window=30).mean()
allData['90day_SMA'] = allData['Close'].rolling(window=90).mean()
allData['360day_SMA'] = allData['Close'].rolling(window=360).mean()


allData_filtered = allData[allData['ticker']=='VOO']

ticker = 'ILMN'
stock_data = allData_filtered 
symbol = ticker 



# Using Plotly Graph Objects
#fig = go.Figure()

#fig.add_trace(go.Scatter(x=stock_data['Date'], y=stock_data['Close'], mode='markers', name='Close'))
#fig.add_trace(go.Scatter(x=stock_data['Date'], y=stock_data['5day_SMA'], mode='markers', name='5day_SMA'))

#fig.update_layout(
#    title='My Data',
#    xaxis_title='Date',
#    yaxis_title='$'
#)


# NexT step: need to add multiple lines (make toggle able?)
# add dataframe of all data and sort 
#  2 levels of dataframes, 1 row per ticketer, and 1 drill down 

import plotly.express as px
# Create Line plot
fig = px.line(stock_data, x=stock_data['Date'], y=stock_data['Close'])

# Add Scatter plot   5day_SMA
fig.add_scatter(x=stock_data['Date'], y=stock_data['Close'])


st.plotly_chart(fig,sharing="streamlit")

