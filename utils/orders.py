import ccxt
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
from utils.exchange_factory import exchanges
from utils.db_util import db_util

class OrderManager:
    def __init__(self, exchange):
        self.exchange = exchange

    def execute_trade_plan(self, symbol, buy_amount, entry_price, profit_exit_price, stop_loss_price, exit_discount):
        # Step 1: Place buy entry order
        entry_order = self.place_limit_order(symbol, 'buy', buy_amount, entry_price, 'entry')
        if entry_order is None:
            print("Failed to place entry order.")
            return False

        # Ensure the entry order is filled before proceeding
        if not self.wait_for_order_fill(entry_order['id'], symbol):
            print("Entry order not filled, aborting trade plan.")
            return False

        # Fetch the executed buy amount after order is filled for accurate sell order amounts
        executed_buy_amount = self.fetch_executed_amount(entry_order['id'], symbol)

        # Step 2: Place profit taking order
        if not self.place_limit_order(symbol, 'sell', executed_buy_amount, profit_exit_price, 'take_profit', check_order_status=False):
            print("Failed to place profit taking order.")
            return False

        # Step 3: Place stop loss order
        if not self.handle_stop_loss(symbol, executed_buy_amount, stop_loss_price, stop_loss_price * (1 - exit_discount)):
            print("Failed to place stop loss order.")
            return False

        print("All orders successfully placed.")
        return True

    def place_limit_order(exchange, symbol, side, amount, price, reason='entry', max_wait_time=60, check_interval=5, check_order_status=True):
        if side not in ['buy', 'sell']:
            print("Invalid side. Please choose 'buy' or 'sell'.")
            return None

        try:
            print(f"Attempting to place a {side} limit order for {symbol} with amount: {amount} and price: {price}")
            order = exchange.create_order(symbol, 'limit', side, amount, price)
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

            print(f"Order {order_id} for {reason} was not filled within {max_wait_time} seconds.")
            return None

        except Exception as e:
            print(f"Error occurred while placing the limit order: {e}, reason: {reason}")
            return None

    def handle_stop_loss(exchange, symbol, amount, stop_price, limit_price, exit_discount = 0.001):
        """
        Places a STOP_LOSS_LIMIT order on Binance.

        Parameters:
        - exchange: The ccxt exchange instance for Binance.
        - symbol: The trading symbol (e.g., 'BTC/USDT').
        - amount: The amount of the asset to sell.
        - stop_price: The price at which the stop loss is triggered.
        - limit_price: The limit price at which the order is placed once the stop price is reached.

        Returns:
        - The response from the exchange after placing the stop loss order.
        """
        adjusted_stop_price = None
        adjusted_limit_price = None
        # Prepare the parameters for the STOP_LOSS_LIMIT order
        stop_order_params = {
            'stopPrice': adjusted_stop_price,  # Adjusted price at which the stop loss will trigger
            'price': adjusted_limit_price  # Adjusted limit price for the STOP_LOSS_LIMIT order
        }
        # Inside the try block, before creating the STOP_LOSS_LIMIT order

        # Fetch the latest ticker data for the symbol
        try:
            ticker = exchange.fetch_ticker(symbol)
            latest_price = ticker['last'] 
            trailing_delta = float(exchange.price_to_precision(symbol, latest_price * 0.001)) # 0.1% of the latest price, adjusted to exchange's precision
            stop_order_params['trailingDelta'] = round(trailing_delta, 2)
            if stop_price >= latest_price:  # For a sell order, ensure stop_price is below the latest price
                stop_price *= (1 - exit_discount)  # Apply a discount to adjust the stop price

                # Adjust the stop_price and limit_price to the exchange's required precision
            adjusted_stop_price = round(float(exchange.price_to_precision(symbol, stop_price)),2)
            adjusted_limit_price = round(float(exchange.price_to_precision(symbol, limit_price)), 2)
            print('adjusted stop order params: ', stop_order_params)
            # Attempt to create a STOP_LOSS_LIMIT order
            stop_exit_order = exchange.create_order(symbol=symbol, type='STOP_LOSS_LIMIT', side='sell',
                                                    amount=amount, price=adjusted_limit_price, params=stop_order_params)
            return stop_exit_order

        except Exception as e:
            # Handle exceptions, such as connectivity issues or API errors
            print(f"An error occurred while placing the STOP_LOSS_LIMIT order: {str(e)}")
            return None

    def wait_for_order_fill(self, order_id, symbol, timeout=60):
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                order_status = self.exchange.fetch_order(order_id, symbol)
                if order_status['status'] == 'closed':  # The order is filled
                    return True
                elif order_status['status'] in ['canceled', 'rejected']:  # Order is not going to be filled
                    print(f"Order {order_id} was {order_status['status']}.")
                    return False
            except Exception as e:
                print(f"Error checking order status for {order_id}: {e}")
            time.sleep(5)  # Wait for 5 seconds before checking again to avoid hitting rate limits
        print(f"Timeout reached waiting for order {order_id} to fill.")
        return False


    def fetch_executed_amount(self, order_id, symbol):
        try:
            order_details = self.exchange.fetch_order(order_id, symbol)
            if order_details['status'] == 'closed':  # Ensure the order is filled
                executed_amount = order_details['filled']
                print(f"Executed amount for order {order_id} is {executed_amount}.")
                return executed_amount
            else:
                print(f"Order {order_id} is not filled; status: {order_details['status']}")
                return None
        except Exception as e:
            print(f"Error fetching executed amount for {order_id}: {e}")
            return None


    # You might also include additional utility methods as needed, such as balance checks, price adjustments, etc.
