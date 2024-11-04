import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def get_prices_yfinance_lookback(selected_symbols, interval='1d', days=30):
    try:
        all_data = pd.DataFrame()
        
        # Ensure 'days' is an integer
        days = int(days)

        # Calculate start date based on the number of days to go back
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format the dates as strings
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        formatted_end_date = end_date.strftime('%Y-%m-%d')
        
        for symbol in selected_symbols:
            # Fetch the data for the given symbol, interval, and date range
            data = yf.download(symbol, interval=interval, start=formatted_start_date, end=formatted_end_date)
            
            # Create a new 'timestamp' column based on the DataFrame's index
            data['timestamp'] = data.index
            
            # Reset the index without keeping the original index column
            data.reset_index(drop=True, inplace=True)
            
            # Drop the 'Close' column
            data.drop(columns=['Close'], inplace=True)
            
            # Rename 'Adj Close' to 'Close'
            data.rename(columns={'Adj Close': 'Close'}, inplace=True)
            
            # Lowercase all column names
            data.columns = data.columns.str.lower()
            
            data['symbol'] = symbol  # Add the symbol column
            all_data = pd.concat([all_data, data], ignore_index=True)  # Concatenate to the all_data DataFrame
        
        return all_data.sort_values(by='timestamp').reset_index(drop=True)  # Sort by 'timestamp' and reset index
    except Exception as e:
        print(f"equity_exchange_util.get_prices_yfinance: error fetching data: {e}")
        return pd.DataFrame()

def get_prices_yfinance_date_range(selected_symbols, start_date, end_date, interval='1d'):
    try:
        all_data = pd.DataFrame()

        # Ensure start_date and end_date are in the correct format
        # No need to reformat if they're already in 'YYYY-MM-DD' as per the function signature requirement

        for symbol in selected_symbols:
            # Fetch the data for the given symbol, interval, and date range
            data = yf.download(symbol, interval=interval, start=start_date, end=end_date)

            # Create a new 'timestamp' column based on the DataFrame's index
            data['timestamp'] = data.index

            # Reset the index without keeping the original index column
            data.reset_index(drop=True, inplace=True)

            # Drop the 'Close' column
            data.drop(columns=['Close'], inplace=True)

            # Rename 'Adj Close' to 'Close'
            data.rename(columns={'Adj Close': 'Close'}, inplace=True)

            # Lowercase all column names
            data.columns = data.columns.str.lower()

            data['symbol'] = symbol  # Add the symbol column
            all_data = pd.concat([all_data, data], ignore_index=True)  # Concatenate to the all_data DataFrame

        return all_data.sort_values(by='timestamp').reset_index(drop=True)  # Sort by 'timestamp' and reset index
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def append_prices(df1, df2):
    try:
        timestamp_column = 'timestamp'
        close_column = 'close'
        symbol_column = 'symbol'

        # Select only the 'timestamp', 'symbol', and 'close' columns, and ensure the timestamp is in datetime format
        df1_selected = df1[[timestamp_column, symbol_column, close_column]].copy()
        df1_selected[timestamp_column] = pd.to_datetime(df1_selected[timestamp_column])

        df2_selected = df2[[timestamp_column, symbol_column, close_column]].copy()
        df2_selected[timestamp_column] = pd.to_datetime(df2_selected[timestamp_column])

        # Round the timestamp to the nearest minute for both selected DataFrames
        df1_selected[timestamp_column] = df1_selected[timestamp_column].dt.round('min')
        df2_selected[timestamp_column] = df2_selected[timestamp_column].dt.round('min')

        # Append the two DataFrames
        appended_df = pd.concat([df1_selected, df2_selected], ignore_index=True)

        return appended_df

    except Exception as e:
        print(f"An error occurred while appending the data: {e}")
        # Optionally, return an empty DataFrame or handle the error as needed
        return pd.DataFrame()
