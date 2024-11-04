from datetime import datetime
from util import exchange_util
import pandas as pd

def fetch_top_movers(exchange, lookback_window, tick_interval, base_currency, total_limit=50, top_limit=20):
    try:
        start_time = datetime.now()
        top_symbols = exchange_util.get_top_symbols_by_volume_base_ccy(exchange, base_currency, total_limit)
        top_movers = exchange_util.get_top_price_movers(exchange, top_symbols, lookback_window, tick_interval, top_limit)
    
        end_time = datetime.now()
        duration = end_time - start_time
        minutes, seconds = divmod(duration.seconds, 60)
        print(f"trend_follower_util.fetch_top_movers: got TOP MOVERS in {minutes} minutes and {seconds} seconds.")
        
        return top_movers
    except Exception as e:
        print(f"trend_follower_util.fetch_top_movers: error fetching top movers: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error

def fetch_order_book_data(top_movers, exchange):
    try:
        start_time = datetime.now()
        for index, row in top_movers.iterrows():
            #print(f"Getting order book data in {exchange} minutes and {row['symbol']} seconds.")
            # we may not need the bid price
            bid_volume, ask_volume, volume_ratio, bid_price, ask_price = exchange_util.fetch_order_book_data_by_symbol(exchange, row['symbol'])
            top_movers.at[index, 'volume_ratio'] = volume_ratio
            top_movers.at[index, 'bid_volume'] = bid_volume
            top_movers.at[index, 'ask_volume'] = ask_volume
            top_movers.at[index, 'bid_price'] = bid_price
            top_movers.at[index, 'ask_price'] = ask_price
            # Print the updated row to verify it's not empty
        end_time = datetime.now()
        duration = end_time - start_time
        minutes, seconds = divmod(duration.seconds, 60)
        print(f"trend_follower_util.fetch_top_movers: got ORDER BOOK data in {minutes} minutes and {seconds} seconds.")
    except Exception as e:
        print(f"trend_follower_util.fetch_top_movers: Error fetching order book data: {e}")
    return top_movers  # Ensure the updated DataFrame is returned
    
def check_entry_signal(top_movers, pump_threshold_pct):
    entry_signal = False
    top_symbol = None
    ask_price = None
    bid_price = None
    for _, row in top_movers.iterrows():
        try:
            # Check if the percentage change and volume ratio meet the threshold,
            # and the closing price is >= 1
            if row['close'] is not None and row['percent_change_close'] >= pump_threshold_pct and row['volume_ratio'] > 1 and row['close'] >= 1:
                entry_signal = True
                top_symbol = row['symbol']
                ask_price = row['ask_price']
                bid_price = row['bid_price']
                return entry_signal,  top_symbol, ask_price, bid_price
        except KeyError as e:
            print(f"trend_follower_util.check_entry_signal: KeyError: {e}. The required column is missing in the DataFrame.")
        except Exception as e:
            print(f"trend_follower_util.check_entry_signal: an unexpected error occurred: {e}")
    return entry_signal, top_symbol, ask_price, bid_price