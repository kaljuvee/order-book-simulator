import alpaca_trade_api as tradeapi
import pandas as pd
from datetime import datetime, timedelta

# Configure your Alpaca API key and secret
# Alpaca API credentials
API_KEY = 'PKWSHV3AS4J71TGOQEOC'
API_SECRET = 'wffi5PYdLHI2N/6Kfqx6LBTuVlfURGgOp9u5mXo5'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'  # or https://api.alpaca.markets for live trading

# Initialize the Alpaca API
api = tradeapi.REST(API_KEY, API_SECRET, ALPACA_BASE_URL, api_version='v2')

crypto_symbols = [
    'AAVE/USDT', 'BCH/USDT', 'BTC/USDT', 'ETH/USDT',
    'LINK/USDT', 'LTC/USDT', 'UNI/USDT',
    'AAVE/USD', 'AVAX/USD', 'BAT/USD', 'BCH/USD',
    'BTC/USD', 'CRV/USD', 'DOT/USD', 'ETH/USD',
    'GRT/USD', 'LINK/USD', 'LTC/USD', 'MKR/USD',
    'SHIB/USD', 'UNI/USD', 'XTZ/USD'
    ]

def get_prices(selected_symbols, timeframe='1Min', time_window=60):
    all_data = pd.DataFrame()
    start_date = (datetime.now() - timedelta(minutes=time_window)).replace(microsecond=0).isoformat() + 'Z'
    end_date = datetime.now().replace(microsecond=0).isoformat() + 'Z'

    print(f"Start Date: {start_date}, End Date: {end_date}")  # Debug print

    for symbol in selected_symbols:
        print(f"Fetching data for symbol: {symbol}")  # Debug print
        try:
            bars = api.get_crypto_bars(symbol, timeframe, start=start_date, end=end_date).df
            if bars.empty:
                print(f"No data returned for {symbol}")  # Debug print
            else:
                bars['symbol'] = symbol
                all_data = pd.concat([all_data, bars], ignore_index=True)
        except Exception as e:
            print(f"An error occurred while fetching data for {symbol}: {e}")
            # Optionally, continue to the next symbol or handle the error as needed

    if all_data.empty:
        print("No data found for any symbols.")
        return pd.DataFrame()

    all_data.index = pd.to_datetime(all_data.index)
    all_data = all_data.rename_axis('timestamp').reset_index()

    return all_data.sort_values(by='timestamp').reset_index(drop=True)
    
def get_latest_crypto_price(symbol):
    try:
        # Fetch the latest bar data for the symbol
        bars = api.get_crypto_bars(symbol, '1Min').df
        
        if bars.empty:
            print(f"No data found for {symbol}")
            return None
        
        # The latest price is the close price of the last bar
        latest_price = bars['close'].iloc[-1]
        
        return latest_price
    except Exception as e:
        print(f"get_latest_crypto_price: An error occurred while fetching the latest price for {symbol}: {e}")
        return None

def main():
    print('old size:', len(crypto_symbols))
    selected_symbols = ['BTC/USD', 'ETH/USD']  # Example symbols, adjust as needed
    prices = get_prices(selected_symbols, '1Min', 15) 
    # Fetching latest prices for each symbol in the list
    #for symbol in crypto_symbols:
    #   price = get_latest_crypto_price(symbol)
    #   print(f"The latest price for {symbol} is {price}")
    print(prices)
if __name__ == "__main__":
    main()