import pandas as pd

def calculate_returns(all_data):
    # Convert columns to numeric types (excluding 'timestamp' and 'symbol')
    numeric_cols = ['close']
    for col in numeric_cols:
        all_data[col] = pd.to_numeric(all_data[col], errors='coerce')

    # Filter data for each symbol and calculate one-minute returns
    symbols = all_data['symbol'].unique()
    returns = pd.DataFrame(index=all_data['timestamp'].unique())

    for symbol in symbols:
        # Filter data for the current symbol
        symbol_data = all_data[all_data['symbol'] == symbol]

        # Calculate one-minute returns and add to the returns DataFrame
        symbol_returns = symbol_data.set_index('timestamp')['close'].pct_change()
        returns[symbol] = symbol_returns
    returns = returns.fillna(0)
    return returns

def sort_correlations(corr_matrix):
    corr_pairs = corr_matrix.unstack().reset_index()

    # Rename columns for clarity
    corr_pairs.columns = ['Asset1', 'Asset2', 'Correlation']

    # Remove self correlation
    corr_pairs = corr_pairs[corr_pairs['Asset1'] != corr_pairs['Asset2']]

    # Sort by absolute correlation values
    corr_pairs['Absolute Correlation'] = corr_pairs['Correlation'].abs()
    sorted_pairs = corr_pairs.sort_values(by='Absolute Correlation', ascending=False)

    # Display the sorted list of correlated pairs in Streamlit
    return sorted_pairs