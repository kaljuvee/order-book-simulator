import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import ccxt
from plotly.subplots import make_subplots
import numpy as np
import plotly.express as px
from util import exchange_util, plot_util
from scipy.stats import zscore
from datetime import datetime
import time
import itertools

def get_pairs(crypto_symbols):
    # Generate all permutations of the crypto symbols
    symbol_permutations = itertools.permutations(crypto_symbols, 2)
    # Create a list of dictionaries for the pairs
    pairs = [{'Asset1': symbol1, 'Asset2': symbol2} for symbol1, symbol2 in symbol_permutations]
    # Convert the list of dictionaries to a DataFrame
    pairs_df = pd.DataFrame(pairs)
    return pairs_df  # Return as a DataFrame
    
def get_run_id():
    return int(round(time.time() * 1000))
    
def get_bid(mid, spread_percentage):
    bid = mid * (1 - 0.5 * spread_percentage / 100)
    return bid

def get_ask(mid, spread_percentage):
    ask = mid * (1 + 0.5 * spread_percentage / 100)
    return ask
    
# Calculate z-score
def zscore(series):
    return (series - series.mean()) / np.std(series)

def initialize_position(positions, symbol_pair):
    """Initializes the position status for a given symbol pair if not already present."""
    if symbol_pair not in positions:
        positions[symbol_pair] = {
            'open': False,
            'entry_price': 0,
            'lots': 0,
            'cum_pnl': 0
        }
   
def get_merge_key(timestamp_series):
    # Rounds the given timestamp Series to the nearest minute using 'min' instead of deprecated 'T'
    return timestamp_series.dt.floor('min')

def merge_and_calculate_ratios(prices, asset1, asset2):
    # Filter prices for each asset and ensure timestamp is in datetime format
    prices_asset1 = prices[prices['symbol'] == asset1].copy()
    prices_asset2 = prices[prices['symbol'] == asset2].copy()
    prices_asset1['timestamp'] = pd.to_datetime(prices_asset1['timestamp'])
    prices_asset2['timestamp'] = pd.to_datetime(prices_asset2['timestamp'])

    # Create a merge key based on rounded timestamps
    prices_asset1['merge_key'] = get_merge_key(prices_asset1['timestamp'])
    prices_asset2['merge_key'] = get_merge_key(prices_asset2['timestamp'])

    # Perform an inner join on the merge key to ensure matching timestamps
    merged_prices = pd.merge(prices_asset1, prices_asset2, on='merge_key', suffixes=('_asset1', '_asset2'), how='inner')

    # Calculate price ratios and z-scores
    if not merged_prices.empty:
        price_ratios = merged_prices['close_asset1'] / merged_prices['close_asset2']
        z_scores = zscore(price_ratios)
    else:
        z_scores = []  # Handle the case where no matching timestamps are found

    return merged_prices, z_scores


def initialize_positions(sorted_pairs):
    positions = {}
    for _, row in sorted_pairs.iterrows():
        asset1, asset2 = row['Asset1'], row['Asset2']
        symbol_pair = f"{asset1}-{asset2}"
        positions[symbol_pair] = {'open': False, 'entry_price': 0, 'lots': 0}
    return positions

def open_position(position, pnl_list, symbol_pair, timestamp, z_score, entry_ask_price, 
                  adjusted_position_size, global_gross_cum_pnl, global_net_cum_pnl, exchange, run_id):
    try:
        position['open'] = True
        position['entry_price'] = entry_ask_price
        position['lots'] = adjusted_position_size / entry_ask_price
        pnl_list.append({
            'pair': symbol_pair, 'timestamp': timestamp, 'action': 'Open Position',
            'z_score': z_score, 'strategy': 'One-sided', 'price': entry_ask_price, 'lots': position['lots'],
            'gross_pnl': 0, 'net_pnl': 0, 'cumulative_gross_pnl': global_gross_cum_pnl, 'cumulative_net_pnl': global_net_cum_pnl, 
            'exchange': exchange, 'run_id': run_id
        })
    except Exception as e:
        print(f"Error opening position for {symbol_pair}: {e}")

def close_position(position, pnl_list, symbol_pair, timestamp, z_score, exit_bid_price, maker_fee, 
                   adjusted_position_size, global_gross_cum_pnl, global_net_cum_pnl, action, reinvest, exchange, run_id):
    try:
        position['open'] = False
        gross_pnl = position['lots'] * (exit_bid_price - position['entry_price'])
        net_pnl = gross_pnl - maker_fee * adjusted_position_size
        updated_global_gross_cum_pnl = global_gross_cum_pnl + gross_pnl
        updated_global_net_cum_pnl = global_net_cum_pnl + net_pnl
        
        pnl_list.append({
            'pair': symbol_pair, 'timestamp': timestamp, 'action': action,
            'z_score': z_score, 'strategy': 'One-sided', 'price': exit_bid_price, 'lots': position['lots'],
            'gross_pnl': gross_pnl, 'net_pnl': net_pnl, 'cumulative_gross_pnl': global_gross_cum_pnl, 'cumulative_net_pnl': global_net_cum_pnl, 
            'exchange': exchange, 'run_id': run_id
        })
        
        if reinvest:
            new_position_size = adjusted_position_size + net_pnl
        else:
            new_position_size = adjusted_position_size

        return updated_global_gross_cum_pnl, updated_global_net_cum_pnl, new_position_size
    except Exception as e:
        print(f"Error closing position for {symbol_pair}: {e}")
        return global_gross_cum_pnl, global_net_cum_pnl, adjusted_position_size  # Return the original values in case of an error


def backtest_zscores_one_sided_bid_ask(prices, sorted_pairs, threshold, position_size, 
                                       stop_loss_limit, profit_limit, exchange, run_id, maker_fee=0.1, reinvest=True):
    pnl_list = []
    global_gross_cum_pnl = 0
    global_net_cum_pnl = 0
    initial_position_size = position_size
    
    stop_loss_limit /= 100
    profit_limit /= 100
    maker_fee /= 100

    positions = initialize_positions(sorted_pairs)

    for index, row in sorted_pairs.iterrows():
        asset1, asset2 = row['Asset1'], row['Asset2']
        symbol_pair = f"{asset1}-{asset2}"
        
        adjusted_position_size = position_size / len(sorted_pairs) if len(sorted_pairs) > 0 else 0

        try:
            merged_prices, z_scores = merge_and_calculate_ratios(prices, asset1, asset2)

            for i, z_score in enumerate(z_scores):
                timestamp = merged_prices.iloc[i]['timestamp_asset1']
                position = positions[symbol_pair]

                if not position['open'] and z_score < -threshold:
                    entry_ask_price = merged_prices.iloc[i]['ask_asset1']
                    open_position(position, pnl_list, symbol_pair, timestamp, z_score, entry_ask_price, 
                                  adjusted_position_size, global_gross_cum_pnl, global_net_cum_pnl, exchange, run_id)

                elif position['open']:
                    exit_bid_price = merged_prices.iloc[i]['bid_asset1']
                    change_percentage = (exit_bid_price - position['entry_price']) / position['entry_price']
                    action = 'Closed with Stop Loss' if change_percentage <= -stop_loss_limit else 'Closed with Profit'
                    if change_percentage <= -stop_loss_limit or change_percentage >= profit_limit:
                        global_gross_cum_pnl, global_net_cum_pnl, adjusted_position_size = close_position(
                            position, pnl_list, symbol_pair, timestamp, z_score, exit_bid_price, maker_fee, adjusted_position_size, 
                            global_gross_cum_pnl, global_net_cum_pnl, action, reinvest, exchange, run_id
                        )

        except Exception as e:
            print(f"Error processing {symbol_pair}: {e}")

    # Update the position size for the next iteration if reinvesting
    if reinvest:
        position_size = initial_position_size + global_net_cum_pnl

    pnl_df = pd.DataFrame(pnl_list)
    pnl_df['gross_pnl'] = pd.to_numeric(pnl_df['gross_pnl'], errors='coerce').fillna(0)
    return pnl_df

def backtest_zscores_one_sided_close(prices, sorted_pairs, threshold, 
                                    position_size, stop_loss_limit, profit_limit, maker_fee, reinvest_profits, exchange, run_id):
    pnl_list = []
    positions = {}
    pivot_prices = prices.pivot(index='timestamp', columns='symbol', values='close')
    global_gross_cum_pnl = 0  # Initialize cumulative PnL as a global variable
    global_net_cum_pnl = 0  # Initialize cumulative PnL as a global variable
    
    # Calculate position size per pair
    num_pairs = len(sorted_pairs)
    position_size_per_pair = position_size / num_pairs if num_pairs > 0 else 0
    
    # Adjust limits and fees to decimal form
    stop_loss_limit /= 100
    profit_limit /= 100
    maker_fee /= 100
    
    for index, row in sorted_pairs.iterrows():
        asset1, asset2 = row['Asset1'], row['Asset2']
        symbol_pair = f"{asset1}-{asset2}"
        
        if symbol_pair not in positions:
            positions[symbol_pair] = {'open': False, 'entry_price': 0, 'lots': 0}

        if asset1 in pivot_prices.columns and asset2 in pivot_prices.columns:
            price_ratios = pivot_prices[asset1] / pivot_prices[asset2]
            z_scores = zscore(price_ratios.dropna())

            for timestamp, z_score in zip(price_ratios.index, z_scores):
                position = positions[symbol_pair]

                if not position['open'] and z_score < -threshold:
                    entry_price = pivot_prices.loc[timestamp, asset1]
                    if entry_price > 0:
                        position['open'] = True
                        position['entry_price'] = entry_price
                        # Use position_size_per_pair to calculate lots
                        position['lots'] = position_size_per_pair / entry_price
                        pnl_list.append({
                            'pair': symbol_pair, 'timestamp': timestamp, 'action': 'Open Position',
                            'z_score': z_score, 'strategy': 'One-sided', 'price': entry_price, 'lots': position['lots'],
                            'gross_pnl': '', 'net_pnl': '', 'cumulative_gross_pnl': global_gross_cum_pnl, 'cumulative_net_pnl': global_net_cum_pnl, 
                            'exchange': exchange, 'run_id': run_id
                        })

                elif position['open']:
                    exit_price = pivot_prices.loc[timestamp, asset1]
                    change_percentage = (exit_price - position['entry_price']) / position['entry_price']
                    if change_percentage <= -stop_loss_limit or change_percentage >= profit_limit:
                        position['open'] = False
                        gross_pnl = position['lots'] * (exit_price - position['entry_price'])
                        net_pnl = gross_pnl - maker_fee * position_size_per_pair  # Use position_size_per_pair for fee calculation
                        global_gross_cum_pnl += gross_pnl
                        global_net_cum_pnl += net_pnl
                        action = 'Closed with Stop Loss' if change_percentage <= -stop_loss_limit else 'Closed with Profit'
                        pnl_list.append({
                            'pair': symbol_pair, 'timestamp': timestamp, 'action': action,
                            'z_score': z_score, 'strategy': 'One-sided', 'price': exit_price, 'lots': position['lots'],
                            'gross_pnl': gross_pnl, 'net_pnl': net_pnl, 'cumulative_gross_pnl': global_gross_cum_pnl, 'cumulative_net_pnl': global_net_cum_pnl, 
                            'exchange': exchange, 'run_id': run_id
                        })
    pnl_df = pd.DataFrame(pnl_list)
    pnl_df['gross_pnl'] = pd.to_numeric(pnl_df['gross_pnl'], errors='coerce').fillna(0)
    return pnl_df

def get_correlation_pairs(returns):
    # Compute the correlation matrix
    correlation_matrix = returns.corr()

    # Flatten the correlation matrix and reset index
    corr_pairs = correlation_matrix.unstack().reset_index()

    # Rename columns for clarity
    corr_pairs.columns = ['Asset1', 'Asset2', 'Correlation']

    # Remove self-correlation
    corr_pairs = corr_pairs[corr_pairs['Asset1'] != corr_pairs['Asset2']]

    # Filter out duplicate pairs by ensuring Asset1 < Asset2
    corr_pairs = corr_pairs[corr_pairs['Asset1'] < corr_pairs['Asset2']]

    # Sort by absolute correlation values
    corr_pairs['Absolute Correlation'] = corr_pairs['Correlation'].abs()
    sorted_pairs = corr_pairs.sort_values(by='Absolute Correlation', ascending=False)

    return sorted_pairs[['Asset1', 'Asset2', 'Correlation']]

def calculate_returns(all_data):
    # Convert columns to numeric types (excluding 'timestamp' and 'symbol')
    numeric_cols = ['bid', 'ask', 'close']
    for col in numeric_cols:
        all_data[col] = pd.to_numeric(all_data[col], errors='coerce')

    # Filter data for each symbol and calculate one-minute returns
    symbols = all_data['symbol'].unique()
    returns = pd.DataFrame(index=all_data['timestamp'].unique())

    for symbol in symbols:
        # Filter data for the current symbol
        symbol_data = all_data[all_data['symbol'] == symbol]

        # Calculate one-minute returns and add to the returns DataFrame
        symbol_returns = symbol_data.set_index('timestamp')['close'].pct_change()
        returns[symbol] = symbol_returns

    return returns
    
def backtest_zscores_one_sided_ba_synthetic(prices, sorted_pairs, threshold, position_size, stop_loss_limit, profit_limit, maker_fee=0.1):
    pnl_list = []
    positions = {}
    pivot_prices = prices.pivot(index='timestamp', columns='symbol', values='close')
    global_gross_cum_pnl = 0  # Initialize cumulative PnL as a global variable
    global_net_cum_pnl = 0  # Initialize cumulative PnL as a global variable
    stop_loss_limit = stop_loss_limit / 100
    profit_limit = profit_limit / 100
    maker_fee = maker_fee / 100
    spread = 0.1
    
    for index, row in sorted_pairs.iterrows():
        asset1, asset2 = row['Asset1'], row['Asset2']
        symbol_pair = f"{asset1}-{asset2}"
        
        # Ensure each pair's position is tracked individually, but PnL is accumulated globally
        if symbol_pair not in positions:
            positions[symbol_pair] = {'open': False, 'entry_price': 0, 'lots': 0}

        if asset1 in pivot_prices.columns and asset2 in pivot_prices.columns:
            price_ratios = pivot_prices[asset1] / pivot_prices[asset2]
            z_scores = zscore(price_ratios.dropna())

            for timestamp, z_score in zip(price_ratios.index, z_scores):
                position = positions[symbol_pair]

                if not position['open'] and z_score < -threshold:
                    entry_price = pivot_prices.loc[timestamp, asset1]
                    entry_price = get_ask(entry_price, spread)
                    
                    if entry_price > 0:
                        position['open'] = True
                        position['entry_price'] = entry_price
                        position['lots'] = position_size / entry_price
                        pnl_list.append({
                            'Pair': symbol_pair, 'Timestamp': timestamp, 'Action': 'Open Position',
                            'Z-Score': z_score, 'Strategy': 'One-sided', 'Price': entry_price, 'Lots': position['lots'], 'Gross PnL': '', 'Net PnL': '',
                            'Cumulative Gross PnL': global_gross_cum_pnl, 'Cumulative Net PnL': global_net_cum_pnl
                        })

                elif position['open']:
                    exit_price = pivot_prices.loc[timestamp, asset1]
                    exit_price = get_bid(entry_price, spread)
                    change_percentage = (exit_price - position['entry_price']) / position['entry_price']                    
                    if change_percentage <= -stop_loss_limit or change_percentage >= profit_limit:
                        position['open'] = False
                        gross_pnl = position['lots'] * (exit_price - position['entry_price'])
                        net_pnl = position['lots'] * (exit_price - position['entry_price']) - maker_fee * position_size
                        global_gross_cum_pnl += gross_pnl
                        global_net_cum_pnl += net_pnl
                        action = 'Closed with Stop Loss' if change_percentage <= -stop_loss_limit else 'Closed with Profit'
                        pnl_list.append({
                            'Pair': symbol_pair, 'Timestamp': timestamp, 'Action': action,
                            'Z-Score': z_score, 'Strategy': 'One-sided', 'Price': exit_price, 'Gross PnL': gross_pnl, 'Net PnL': net_pnl,
                            'Cumulative Gross PnL': global_gross_cum_pnl, 'Cumulative Net PnL': global_net_cum_pnl
                        })

    return pd.DataFrame(pnl_list)
