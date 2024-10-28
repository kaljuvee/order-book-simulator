import streamlit as st
import sys
from decimal import Decimal
from datetime import datetime
import pandas as pd
from trade.order_matching import OrderBook, Order

st.title("Order Matching System")

# Initialize OrderBook and populate with sample OPTI orders
if 'order_books' not in st.session_state:
    st.session_state.order_books = {}
    st.session_state.order_counter = 0
    
    # Create OPTI order book and populate with sample orders
    opti_book = OrderBook()
    sample_orders = [
        Order("sim_sell_1", "OPTI", "SELL", Decimal("1.20"), 1000, datetime.now()),
        Order("sim_sell_2", "OPTI", "SELL", Decimal("1.15"), 500, datetime.now()),
        Order("sim_sell_3", "OPTI", "SELL", Decimal("1.10"), 750, datetime.now()),
        Order("sim_buy_1", "OPTI", "BUY", Decimal("1.05"), 800, datetime.now()),
        Order("sim_buy_2", "OPTI", "BUY", Decimal("1.00"), 1000, datetime.now()),
        Order("sim_buy_3", "OPTI", "BUY", Decimal("0.95"), 600, datetime.now()),
    ]
    
    for order in sample_orders:
        opti_book.add_order(order)
    
    st.session_state.order_books["OPTI"] = opti_book

# Add this near the top where other session state variables are initialized
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []

# Function to generate unique order IDs
def get_next_order_id():
    st.session_state.order_counter += 1
    return f"order_{st.session_state.order_counter}"

# Create two columns for the form
col1, col2 = st.columns(2)

with col1:
    st.subheader("Place New Order")
    with st.form("new_order_form"):
        # Add symbol selection
        symbol = st.selectbox(
            "Symbol",
            ["OPTI", "CLIP", "BTC", "ETH", "SOL"],
            help="Select the trading symbol"
        )
        
        # Add order type selection
        order_type = st.selectbox("Order Type", ["LIMIT", "MARKET"])
        
        side = st.selectbox("Side", ["BUY", "SELL"])
        
        # Show price input based on order type
        if order_type == "LIMIT":
            price = st.number_input("Price", min_value=0.01, value=1.10, step=0.01)
        else:
            # For market orders, show the best matching price
            best_price = None
            if symbol in st.session_state.order_books:
                snapshot = st.session_state.order_books[symbol].get_order_book_snapshot()
                if side == "BUY":
                    best_price = snapshot['best_ask']
                else:  # SELL
                    best_price = snapshot['best_bid']
            
            if best_price:
                st.write(f"Market Order - Best {'Ask' if side == 'BUY' else 'Bid'}: ${best_price}")
            else:
                st.write(f"No {'selling' if side == 'BUY' else 'buying'} orders available")
            price = "MARKET"
        
        quantity = st.number_input("Quantity", min_value=1, value=100, step=1)
        
        submit_button = st.form_submit_button("Place Order")
        if submit_button:
            try:
                order_id = get_next_order_id()
                
                # For market orders, set price to 0 for buys (will match lowest ask)
                # or infinity for sells (will match highest bid)
                if order_type == "MARKET":
                    price = Decimal('0') if side == "BUY" else Decimal('999999')
                else:
                    price = Decimal(str(price))
                
                new_order = Order(
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    price=price,
                    quantity=quantity,
                    timestamp=datetime.now()
                )
                
                # Initialize order book for symbol if it doesn't exist
                if symbol not in st.session_state.order_books:
                    st.session_state.order_books[symbol] = OrderBook()
                
                trades = st.session_state.order_books[symbol].add_order(new_order)
                if trades:
                    st.success(f"Order matched and FILLED! Generated {len(trades)} trades")
                    # Add trades to trade history
                    for trade in trades:
                        trade_details = {
                            'Symbol': symbol,
                            'Price': float(trade.price),
                            'Quantity': trade.quantity,
                            'Timestamp': datetime.now(),
                            'Buy Order': trade.buy_order_id,
                            'Sell Order': trade.sell_order_id
                        }
                        st.session_state.trade_history.append(trade_details)
                        st.write(f"Trade executed at ${trade.price}: {trade.quantity} units")
                    st.rerun()
                else:
                    if order_type == "MARKET":
                        st.error("No matching orders available for market order")
                    else:
                        st.success(f"Limit order placed successfully! ID: {order_id}")
            except Exception as e:
                st.error(f"Error placing order: {str(e)}")

with col2:
    st.subheader("Cancel Order")
    with st.form("cancel_order_form"):
        # Get list of active orders across all symbols
        active_orders = []
        for symbol, order_book in st.session_state.order_books.items():
            symbol_orders = [
                (order_id, order) 
                for order_id, order in order_book.orders.items() 
                if order.status == 'ACTIVE'
            ]
            active_orders.extend([(symbol, order_id, order) for order_id, order in symbol_orders])
        
        if active_orders:
            order_to_cancel = st.selectbox(
                "Select Order to Cancel",
                options=[(symbol, order_id) for symbol, order_id, _ in active_orders],
                format_func=lambda x: f"{x[0]} - {x[1]} - {st.session_state.order_books[x[0]].orders[x[1]].side} "
                                    f"{st.session_state.order_books[x[0]].orders[x[1]].quantity} @ "
                                    f"{st.session_state.order_books[x[0]].orders[x[1]].price}"
            )
            cancel_button = st.form_submit_button("Cancel Order")
            
            if cancel_button:
                symbol, order_id = order_to_cancel
                if st.session_state.order_books[symbol].cancel_order(order_id):
                    st.success(f"Order {order_id} cancelled successfully!")
                else:
                    st.error("Failed to cancel order")
        else:
            st.write("No active orders to cancel")
            st.form_submit_button("Cancel Order", disabled=True)

# Display Order Book
st.subheader("Order Books")
selected_symbol = st.selectbox("Select Symbol to View", options=list(st.session_state.order_books.keys()) if st.session_state.order_books else ["No Orders"])

if st.session_state.order_books and selected_symbol in st.session_state.order_books:
    snapshot = st.session_state.order_books[selected_symbol].get_order_book_snapshot()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"Asks (Sell Orders) - {selected_symbol}")
        if snapshot['asks']:
            asks_df = pd.DataFrame(snapshot['asks'], columns=['Price', 'Quantity'])
            asks_df = asks_df.sort_values('Price', ascending=True)
            st.dataframe(asks_df, hide_index=True)
        else:
            st.write("No active sell orders")

    with col2:
        st.write(f"Bids (Buy Orders) - {selected_symbol}")
        if snapshot['bids']:
            bids_df = pd.DataFrame(snapshot['bids'], columns=['Price', 'Quantity'])
            bids_df = bids_df.sort_values('Price', ascending=False)
            st.dataframe(bids_df, hide_index=True)
        else:
            st.write("No active buy orders")

    # Update Market Summary
    st.subheader(f"Market Summary - {selected_symbol}")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Best Bid", f"${snapshot['best_bid']}" if snapshot['best_bid'] else "No Bids")
    with col2:
        st.metric("Best Ask", f"${snapshot['best_ask']}" if snapshot['best_ask'] else "No Asks")

# Display Order History
st.subheader("Order History")
if st.session_state.order_books:
    orders_data = []
    for symbol, order_book in st.session_state.order_books.items():
        for order in order_book.orders.values():
            orders_data.append({
                'Symbol': symbol,
                'Order ID': order.order_id,
                'Side': order.side,
                'Price': float(order.price),
                'Quantity': order.quantity,
                'Filled': order.filled_quantity,
                'Status': order.status
            })
    if orders_data:
        orders_df = pd.DataFrame(orders_data)
        st.dataframe(orders_df, hide_index=True)
    else:
        st.write("No orders yet")
else:
    st.write("No orders yet")

# Display Trade History
st.subheader("Trade History")
if st.session_state.trade_history:
    trades_df = pd.DataFrame(st.session_state.trade_history)
    trades_df = trades_df.sort_values('Timestamp', ascending=False)
    st.dataframe(trades_df, hide_index=True)
else:
    st.write("No trades yet")
