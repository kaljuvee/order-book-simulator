import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.exchange_factory import exchanges, exchange_base_currencies
from utils.exchange_util import fetch_order_book_data_by_symbol

st.title("Order Book Viewer")

# Exchange selection
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

# Add retrieve button
if st.button("Retrieve Order Book"):
    try:
        # Fetch order book data
        exchange = exchanges[selected_exchange]
        order_book = exchange.fetch_order_book(trading_pair, limit=20)
        
        # Create DataFrames for bids and asks - now handling all columns
        bids_df = pd.DataFrame(order_book['bids'])
        asks_df = pd.DataFrame(order_book['asks'])
        
        # Rename columns appropriately
        column_names = ['Price', 'Volume', 'Timestamp'] if bids_df.shape[1] == 3 else ['Price', 'Volume']
        bids_df.columns = column_names
        asks_df.columns = column_names
        
        # Display order book tables
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Bids")
            st.dataframe(bids_df[['Price', 'Volume']])  # Only show price and volume
        
        with col2:
            st.subheader("Asks")
            st.dataframe(asks_df[['Price', 'Volume']])  # Only show price and volume
        
        # Create visualization
        fig = go.Figure()
        
        # Add bids bars (green)
        fig.add_trace(go.Bar(
            x=bids_df['Price'],
            y=bids_df['Volume'],
            name='Bids',
            marker_color='rgba(0, 255, 0, 0.5)'
        ))
        
        # Add asks bars (red)
        fig.add_trace(go.Bar(
            x=asks_df['Price'],
            y=asks_df['Volume'],
            name='Asks',
            marker_color='rgba(255, 0, 0, 0.5)'
        ))
        
        # Update layout
        fig.update_layout(
            title=f"Order Book for {trading_pair} on {selected_exchange.capitalize()}",
            xaxis_title="Price",
            yaxis_title="Volume",
            barmode='overlay',
            height=600
        )
        
        # Display the plot
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error fetching order book: {str(e)}")
