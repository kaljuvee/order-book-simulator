from datetime import datetime, timezone, timedelta
from util import exchange_factory, db_util
import pandas as pd
import pytz

def store_order(order_data):
    try:
        # Convert timestamp to UTC datetime
        utc_datetime = datetime.fromtimestamp(order_data['timestamp'] / 1000, pytz.utc)
        
        # Define the Eastern timezone
        eastern = pytz.timezone('America/New_York')
        
        # Convert UTC datetime to Eastern Time (automatically handles EST/EDT)
        est_datetime = utc_datetime.astimezone(eastern).strftime('%Y-%m-%d %H:%M:%S')
        # Order details
        order_details = {
            'order_id': order_data['info']['orderId'],
            'client_order_id': order_data['clientOrderId'],
            'symbol': order_data['symbol'],
            'utc_transact_time': utc_datetime,
            'est_transact_time': est_datetime,
            'price': order_data['price'],
            'orig_qty': order_data['amount'],
            'executed_qty': order_data['filled'],
            'cummulative_quote_qty': order_data['cost'],
            'status': order_data['status'],
            'type': order_data['type'],
            'side': order_data['side'],
            'time_in_force': order_data['timeInForce']
        }   
        #orders_df = pd.DataFrame(order_details)
        orders_df = pd.DataFrame([order_details], index=[0])
        db_util.write_table_append(orders_df, 'orders')
        print(f"store_order: order data stored: {orders_df}")

    except Exception as e:
        print(f"store_order: an error occurred while storing the order data: {e}")
        return None

    # Further code to store orders_df, fills_df, and fees_df to the database can be added here.

