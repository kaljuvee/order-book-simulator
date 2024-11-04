from datetime import datetime, timedelta
from util import exchange_util, db_util, file_util, order_util
import pandas as pd

def fetch_bottom_movers(exchange, selected_interval, total_limit=50, top_limit=20):
    try:
        start_time = datetime.now()
        top_symbols = exchange_util.get_top_symbols_by_volume_usd(exchange, total_limit)
        top_movers = exchange_util.get_bottom_price_movers(exchange, top_symbols, selected_interval, '1m', top_limit)
    
        end_time = datetime.now()
        duration = end_time - start_time
        minutes, seconds = divmod(duration.seconds, 60)
        print(f"fetch_bottom_movers: got bottom movers in {minutes} minutes and {seconds} seconds.")
        
        return top_movers
    except Exception as e:
        print(f"fetch_bottom_movers: error fetching bottom movers: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error

def fetch_order_book_data(top_movers, exchange):
    try:
        start_time = datetime.now()
        for index, row in top_movers.iterrows():
            #print(f"Getting order book data in {exchange} minutes and {row['symbol']} seconds.")
            bid_volume, ask_volume, volume_ratio = exchange_util.fetch_order_book_data_by_symbol(exchange, row['symbol'])
            top_movers.at[index, 'volume_ratio'] = volume_ratio
            top_movers.at[index, 'bid_volume'] = bid_volume
            top_movers.at[index, 'ask_volume'] = ask_volume
            # Print the updated row to verify it's not empty
        end_time = datetime.now()
        duration = end_time - start_time
        minutes, seconds = divmod(duration.seconds, 60)
        print(f"fetch_top_movers: got ORDER BOOK data in {minutes} minutes and {seconds} seconds.")
    except Exception as e:
        print(f"Error fetching order book data: {e}")
    return top_movers  # Ensure the updated DataFrame is returned
    
def check_entry_signal(top_movers, pump_threshold_pct):
    for _, row in top_movers.iterrows():
        try:
            # Check if the percentage change and volume ratio meet the threshold,
            # and the closing price is >= 1
            if row['close'] is not None and row['percent_change_close'] >= pump_threshold_pct and row['volume_ratio'] > 1 and row['close'] >= 1:
                return row['symbol'], row['close']  # Return symbol and entry price
        except KeyError as e:
            print(f"pump_strategy_util.check_entry_signal: KeyError: {e}. The required column is missing in the DataFrame.")
        except Exception as e:
            print(f"pump_strategy_util.check_entry_signal: an unexpected error occurred: {e}")
    return None, None

def check_exit_signal(latest_price, position_entry_price, volume_ratio, profit_target, stop_loss):
    exit_signal = False
    exit_reason = None
    try:
        percent_change_from_entry = (latest_price - position_entry_price) / position_entry_price * 100
        print(f"pump_strategy_util.check_exit_signal: percent_change_from_entry: {percent_change_from_entry}, volume_ratio: {volume_ratio}.")
        # Check if volume ratio condition is met; TODO: try different volume ratio treshholds (eg < 1 when the market has turned)
        if volume_ratio >= 1.0 and percent_change_from_entry > profit_target:
            exit_signal = True
            exit_reason = 'profit_target'
         
        elif volume_ratio < 1.0 and percent_change_from_entry < stop_loss:          # Exit signal due to profit target being hit
            exit_signal = True
            exit_reason = 'profit_target'

    except Exception as e:
        print(f"check_exit_signal: an error occurred: {e}")
    return exit_signal, exit_reason  # Default to no exit signal if conditions are not met or an error occurs