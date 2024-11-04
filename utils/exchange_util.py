import pandas as pd
import ccxt
import math
from datetime import datetime, timedelta
import pytz

def get_top_symbols_by_volume_base_ccy(exchange_id, base_currency, limit=15):
    try:
        # Initialize the exchange
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class()

        # Load markets
        exchange.load_markets()

        # Fetch ticker information for all symbols
        tickers = exchange.fetch_tickers()

        # Filter tickers for those paired with the specified base currency
        filtered_tickers = {
            symbol: ticker for symbol, ticker in tickers.items()
            if symbol.endswith(f'/{base_currency}')
        }

        # Sort the filtered tickers by volume and get the top 'limit' tickers
        sorted_tickers = sorted(
            filtered_tickers.values(), key=lambda x: x['quoteVolume'], reverse=True
        )[:limit]

        # Create a list of top symbols with their volumes
        top_symbols = [ticker['symbol'] for ticker in sorted_tickers]
        return top_symbols
    except Exception as e:
        return str(e)  # Return error message in case of an exception

def get_symbols_usd(exchange_id):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class()
        all_symbols = exchange.load_markets().keys()

        # Specify the base currencies you want to exclude
        excluded_base_currencies = ['GBP', 'EUR', 'CHF']

        # Filter to include only symbols that are paired with USD or USDT, but not with the excluded base currencies
        filtered_symbols = [
            symbol for symbol in all_symbols 
            if (symbol.endswith('/USD') or symbol.endswith('/USDT')) and not any(symbol.startswith(excluded_base + '/') for excluded_base in excluded_base_currencies)
        ]

        return filtered_symbols, None  # Return symbols and no error
    except Exception as e:
        return [], str(e)  # Return empty list and error message

def get_prices(exchange_id, selected_symbols, timeframe, days=1):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class()

        all_data = pd.DataFrame()
        limit_per_call = 1440
        interval_in_milliseconds = 60000
        total_data_points = limit_per_call * days
        number_of_calls = math.ceil(total_data_points / limit_per_call)
        
        for symbol in selected_symbols:
            for i in range(number_of_calls):
                if exchange_id == 'bybit':
                    since = None if i == 0 else exchange.milliseconds() - (86400000 * days) + (i * limit_per_call * interval_in_milliseconds)
                else:
                    since = exchange.milliseconds() - (86400000 * days) + (i * limit_per_call * interval_in_milliseconds)
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit_per_call)
                data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
                data['symbol'] = symbol
                all_data = pd.concat([all_data, data], ignore_index=True)

        return all_data.sort_values(by='timestamp').reset_index(drop=True)
    except Exception as e:
        print(f"Error fetching data from {exchange_id}: {e}")
        return pd.DataFrame()


def get_latest_price_exchange(exchange, symbol):
    try:
        exchange_id = exchange['exchange_id']
        print(f"get_latest_price: getting {symbol} on {exchange_id}.")
        
        # Check if the exchange has fetchTicker method
        if not exchange.has['fetchTicker']:
            raise Exception(f"{exchange_id} does not support fetchTicker method.")
        
        # Fetch the latest ticker data for the symbol
        ticker = exchange.fetch_ticker(symbol)
        
        # Extract the latest price from the ticker data
        latest_price = ticker['last']  # 'last' price is typically considered the latest price
        
        return latest_price
    except Exception as e:
        print(f"get_latest_price: an error occurred while fetching the latest price for {symbol} on {exchange_id}: {e}")
        return None

def get_latest_price(exchange_id, symbol):
    try:
        print(f"get_latest_price: getting {symbol} on {exchange_id}.")
        # Initialize the exchange
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class()
        
        # Check if the exchange has fetchTicker method
        if not exchange.has['fetchTicker']:
            raise Exception(f"{exchange_id} does not support fetchTicker method.")
        
        # Fetch the latest ticker data for the symbol
        ticker = exchange.fetch_ticker(symbol)
        
        # Extract the latest price from the ticker data
        latest_price = ticker['last']  # 'last' price is typically considered the latest price
        
        return latest_price
    except Exception as e:
        print(f"get_latest_price: an error occurred while fetching the latest price for {symbol} on {exchange_id}: {e}")
        return None

def get_prices_by_minute(exchange_id, selected_symbols, timeframe, minutes=5):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class()
        
        all_data = pd.DataFrame()
        limit_per_call = 1440  # Assuming this as a common safe limit; adjust based on exchange specifics
        interval_in_milliseconds = 60000  # For 1m timeframe; adjust if using a different timeframe
        
        # Calculate the number of milliseconds to go back
        milliseconds_to_go_back = minutes * interval_in_milliseconds
        since = exchange.milliseconds() - milliseconds_to_go_back
        
        for symbol in selected_symbols:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit_per_call)
            data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
            data['symbol'] = symbol
            all_data = pd.concat([all_data, data], ignore_index=True)
                
        return all_data.sort_values(by='timestamp').reset_index(drop=True)
    except Exception as e:
        print(f"Error fetching data from {exchange_id}: {e}")
        return pd.DataFrame()

def get_n_minute_change(exchange_id, selected_symbols, time_window, tick_interval):
    try:
        # Fetch historical data
        all_data = get_prices_by_minute(exchange_id, selected_symbols, tick_interval, int(time_window))
        
        # Initialize a list to collect data
        changes_list = []
        
        for symbol in selected_symbols:
            # Filter data for the current symbol
            symbol_data = all_data[all_data['symbol'] == symbol]
            
            # Calculate the change over the specified time window
            symbol_data = symbol_data.set_index('timestamp').resample(f'{time_window}min').agg({'close': 'last', 'volume': 'sum'}).dropna()
            symbol_data['percent_change_close'] = symbol_data['close'].pct_change() * 100
            symbol_data['percent_change_volume'] = symbol_data['volume'].pct_change() * 100
            
            # If there are changes, get the latest and add to the changes_list
            if not symbol_data.empty:
                latest_change = symbol_data.iloc[-1]
                changes_list.append({
                    'symbol': symbol,
                    'percent_change_close': latest_change['percent_change_close'],
                    'percent_change_volume': latest_change['percent_change_volume'],
                    'close': latest_change['close']  # Include 'close' price in the final DataFrame
                })
        
        # Create a DataFrame from the list
        result = pd.DataFrame(changes_list)
        
        # Sort the result DataFrame by 'percent_change_close' in descending order
        
        return result
    except Exception as e:
        print(f"An error occurred during the calculation: {e}")
    return pd.DataFrame(columns=['symbol', 'percent_change_close', 'percent_change_volume', 'close'])  # Return an empty DataFrame with the specified columns in case of error

def get_bottom_price_movers(exchange_id, selected_symbols, time_window, tick_interval, symbol_options):
    # Fetch trading data and calculate percentage changes
    changes = get_n_minute_change(exchange_id, selected_symbols, time_window, tick_interval)
    changes = changes.sort_values(by='percent_change_close', ascending=True).reset_index(drop=True)
    # Apply the cutoff based on symbol_options to limit the number of symbols displayed
    limited_changes = changes.head(symbol_options)
    return limited_changes

def get_top_price_movers(exchange_id, selected_symbols, time_window, tick_interval, symbol_options):
    # Fetch trading data and calculate percentage changes
    changes = get_n_minute_change(exchange_id, selected_symbols, time_window, tick_interval)
    changes = changes.sort_values(by='percent_change_close', ascending=False).reset_index(drop=True)
    # Apply the cutoff based on symbol_options to limit the number of symbols displayed
    limited_changes = changes.head(symbol_options)
    return limited_changes

def fetch_order_book_data_by_symbol(exchange_id, symbol):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({'enableRateLimit': True})  # Enable rate limit to avoid being banned by the exchange
        order_book = exchange.fetch_order_book(symbol)
        
        bid_volume = sum([order[1] for order in order_book['bids']])
        ask_volume = sum([order[1] for order in order_book['asks']])
        volume_ratio = bid_volume / ask_volume if ask_volume != 0 else None  # Avoid division by zero

        # Get the top of the order book
        top_bid_price = order_book['bids'][0][0] if order_book['bids'] else None  # Highest bid price
        top_ask_price = order_book['asks'][0][0] if order_book['asks'] else None  # Lowest ask price
        
        return bid_volume, ask_volume, volume_ratio, top_bid_price, top_ask_price
    except Exception as e:
        print(f"Error fetching order book data for {symbol} from {exchange_id}: {e}")
        return None, None, None, None, None  # Return None values in case of an error

def get_btc_price_history(exchange_list, start_date, end_date, timeframe='1m'):
    all_data = pd.DataFrame()
    limit_per_call = 1440  # Assuming this as a common safe limit; adjust based on exchange specifics
    timeframes = {
        "1m": 60000,
        "5m": 300000,
        "15m": 900000,
        "30m": 1800000,
        "1h": 3600000,
        "6h": 21600000,
        "12h": 43200000,
        "1d": 86400000,
        "1w": 604800000
    }
    interval_in_milliseconds = timeframes.get(timeframe, 60000)  # Default to 1m if not found

    start_timestamp = int(pd.to_datetime(start_date).timestamp() * 1000)
    end_timestamp = int(pd.to_datetime(end_date).timestamp() * 1000)
    total_time_range = end_timestamp - start_timestamp
    total_data_points = math.ceil(total_time_range / interval_in_milliseconds)
    number_of_calls = math.ceil(total_data_points / limit_per_call)

    nasdaq_open = datetime.strptime("09:30:00", "%H:%M:%S").time()
    nasdaq_close = datetime.strptime("16:00:00", "%H:%M:%S").time()
    est = pytz.timezone("US/Eastern")

    for exchange_id in exchange_list:
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class()

            for i in range(number_of_calls):
                since = start_timestamp + (i * limit_per_call * interval_in_milliseconds)
                ohlcv = exchange.fetch_ohlcv('BTC/USD', timeframe, since, limit=limit_per_call)
                data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert(est)

                # Filter out data outside of NASDAQ market hours and end date
                data = data[data['timestamp'].dt.time.between(nasdaq_open, nasdaq_close)]
                data = data[data['timestamp'].dt.tz_localize(None) <= pd.to_datetime(end_date)]

                if not data.empty:
                    data['symbol'] = 'BTC/USD-' + exchange_id.upper()
                    all_data = pd.concat([all_data, data], ignore_index=True)
        except Exception as e:
            print(f"Error fetching BTC/USD data from {exchange_id}: {e}")

    return all_data.sort_values(by='timestamp').reset_index(drop=True)


def get_btc_usd_price_history_by_exchange(exchange_id, timeframe, days=1):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class()
        
        all_data = pd.DataFrame()
        limit_per_call = 1440  # Assuming this as a common safe limit; adjust based on exchange specifics
        # Adjust the interval_in_milliseconds based on the selected timeframe
        timeframes = {
            "1m": 60000,
            "5m": 300000,
            "15m": 900000,
            "30m": 1800000,
            "1h": 3600000,
            "6h": 21600000,
            "12h": 43200000,
            "1d": 86400000,
            "1w": 604800000
        }
        interval_in_milliseconds = timeframes.get(timeframe, 60000)  # Default to 1m if not found
        total_data_points = limit_per_call * days
        number_of_calls = math.ceil(total_data_points / limit_per_call)
        
        for i in range(number_of_calls):
            since = exchange.milliseconds() - (86400000 * days) + (i * limit_per_call * interval_in_milliseconds)
            ohlcv = exchange.fetch_ohlcv('BTC/USD', timeframe, since, limit_per_call)
            data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
            data['symbol'] = 'BTC/USD'
            all_data = pd.concat([all_data, data], ignore_index=True)
                
        return all_data.sort_values(by='timestamp').reset_index(drop=True)
    except Exception as e:
        print(f"Error fetching BTC/USD data from {exchange_id}: {e}")
        return pd.DataFrame()

