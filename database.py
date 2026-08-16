import sqlite3
import pandas as pd
import os

DB_PATH = 'inventory.db'

def get_db_connection():
    # 60 second timeout to prevent "database is locked" errors
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.row_factory = sqlite3.Row
    
    # Auto-recreate table if database was deleted while running
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            barcode TEXT PRIMARY KEY,
            artist TEXT,
            title TEXT,
            price REAL,
            stock INTEGER,
            format TEXT
        )
    ''')
    conn.commit()
    return conn

def init_db():
    get_db_connection().close()

def get_all_products_df():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

def apply_updates(updates_df, inserts_df):
    """
    Applies updates to existing rows and inserts new rows sequentially.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Ultra-fast bulk optimizations
    c.execute("PRAGMA synchronous = OFF")
    c.execute("PRAGMA journal_mode = OFF")
    c.execute("PRAGMA cache_size = -1000000") # 1GB cache
    
    # Use robust executemany to completely bypass SQLite's dynamic typing bugs
    if not updates_df.empty:
        update_data = updates_df[['artist', 'title', 'price', 'stock', 'format', 'barcode']].values.tolist()
        c.executemany('''
            UPDATE products 
            SET artist=?, title=?, price=?, stock=?, format=?
            WHERE barcode=?
        ''', update_data)
        
    if not inserts_df.empty:
        insert_data = inserts_df[['barcode', 'artist', 'title', 'price', 'stock', 'format']].values.tolist()
        c.executemany('''
            INSERT OR IGNORE INTO products (barcode, artist, title, price, stock, format)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', insert_data)
        
    conn.commit()
    conn.close()

def get_product_by_barcode(barcode):
    """Fetches a single product from the database by barcode."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE barcode = ?", (str(barcode),))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None
