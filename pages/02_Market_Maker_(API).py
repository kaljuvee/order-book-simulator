import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal
from utils.orders import OrderManager
from utils.exchange_factory import exchanges, exchange_base_currencies

st.title("Market Maker (API)")

# Initialize session state variables
if 'trade_history_api' not in st.session_state:
    st.session_state.trade_history_api = []

# Exchange and symbol selection
available_exchanges = ['kraken', 'bybit', 'okx', 'binance']
selected_exchange = st.selectbox(
    "Select Exchange",
    available_exchanges
)

# Token selection
base_tokens = ['BTC', 'ETH', 'SOL', 'DOT']
selected_token = st.selectbox(
    "Select Token",
    base_tokens
)

# Create trading pair based on selected token and exchange's base currency
base_currency = exchange_base_currencies[selected_exchange]
trading_pair = f"{selected_token}/{base_currency}"

# Initialize exchange and order manager
exchange = exchanges[selected_exchange]
order_manager = OrderManager(exchange)

# Refresh button for order book
if st.button("Refresh Order Book"):
    try:
        order_book = exchange.fetch_order_book(trading_pair, limit=20)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Asks (Sell Orders)")
            asks_df = pd.DataFrame(order_book['asks'], columns=['Price', 'Quantity'])
            asks_df = asks_df.sort_values('Price', ascending=True)
            st.dataframe(asks_df, hide_index=True)

        with col2:
            st.write("Bids (Buy Orders)")
            bids_df = pd.DataFrame(order_book['bids'], columns=['Price', 'Quantity'])
            bids_df = bids_df.sort_values('Price', ascending=False)
            st.dataframe(bids_df, hide_index=True)

        # Update Market Summary
        st.subheader("Market Summary")
        col1, col2 = st.columns(2)
        with col1:
            best_bid = bids_df.iloc[0]['Price'] if not bids_df.empty else "No Bids"
            st.metric("Best Bid", f"${best_bid}")
        with col2:
            best_ask = asks_df.iloc[0]['Price'] if not asks_df.empty else "No Asks"
            st.metric("Best Ask", f"${best_ask}")

    except Exception as e:
        st.error(f"Error fetching order book: {str(e)}")

# Create two columns for order placement and cancellation
col1, col2 = st.columns(2)

with col1:
    st.subheader("Place New Order")
    with st.form("new_order_form"):
        side = st.selectbox("Side", ["BUY", "SELL"])
        price = st.number_input("Limit Price", min_value=0.01, value=1.00, step=0.01)
        quantity = st.number_input("Quantity", min_value=0.0001, value=0.01, step=0.0001)
        
        submit_button = st.form_submit_button("Place Limit Order")
        if submit_button:
            try:
                order = order_manager.place_limit_order(
                    trading_pair,
                    side.lower(),
                    quantity,
                    price
                )
                if order:
                    st.success(f"Limit order placed successfully! Order ID: {order['id']}")
                    # Add to trade history
                    trade_details = {
                        'Symbol': trading_pair,
                        'Order ID': order['id'],
                        'Type': 'LIMIT',
                        'Side': side,
                        'Price': price,
                        'Quantity': quantity,
                        'Status': order['status'],
                        'Timestamp': datetime.now()
                    }
                    st.session_state.trade_history_api.append(trade_details)
            except Exception as e:
                error_msg = str(e)
                if hasattr(e, 'args') and len(e.args) > 0:
                    error_msg = f"Exchange error: {e.args[0]}"
                st.error(f"Error placing limit order:\n{error_msg}")

with col2:
    st.subheader("Cancel Order")
    with st.form("cancel_order_form"):
        try:
            # Fetch open orders
            open_orders = exchange.fetch_open_orders(trading_pair)
            if open_orders:
                order_options = [(order['id'], f"{order['side'].upper()} {order['amount']} @ {order['price']}") 
                               for order in open_orders]
                selected_order = st.selectbox(
                    "Select Order to Cancel",
                    options=[order[0] for order in order_options],
                    format_func=lambda x: next(order[1] for order in order_options if order[0] == x)
                )
                
                cancel_button = st.form_submit_button("Cancel Order")
                if cancel_button:
                    try:
                        exchange.cancel_order(selected_order, trading_pair)
                        st.success(f"Order {selected_order} cancelled successfully!")
                    except Exception as e:
                        st.error(f"Failed to cancel order: {str(e)}")
            else:
                st.write("No active orders to cancel")
                st.form_submit_button("Cancel Order", disabled=True)
        except Exception as e:
            st.error(f"Error fetching open orders: {str(e)}")

# Display Trade History
st.subheader("Trade History")
if st.session_state.trade_history_api:
    trades_df = pd.DataFrame(st.session_state.trade_history_api)
    trades_df = trades_df.sort_values('Timestamp', ascending=False)
    st.dataframe(trades_df, hide_index=True)
else:
    st.write("No trades yet")
