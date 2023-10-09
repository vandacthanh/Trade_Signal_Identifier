import streamlit as st
import pandas as pd
import numpy as np

import talib
from technical.indicators import ichimoku
from tvDatafeed import TvDatafeed, Interval

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from datetime import datetime

from statsmodels.tsa.vector_ar.var_model import VAR
from sklearn.metrics import mean_squared_error
from math import sqrt

def data_retrieval(asset, n_bars, price_selection, period, interval):
    tv = TvDatafeed()
    
    ASSET_MAPPING = {
                    'SILVER': ('SI1!', 'COMEX'),
                    'GOLD': ('GC1!', 'COMEX'),
                    'Platinum': ('PL1!', 'NYMEX'),
                    'Crude Oil': ('CL1!', 'NYMEX'),
                    'Natural Gas': ('NG1!', 'NYMEX'),
                    'Copper': ('HG1!', 'COMEX'),
                    'Corn': ('ZC1!', 'CBOT'),
                    'Soybean': ('ZS1!', 'CBOT'),
                    'Wheat': ('ZW1!', 'CBOT'),
                    
                    'S&P 500': ('SPX', 'SP'),
                    'Nasdaq 100 Index': ('NDX', 'NASDAQ'),                    
                    'Dow Jones Industrial Average Index': ('DJI', 'NYMEX'),
                    
                    'Apple Inc': ('AAPL', 'NASDAQ'),
                    'Alphabet Inc (Google) Class A': ('GOOGL', 'NASDAQ'),
                    'Amazon.com, Inc': ('AMZN', 'NASDAQ'),
                    'Meta Platforms, Inc.': ('META', 'NASDAQ'),
                    'Tesla, Inc.': ('TSLA', 'NASDAQ'),
                    
                    'RIPPLE': ('XRPUSD', 'CRYPTO'),
                    'BITCOIN': ('BTCUSD', 'CRYPTO'),
                    'Ethereum':('ETHUSD', 'CRYPTO')
    }
    
    INTERVAL_MAPPING  = {
                        '1 minute': Interval.in_1_minute,
                        '3 minutes': Interval.in_3_minute,
                        '5 minutes': Interval.in_5_minute,
                        '15 minutes': Interval.in_15_minute,
                        '30 minutes': Interval.in_30_minute,
                        '45 minutes': Interval.in_45_minute,
                        '1 hour': Interval.in_1_hour,
                        '2 hours': Interval.in_2_hour,
                        '3 hours': Interval.in_3_hour,
                        '4 hours': Interval.in_4_hour,
                        'daily': Interval.in_daily,
                        'weekly': Interval.in_weekly,
                        'monthly': Interval.in_monthly
                        }
    asset_mapping = ASSET_MAPPING.get(asset, ('', ''))  
    interval_mapping = INTERVAL_MAPPING.get(interval, ())
    symbol, exchange = asset_mapping
    dataframe = tv.get_hist(symbol=symbol,
                            exchange=exchange,
                            interval=interval_mapping,
                            n_bars=n_bars)

    # Calculate KAMA
    dataframe['KAMA'] = talib.KAMA(dataframe[price_selection], timeperiod=period)
    
    # Calculate Ichimoku
    ichi = ichimoku(dataframe)
    dataframe['tenkan'] = ichi['tenkan_sen']
    dataframe['kijun'] = ichi['kijun_sen']
    dataframe['senkou_a'] = ichi['senkou_span_a']
    dataframe['senkou_b' ]= ichi['senkou_span_b']
    dataframe['cloud_green'] = ichi['cloud_green']
    dataframe['cloud_red'] = ichi['cloud_red']
    
    # Drop unknown value
    dataframe = dataframe.dropna()
    
    # Add the datetime column back from index
    dataframe.reset_index(inplace=True)
    dataframe['time'] = dataframe.iloc[:,0]
    dataframe['time'] = pd.to_datetime(dataframe.time)
    dataframe['time_formated'] = dataframe['time'].dt.strftime('%m/%d/%Y %H:%M:%S')
    return dataframe

def plot_dataframe(dataframe, asset):
    st.markdown(f"<h1 style='text-align: center; color: grey;'>SIGNAL ANALYSIS ON {asset} </h1>", unsafe_allow_html=True)
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=dataframe['time_formated'], 
                             y=dataframe['close'],
                             line_color='rgb(0,100,80)',
                             name='Closing Price',
                             ))
    
    fig.add_trace(go.Scatter(x=dataframe['time_formated'], 
                             y=dataframe['KAMA'],
                             line_color='black',
                             name='KAMA',
                             ))
    
    fig.add_trace(go.Scatter(x=dataframe['time_formated'], 
                             y=dataframe['tenkan'],
                             line_color='green',
                             name='CONVERSION',
                             ))
    
    fig.add_trace(go.Scatter(x=dataframe['time_formated'], 
                             y=dataframe['kijun'],
                             line_color='red',
                             name='STANDARD',
                             ))
    
    fig.update_traces(mode='lines')

    return st.plotly_chart(fig, theme="streamlit", use_container_width=True)

def signal_detector(df, interval):
    now = datetime.now()
    check_time = now.strftime("%d/%m/%Y %H:%M:%S")
    # Check if the current price is above KAMA and above Ichimoku Cloud
    if df['close'].iloc[-1] > df.KAMA.iloc[-1] and df['close'].iloc[-1] > df.tenkan.iloc[-1] and df.tenkan.iloc[-1] > df.kijun.iloc[-1]:
        st.success(f"At {check_time} - {interval} interval - Bullish Pattern Detected.")
    # Check if the current price is below KAMA and below Ichimoku Cloud
    elif df['close'].iloc[-1] < df.KAMA.iloc[-1] and df['close'].iloc[-1] < df.tenkan.iloc[-1] and df.tenkan.iloc[-1] < df.kijun.iloc[-1]:
        st.error(f"At {check_time} - {interval} interval - Bearish Pattern Detected.")
    else: 
        st.warning(f"At {check_time} - {interval} interval - Market is under consolidation.")
    return None 


if __name__ == "__main__":

    # SIDEBAR
    st.sidebar.subheader("INPUT PARAMETERS")
    # Define a dictionary for market selection mapping
    MARKET_OPTIONS = {
        'COMMODITY': [
            'SILVER', 'GOLD', 'Platinum', 'Crude Oil', 'Natural Gas', 'Copper',
            'Corn','Soybean', 'Wheat'
        ],
        'INDEX FUNDS': [
            'S&P 500', 'Nasdaq 100 Index', 'Dow Jones Industrial Average Index'
        ],
        'STOCKS': [
            'Alphabet Inc (Google) Class A', 'Amazon.com, Inc.',
            'Meta Platforms, Inc.', 'Tesla, Inc.'
        ],
        'CRYPTO CURRENCY': [
            'RIPPLE', 'BITCOIN', 'Ethereum'
        ]
    }

    # Market selection
    market = st.sidebar.selectbox("MARKET SELECTION", list(MARKET_OPTIONS.keys()))

    # Asset selection based on market selection
    asset_options = MARKET_OPTIONS.get(market, [])
    if asset_options:
        asset = st.sidebar.selectbox("ASSET SELECTION", asset_options)
    else:
        asset = None  # If no asset options are available for the selected market
        

    interval = st.sidebar.selectbox("INTERVAL SELECTION", ['1 minute','3 minutes','5 minutes','15 minutes',
                                                           '30 minutes', '45 minutes', '1 hour', '2 hours',
                                                           '3 hours', '4 hours', 'daily', 'weekly','monthly'
                                                           ])
    n_bars = st.sidebar.number_input("NUMBER OF BARS", min_value=100, value=1000)
    price_selection = st.sidebar.selectbox("KAMA INPUT PRICE", ['high', 'low', 'open', 'close'])
    period = st.sidebar.number_input("INTERVAL PERIOD FOR KAMA", min_value=10, value=60)

    try:
        df = data_retrieval(asset, n_bars, price_selection, period, interval)
        plot_dataframe(df, asset)
        signal_detector(df, interval)
    except Exception as e:
        st.error("There has been a problem with retrieving the data. Please consult Van Dac Thanh for more information")
        st.error(f"{str(e)}")
