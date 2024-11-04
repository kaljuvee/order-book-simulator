import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import ccxt
from plotly.subplots import make_subplots
import numpy as np
import plotly.express as px
import statsmodels.api as sm

def plot_benchmark_returns(cumulative_portfolio_returns, cumulative_benchmark_returns, benchmark_ticker='SPY'):
    # Normalize the returns to start at 1 (100%) for better comparison
    normalized_portfolio_returns = (1 + cumulative_portfolio_returns).fillna(0)
    normalized_benchmark_returns = (1 + cumulative_benchmark_returns).fillna(0)

    # Create traces
    portfolio_trace = go.Scatter(x=normalized_portfolio_returns.index, y=normalized_portfolio_returns, mode='lines', name='Portfolio')
    benchmark_trace = go.Scatter(x=normalized_benchmark_returns.index, y=normalized_benchmark_returns, mode='lines', name=f'{benchmark_ticker} Benchmark')

    # Layout
    layout = go.Layout(title='Portfolio vs. Benchmark Equity Line',
                       xaxis=dict(title='Date'),
                       yaxis=dict(title='Cumulative Returns'))

    # Create figure and add traces
    fig = go.Figure(data=[portfolio_trace, benchmark_trace], layout=layout)

    # Show plot
    return fig

def plot_corr_matrix(correlation_matrix):
    # Create a heatmap using Plotly
    fig = px.imshow(correlation_matrix, 
                    text_auto=True,
                    aspect="auto", 
                    color_continuous_scale='RdYlGn',  # Red-Yellow-Green color scale
                    zmin=-1,  # Minimum value of the color scale
                    zmax=1,   # Maximum value of the color scale
                    labels=dict(x="Asset", y="Asset", color="Correlation"))

    fig.update_layout(title='Correlation Matrix Heatmap', xaxis_nticks=36, yaxis_nticks=36)

    # Display the plot in Streamlit
    st.plotly_chart(fig)

def plot_equity_line(signals):
    # Create a plotly figure
    fig = go.Figure()

    # Add a line trace for cumulative PnL
    fig.add_trace(
        go.Scatter(x=signals['Timestamp'], y=signals['Cumulative PnL'], mode='lines', name='Cumulative PnL')
    )

    # Update layout
    fig.update_layout(
        height=600,
        width=800,
        title_text="Cumulative PnL Over Time",
        xaxis_title="Time",
        yaxis_title="Cumulative PnL",
        showlegend=False
    )

    st.plotly_chart(fig)

def plot_zscore(all_data, asset1, asset2):
    # Filter data for each asset
    data_asset1 = all_data[all_data['symbol'] == asset1]
    data_asset2 = all_data[all_data['symbol'] == asset2]

    # Ensure matching timestamps
    merged_data = pd.merge(data_asset1, data_asset2, on='timestamp', suffixes=('_asset1', '_asset2'))

    # Calculate the ratio of the two assets' prices
    ratios = merged_data['close_asset1'] / merged_data['close_asset2']

    # Calculate z-score
    z_scores = zscore(ratios)

    # Create a plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=merged_data['timestamp'], y=z_scores, mode='lines', name='Z-Score'))
    fig.update_layout(title=f'Z-Score Over Time for {asset1} vs {asset2}', xaxis_title='Timestamp', yaxis_title='Z-Score')

    # Display the plot in Streamlit
    st.plotly_chart(fig)

def plot_all_zscores(all_data, sorted_pairs, page, pairs_per_page=5, subplot_height=300):
    # Start and end indices for the current page
    start_index = page * pairs_per_page
    end_index = start_index + pairs_per_page
    pairs_subset = sorted_pairs.iloc[start_index:end_index]

    # Create subplots for the current page
    fig = make_subplots(rows=len(pairs_subset), cols=1, shared_xaxes=True, vertical_spacing=0.05)

    for i, (_, row) in enumerate(pairs_subset.iterrows()):
        asset1 = row['Asset1']
        asset2 = row['Asset2']

        # Filter data for each asset
        data_asset1 = all_data[all_data['symbol'] == asset1]
        data_asset2 = all_data[all_data['symbol'] == asset2]

        # Ensure matching timestamps
        merged_data = pd.merge(data_asset1, data_asset2, on='timestamp', suffixes=('_asset1', '_asset2'))

        # Calculate the ratio of the two assets' prices and z-score
        ratios = merged_data['close_asset1'] / merged_data['close_asset2']
        z_scores = zscore(ratios)
        
        subplot_title = f'{asset1} vs {asset2}'
        fig.update_yaxes(title=subplot_title, row=i+1, col=1)
        # Add trace to the subplot
        fig.add_trace(go.Scatter(x=merged_data['timestamp'], y=z_scores, mode='lines', name=f'{asset1} vs {asset2}'), row=i+1, col=1)

    # Update layout
    fig.update_layout(height=subplot_height*len(pairs_subset), width=800, title_text="Z-Scores for Asset Pairs")

    # Display the plot in Streamlit
    st.plotly_chart(fig)

def plot_prices(all_data, symbols, benchmark):
    try:
        # Remove duplicates from the symbols list and ensure the benchmark symbol is included only once
        symbols = list(set(symbols))  # Convert symbols list to a set to remove duplicates, then back to a list
        if symbols.count(benchmark) > 1:  # If the benchmark symbol appears more than once
            symbols.remove(benchmark)  # Remove the extra occurrences

        # Check if 'all_data' contains the benchmark symbol
        if not all_data[all_data['symbol'] == benchmark].empty:
            # Normalize each symbol's prices to start at 100 using the benchmark's first price
            normalized_data = all_data.pivot(index='timestamp', columns='symbol', values='close')
            normalized_data = normalized_data.div(normalized_data.iloc[0]) * 100

            # Plotting
            fig = go.Figure()
            for symbol in symbols:
                if symbol in normalized_data.columns:
                    fig.add_trace(go.Scatter(x=normalized_data.index, y=normalized_data[symbol], mode='lines', name=symbol))

            fig.update_layout(title=f'Normalized Prices Relative to {benchmark}', xaxis_title='Timestamp', yaxis_title='Normalized Price')

            # Display the plot in Streamlit
            st.plotly_chart(fig)
        else:
            # Handle the case where the benchmark symbol is not found in 'all_data'
            st.error(f"Benchmark symbol '{benchmark}' not found in the data.")
    except Exception as e:
        st.error(f"An error occurred while plotting prices: {e}")


def plot_cointegration_heatmap(returns):
    try:
        # Fill NaN values with 0s
        returns_filled = returns.fillna(0)

        assets = returns_filled.columns
        p_values_matrix = pd.DataFrame(index=assets, columns=assets, data=np.nan)
        
        # Perform pairwise cointegration tests and store p-values
        for asset1 in assets:
            for asset2 in assets:
                if asset1 != asset2:
                    try:
                        coint_test = sm.tsa.stattools.coint(returns_filled[asset1], returns_filled[asset2])
                        p_values_matrix.loc[asset1, asset2] = coint_test[1]  # p-value is at index 1
                    except Exception as e:
                        print(f"Error performing cointegration test between {asset1} and {asset2}: {e}")
                        p_values_matrix.loc[asset1, asset2] = np.nan

        # Create a heatmap using Plotly
        fig = px.imshow(p_values_matrix, 
                        text_auto=True,
                        aspect="auto", 
                        color_continuous_scale='RdYlGn_r',  # Red-Yellow-Green color scale (reversed)
                        labels=dict(x="Asset", y="Asset", color="P-Value"))

        fig.update_layout(title='Cointegration Test P-Values Heatmap', xaxis_nticks=36, yaxis_nticks=36)

        # Flatten the p-values matrix and reset index
        coint_pairs = p_values_matrix.unstack().reset_index()
        coint_pairs.columns = ['Asset1', 'Asset2', 'P-Value']

        # Remove NaNs and sort by p-values
        coint_pairs = coint_pairs.dropna().sort_values(by='P-Value')

        return fig, coint_pairs

    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame()

# Example Usage (assuming 'returns' is a DataFrame of asset returns)
# sorted_pairs = plot_cointegration_heatmap(returns)

def plot_returns(all_data):
    # Convert columns to numeric types (excluding 'timestamp' and 'symbol')
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
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

    # Create subplots
    fig = make_subplots(rows=len(symbols), cols=1, shared_xaxes=True, vertical_spacing=0.02)

    for i, symbol in enumerate(symbols, start=1):
        # Add a trace for each symbol
        fig.add_trace(
            go.Scatter(x=returns.index, y=returns[symbol], mode='lines', name=symbol),
            row=i, col=1
        )
        # Add title for each subplot
        subplot_title = f'Returns for {symbol}'
        fig.update_yaxes(title=subplot_title, row=i, col=1)

    # Update layout
    fig.update_layout(height=300*len(symbols), width=800, title_text="One-Minute Returns Over Time")

    # Display the plot in Streamlit
    st.plotly_chart(fig)
    return returns

def plot_correlations(returns):
    # Compute the correlation matrix
    correlation_matrix = returns.corr()

    # Create a heatmap using Plotly
    fig = px.imshow(correlation_matrix, 
                    text_auto=True,
                    aspect="auto", 
                    color_continuous_scale='RdYlGn',  # Red-Yellow-Green color scale
                    zmin=-1,  # Minimum value of the color scale
                    zmax=1,   # Maximum value of the color scale
                    labels=dict(x="Asset", y="Asset", color="Correlation"))

    fig.update_layout(title='Correlation Matrix Heatmap', xaxis_nticks=36, yaxis_nticks=36)

    # Display the plot in Streamlit
    st.plotly_chart(fig)

    # Flatten the correlation matrix and reset index
    corr_pairs = correlation_matrix.unstack().reset_index()

    # Rename columns for clarity
    corr_pairs.columns = ['Asset1', 'Asset2', 'Correlation']

    # Remove self correlation
    corr_pairs = corr_pairs[corr_pairs['Asset1'] != corr_pairs['Asset2']]

    # Sort by absolute correlation values
    corr_pairs['Absolute Correlation'] = corr_pairs['Correlation'].abs()
    sorted_pairs = corr_pairs.sort_values(by='Absolute Correlation', ascending=False)

    # Display the sorted list of correlated pairs in Streamlit
    st.dataframe(sorted_pairs[['Asset1', 'Asset2', 'Correlation']])
    return sorted_pairs

# Calculate z-score
def zscore(series):
    return (series - series.mean()) / np.std(series)
