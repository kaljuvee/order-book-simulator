import ccxt
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
from utils import exchange_factory, db_util
from pprint import pprint

exchanges = exchange_factory.exchanges

def adjust_price_precision(exchange, symbol, price):
    market_info = exchange.market(symbol)
    price_precision = market_info['precision']['price']
    return round(price, price_precision)

def adjust_amount_precision(exchange, symbol, amount):
    market_info = exchange.market(symbol)
    amount_precision = market_info['precision']['amount']
    return round(amount, amount_precision)

def check_exchange_symbol_balance(exchange, symbol):
    try:
        # Ensure the exchange has been loaded with markets
        exchange.load_markets()
        
        # Fetch the account balance
        balance = exchange.fetch_balance()
        
        # Extract the balance for the specified symbol
        symbol_balance = balance['total'].get(symbol, 0)
        
        print(f"{exchange.id} balance for {symbol}: {symbol_balance}")
        return symbol_balance
    except Exception as e:
        print(f"An error occurred while fetching balance for {symbol} from {exchange.id}: {e}")
        return None


def adjust_price_precision(exchange, symbol, price):
    market = exchange.market(symbol)
    return round(price, market['precision']['price'])

def place_stop_loss(exchange, symbol, amount, stop_price, exit_discount=0.001, trailing_delta=0):
    try:
        # Fetch the latest ticker data for the symbol to ensure stop_price is appropriate
        ticker = exchange.fetch_ticker(symbol)
        latest_price = ticker['last']

        # Adjust stop_price only if it's higher than the latest price, which is unlikely for a sell stop
        if stop_price >= latest_price:
            stop_price *= (1 - exit_discount)

        # Set the limit price slightly below the stop price to increase the likelihood of the order being filled
        limit_price = stop_price * (1 - exit_discount)

        # Adjust the prices to match the exchange's required precision
        adjusted_stop_price = adjust_price_precision(exchange, symbol, stop_price)
        adjusted_limit_price = adjust_price_precision(exchange, symbol, limit_price)

        # Prepare the parameters
        params = {
            'stopPrice': adjusted_stop_price,  # This is where Binance expects the stopPrice
            'type': 'STOP_LOSS_LIMIT',
            'trailingDelta': 1.0  # 1% trailing stop for Binance
        }

        print(f"Placing stop loss order for {symbol} with params: {params}")

        # Place the stop loss limit order
        stop_exit_order = exchange.create_order(symbol=symbol, type='STOP_LOSS_LIMIT', side='sell',
                                              amount=amount, price=adjusted_limit_price, params=params)
        return stop_exit_order

    except Exception as e:
        print(f"Error placing stop loss order: {e}")
        return None

def place_limit_order(exchange, symbol, side, amount, price, reason='entry', max_wait_time=60, check_interval=5, check_order_status=True):
    try:
        params = {
            'price': price,
            'amount': amount,  # Adjusted limit price for the STOP_LOSS_LIMIT order
            'side': side,
            'type': 'limit'
        }
        print(f"Attempting to place order for {symbol} with {params}")
        order = exchange.create_order(symbol, **params)
        order_id = order.get('id')

        if not order_id:
            print("Failed to retrieve order ID.")
            return None

        print(f"Order {order_id} for {reason} placed, checking for fill status...")
        
        if check_order_status:
             print("checking for fill status...")
             start_time = time.time()
             while time.time() - start_time < max_wait_time:
                order_status = exchange.fetch_order(order_id, symbol)
                if order_status['status'] == 'closed':
                    print(f"Order {order_id} for {reason} is filled.")
                    return order_status
                time.sleep(check_interval)
        if check_order_status:
            print(f"Order {order_id} for {reason} was not filled within {max_wait_time} seconds.")
        return order

    except Exception as e:
        print(f"Error occurred while placing the limit order: {e}, reason: {reason}")
        return None


def get_symbol_balance(exchange, symbol):
    try:
        base_currency = symbol.split('/')[0]
        #base_ccy_amount = check_exchange_symbol_balance(exchange, base_currency)
        balance = exchange.fetch_balance()
        total_balance = balance[base_currency]['total'] 
        available_balance = balance[base_currency]['free'] 
        print(f"order_util.get_symbol_balance:total_balance: {total_balance}.")
        print(f"order_util.get_symbol_balance:available_balance: {available_balance}.")
        return available_balance
    except Exception as e:
        print(f"An error occurred while fetching symbol balance: {e}")
        return None
    
def check_order_status(exchange, order_id, symbol):
    try:
        #exchange = exchanges[exchange_id]
        order_status = exchange.fetch_order(order_id, symbol)
        return order_status
    except Exception as e:
        print(f"An error occurred while checking the order status: {e}")
        return None

def cancel_order(exchange, order_id, symbol):
    try:
        # Cancel the order
        result = exchange.cancel_order(order_id, symbol)
        print("Order canceled successfully:", result)
        return result
    except Exception as e:
        print("An error occurred while canceling the order:", str(e))

def place_market_sell_order(exchange, symbol, amount):
    try:
        # Create a market sell order
        order = exchange.create_order(symbol, 'market', 'sell', amount)
        print("order_util.place_market_sell_order: Market sell order placed successfully:")
        pprint(order)
        return order
    except Exception as e:
        print("An error occurred while placing a market sell order:", str(e))

def get_latest_price(exchange, symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        latest_price = ticker['last']  # 'last' is typically used for the latest market price
        return latest_price
    except Exception as e:
        print(f"An error occurred while fetching the latest price for {symbol}: {e}")
        return None

def get_latest_bid_ask(exchange_id, symbol):
    # Initialize the exchange
    exchange_class = getattr(ccxt, exchange_id)()
    
    # Check if the exchange has the required capability
    if not exchange_class.has['fetchOrderBook']:
        print(f"{exchange_id} does not support fetching order book.")
        return None

    try:
        # Load markets if not already loaded
        exchange_class.load_markets()

        # Fetch the order book for the given symbol
        order_book = exchange_class.fetch_order_book(symbol)

        # Extract the topmost bid and ask
        top_bid = order_book['bids'][0][0] if order_book['bids'] else None
        top_ask = order_book['asks'][0][0] if order_book['asks'] else None

        return {
            'symbol': symbol,
            'bid': top_bid,
            'ask': top_ask
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
