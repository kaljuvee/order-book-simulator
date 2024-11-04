import pandas as pd
from utils.db_util import db_util

def store_trade_pnl(trades_df, position_entry_symbol, entry_time, 
                    position_entry_price, exit_time, exit_fill_price, 
                    exit_fill_amount, taker_fee, profit_target, stop_loss, exit_reason, strategy, run_id, exchange, live_mode, column_list):
    try:
        # Calculate gross and net PnL
        gross_pnl = (exit_fill_price - position_entry_price) * exit_fill_amount
        net_pnl = gross_pnl - (gross_pnl * taker_fee * 2)

        # Calculate cumulative PnL
        gross_cum_pnl = trades_df['gross_pnl'].sum() + gross_pnl if not trades_df.empty else gross_pnl
        net_cum_pnl = trades_df['net_pnl'].sum() + net_pnl if not trades_df.empty else net_pnl

        print(f"Exited position for {position_entry_symbol}, Gross PnL: {gross_pnl}, Gross Cumulative PnL: {gross_cum_pnl}")

        # Prepare the trade record as a list
        trade_record = [position_entry_symbol, entry_time, position_entry_price, exit_time, exit_fill_price, 
                        exit_fill_amount, profit_target, stop_loss, 
                        gross_pnl, net_pnl, gross_cum_pnl, net_cum_pnl, exit_reason, strategy, run_id, exchange, live_mode]

        # Convert trade record to DataFrame with appropriate column names
        trade_record_df = pd.DataFrame([trade_record], columns = column_list)

        # Append the new trade record to the trades DataFrame
        trades_df.loc[len(trades_df)] = trade_record

        # Append the new trade record to the SQL table
        db_util.write_table_append(trade_record_df, 'crypto_trades')

        print('Wrote new PnL:', trades_df)
        return trades_df
    except Exception as e:
        print(f"An error occurred while storing trade PnL: {e}")
        return None
