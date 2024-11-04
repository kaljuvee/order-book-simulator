def check_exit_signal_old(top_movers, position_entry_symbol, position_entry_price):
    for _, row in top_movers.iterrows():
        if row['symbol'] == position_entry_symbol:
            percent_change_from_entry = (row['close'] - position_entry_price) / position_entry_price * 100
            if percent_change_from_entry > 0.5 or percent_change_from_entry < -0.5 or row['volume_ratio'] < 1:
                return True  # Exit signal
    return False