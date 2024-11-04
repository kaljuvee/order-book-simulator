import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
import traceback
from dotenv import load_dotenv
import os
# Load the environment variables from the .env file
load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PWD = os.getenv('DB_PWD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

db_params = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PWD,
    'host': DB_HOST,
    'port': DB_PORT,  # default is 5432 for PostgreSQL
}

def get_news_prediction():
    # Define the SQL query
    sql_query = '''
    SELECT distinct ticker, title, link, topic, published_est, market,
       begin_price, end_price, index_begin_price, index_end_price,
       daily_return, index_return, daily_alpha, actual_action, predicted_action, confidence
    FROM news_price
    ORDER BY published_est DESC
    '''

    try:
        # Fetch data into a pandas DataFrame using the engine
        news_df = pd.read_sql_query(sql_query, engine)

        if news_df.empty:
            logger.warning("The query returned no results.")
            return pd.DataFrame()  # Return an empty DataFrame for consistency
        else:
            return news_df
    except Exception as e:
        logger.error(f"An error occurred while executing the query: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of an error

# Create a connection to the PostgreSQL database
engine = create_engine(f"postgresql+psycopg2://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}")

def write_bid_ask(df):
    try:
        if not df.empty:
            with engine.connect() as conn:
                df.to_sql('ccxt_bid_ask', conn, if_exists='append', index=False)
    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc())

def write_table_replace(df, table):
    try:
        if not df.empty:
            with engine.connect() as conn:
                df.to_sql(table, conn, if_exists='replace', index=False)
    except Exception as e:
        print(f"Write table: an error occurred: {e}")
        print(traceback.format_exc())

def write_table_append(df, table):
    try:
        if not df.empty:
            with engine.connect() as conn:
                df.to_sql(table, conn, if_exists='append', index=False)
    except Exception as e:
        print(f"Write table: an error occurred: {e}")
        print(traceback.format_exc())

def write_pnl(df):
    try:
        if not df.empty:
            with engine.connect() as conn:
                df.to_sql('pnl', conn, if_exists='append', index=False)
    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc())

def store(df, table):
    try:
        if not df.empty:
            with engine.connect() as conn:
                df.to_sql(table, conn, if_exists='append', index=False)
    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc())

def get_prices(exchange):
    sql_query = text('''
    SELECT symbol, timestamp, bid, ask, (bid + ask)/2 as close, exchange from ccxt_bid_ask
    WHERE exchange = :exchange
    ''')
    with engine.connect() as conn:
        prices_df = pd.read_sql_query(sql_query, conn, params={'exchange': exchange})
    return prices_df

def get_crypto_trades():
    sql_query = text('''
    select * from crypto_trades order by run_id desc
    ''')
    with engine.connect() as conn:
        df = pd.read_sql_query(sql_query, conn)
    return df

def get_news():
    sql_query = text('''
    SELECT distinct ticker, title, link, topic, published_est, market FROM news_item 
    ORDER BY published_est DESC
    LIMIT 1000
    ''')
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(sql_query, conn)
        return df
    except Exception as e:
        print(f"An error occurred while fetching news: {e}")
        # Return an empty DataFrame in case of error
        return pd.DataFrame()
    
def get_bid_ask(exchange, symbols):
    # Generate a list of parameter placeholders (e.g., ':symbol1', ':symbol2', ...)
    symbol_placeholders = [f':symbol{i}' for i in range(len(symbols))]

    # Create the SQL query using `text()` and include placeholders
    sql_query = text(f'''
    SELECT symbol, timestamp, bid, ask, (bid + ask)/2 as close, exchange from ccxt_bid_ask
    WHERE exchange = :exchange AND symbol IN ({', '.join(symbol_placeholders)})
    ORDER BY timestamp ASC
    ''')

    # Create a dictionary that maps placeholders to actual symbol values
    params = {f'symbol{i}': symbol for i, symbol in enumerate(symbols)}
    params['exchange'] = exchange  # Add exchange to the parameters

    with engine.connect() as conn:
        # Pass the query and the parameters dictionary to `pd.read_sql_query`
        prices_df = pd.read_sql_query(sql_query, conn, params=params)
    return prices_df

def get_symbols(exchange):
    sql_query = '''
    SELECT DISTINCT symbol FROM ccxt_bid_ask
    WHERE exchange = %s
    '''
    symbols_df = pd.read_sql_query(sql_query, engine, params=(exchange,))
    symbols_list = symbols_df['symbol'].tolist()
    return symbols_list
