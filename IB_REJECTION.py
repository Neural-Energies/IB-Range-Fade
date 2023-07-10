import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime

# Function to check if price is within the threshold range of target
def price_within_range(price, target, lower_threshold, upper_threshold):
    return lower_threshold <= price - target <= upper_threshold

@st.experimental_memo()
def load_data():
    df = pd.read_csv('https://raw.githubusercontent.com/Neural-Energies/IB-Range-Fade/main/IBSTUDY.CSV')

    df['Date'] = pd.to_datetime(df['Date'])
    df['TradingDay'] = df['Date'].dt.date
    return df

df = load_data()

# Use sliders to set the dynamic thresholds
ibh_front_run_threshold = st.sidebar.slider('Set IBH Front Run Threshold (in ticks)', min_value=0, max_value=100, value=4) * 0.25
ibh_broke_threshold = st.sidebar.slider('Set IBH Broke Threshold (in ticks)', min_value=0, max_value=100, value=4) * 0.25
ibl_front_run_threshold = st.sidebar.slider('Set IBL Front Run Threshold (in ticks)', min_value=-100, max_value=0, value=-4) * 0.25
ibl_broke_threshold = st.sidebar.slider('Set IBL Broke Threshold (in ticks)', min_value=-100, max_value=0, value=-4) * 0.25
vwap_range = st.sidebar.slider('Set VWAP Range (in ticks)', min_value=0, max_value=100, value=10) * 0.25
code_runs_per_day = st.sidebar.slider('Set number of times code runs per day', min_value=1, max_value=10, value=1)
analyze_button = st.sidebar.button('Analyze')

st.write("""
    # Instructions:
    Use the sliders to adjust the thresholds for different events:
    - IBH Front Run Threshold: This is the threshold before the price crosses the IBH. Set in ticks.
    - IBH Broke Threshold: This is the threshold for price to exceed the IBH for a breakout to occur. Set in ticks.
    - IBL Front Run Threshold: This is the threshold before the price crosses the IBL. Set in negative ticks.
    - IBL Broke Threshold: This is the threshold for price to drop below the IBL for a breakout to occur. Set in negative ticks.
    - VWAP Range: This is the range within which a price movement is considered a reversion event. Set in ticks.
    - Number of times code runs per day: This is the number of breakout/reversion attempts to consider each day.
""")

if analyze_button:
    breakouts = 0
    reversions = 0
    event_points = []
    trading_days = df['TradingDay'].unique()

    for trading_day in trading_days:
        daily_data = df[df['TradingDay'] == trading_day]
        daily_runs = 0
        breakout_flag = False

        if daily_data.empty or daily_data.iloc[-1]['Date'].time() < datetime.time(10, 30):
            continue

        IBH = daily_data['IBH'].values[0]  # Use provided IBH
        IBL = daily_data['IBL'].values[0]  # Use provided IBL

        for index, row in daily_data[daily_data['Date'].dt.time >= datetime.time(10, 30)].iterrows():

            # Break if code has already run the maximum times for the day
            if daily_runs >= code_runs_per_day:
                break

            if price_within_range(row['High'], IBH, -ibh_front_run_threshold, ibh_broke_threshold):
                if row['High'] >= IBH + ibh_broke_threshold:
                    breakouts += 1
                    breakout_flag = True
                    event_points.append((row['Date'], row['High'], 'Breakout'))
                    daily_runs += 1
                elif not breakout_flag and price_within_range(row['Low'], row['VWAP'], -vwap_range, vwap_range):
                    reversions += 1
                    event_points.append((row['Date'], row['High'], 'Reversion'))
                    daily_runs += 1

            elif price_within_range(row['Low'], IBL, ibl_front_run_threshold, -ibl_broke_threshold):
                if row['Low'] <= IBL + ibl_broke_threshold:
                    breakouts += 1
                    breakout_flag = True
                    event_points.append((row['Date'], row['Low'], 'Breakout'))
                    daily_runs += 1
                elif not breakout_flag and price_within_range(row['High'], row['VWAP'], -vwap_range, vwap_range):
                    reversions += 1
                    event_points.append((row['Date'], row['Low'], 'Reversion'))
                    daily_runs += 1

    total_attempts = breakouts + reversions

    probability_breakout = breakouts / total_attempts if total_attempts else 0
    probability_reversion = reversions / total_attempts if total_attempts else 0

    # Convert to percentage with 2 decimal places
    probability_breakout *= 100
    probability_reversion *= 100

    st.write(f"Probability of a breakout on the first attempt: {probability_breakout:.2f}%")
    st.write(f"Probability of price reverting to VWAP after an attempt: {probability_reversion:.2f}%")

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df['Date'], y=df['High'], mode='lines', name='High'))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Low'], mode='lines', name='Low'))
    if event_points:  # Check if there are any events recorded
        breakout_dates, breakout_values, event_types = zip(*event_points)
        fig.add_trace(go.Scatter(x=breakout_dates, y=breakout_values, mode='markers', name='Events',marker=dict(color=['red' if event_type == 'Breakout' else 'green' for event_type in event_types])))
    else:
        st.write("No events recorded.")
        
    st.plotly_chart(fig)
