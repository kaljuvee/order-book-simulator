import vectorbt as vbt
from datetime import datetime, timedelta
import numpy as np
import re
import numpy as np

def simulate_trades(entries, prices, stop_loss_pct, take_profit_pct):
    try:
        sl_exits = np.full_like(entries, False)
        tp_exits = np.full_like(entries, False)
        
        for i in range(1, len(entries) - 1):  # Adjusted to prevent out-of-bounds in the last iteration
            if entries[i]:
                entry_price = prices[i]
                for j in range(i + 1, len(entries)):
                    if j >= len(prices):  # Check to ensure 'j' does not exceed the length of 'prices'
                        break
                    
                    # Check stop loss condition
                    if not sl_exits[i] and prices[j] <= entry_price * (1 - stop_loss_pct):
                        sl_exits[j] = True
                        break  # Exit the loop on first condition met
                    
                    # Check take profit condition
                    if not tp_exits[i] and prices[j] >= entry_price * (1 + take_profit_pct):
                        tp_exits[j] = True
                        break  # Exit the loop on first condition met

        # Combine exit signals: original exits, stop loss exits, and take profit exits
        combined_exits = np.logical_or(sl_exits, tp_exits)
        return combined_exits

    except Exception as e:
        print(f"An error occurred during trade simulation: {e}")
        # Return None or an appropriate value indicating failure
        return None


# Utility function to convert frequency format from '1m' to '1T'
def convert_frequency(freq):
    match = re.match(r'(\d+)m', freq)
    if match:
        minutes = match.group(1)
        return f'{minutes}T'  # Convert to pandas frequency format
    return freq  # Return the original frequency if no match

def backtest_zscore(asset1, asset2, window, threshold, position_size, stop_loss_pct, take_profit_pct, input_frequency, lookback_days):
    try:
        # Convert the input frequency to the desired format
        frequency = convert_frequency(input_frequency)

        # Set the start and end dates based on lookback_days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        # Fetch historical price data with the specified frequency
        asset1_data = vbt.YFData.download(asset1, start=start_date, end=end_date, interval=input_frequency).get('Close')
        asset2_data = vbt.YFData.download(asset2, start=start_date, end=end_date, interval=input_frequency).get('Close')

        # Align the data based on timestamps
        asset1_data_aligned, asset2_data_aligned = asset1_data.align(asset2_data, join='inner')

        # Calculate the price ratio using aligned data
        price_ratio = asset1_data_aligned / asset2_data_aligned
        mean = price_ratio.rolling(window, min_periods=1).mean()
        std = price_ratio.rolling(window, min_periods=1).std(ddof=0)
        z_scores = (price_ratio - mean) / std.replace(0, np.nan)

        # Entry and exit signals based on Z-Score threshold
        entries = z_scores < -threshold
        exits = z_scores > threshold

        # Simulate trades and calculate combined exit signals
        combined_exits = simulate_trades(entries, asset1_data_aligned, stop_loss_pct, take_profit_pct)
        
        # Combine with original exit signals
        combined_exits = np.logical_or(combined_exits, exits)

        # Perform backtesting with combined exit signals
        portfolio = vbt.Portfolio.from_signals(
            asset1_data_aligned,
            entries=entries,
            exits=combined_exits,
            size=position_size,
            freq=frequency  # Changed from '1T' to 'frequency' to match input frequency
        )

        return portfolio

    except Exception as e:
        print(f"An error occurred during backtesting: {e}")
        # Optionally, return None or a specific error indicator
        return None

# Assuming 'portfolio' is your Portfolio object from the backtest
def benchmark_returns(portfolio, benchmark_ticker='SPY'):
    # Call the returns method to get the returns DataFrame
    portfolio_returns_df = portfolio.returns()

    # Obtain the start and end dates from the portfolio's returns DataFrame index
    start_date = portfolio_returns_df.index[0]
    end_date = portfolio_returns_df.index[-1]

    # Fetch benchmark data for the same date range as your backtest
    benchmark_data = vbt.YFData.download(benchmark_ticker, start=start_date, end=end_date, interval='1d').get('Close')

    # Calculate daily returns for the benchmark
    benchmark_returns = benchmark_data.vbt.pct_change()

    # Calculate cumulative returns
    cumulative_portfolio_returns = portfolio_returns_df.vbt.cumsum()
    cumulative_benchmark_returns = benchmark_returns.vbt.cumsum()

    return cumulative_portfolio_returns, cumulative_benchmark_returns
