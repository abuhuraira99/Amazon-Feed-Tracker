import os
import pandas as pd
from database import get_all_products_df

DOWNLOADS_DIR = 'downloads'
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def process_feed(filepath):
    """
    Reads the new feed file and compares it with the database.
    Returns a dictionary of paths to the generated Excel files and a list of changed rows for the UI.
    """
    # 1. Read new feed
    new_df = pd.read_csv(filepath, sep='|', dtype={'barcode': str})
    # Fill NA to prevent issues
    new_df['stock'] = pd.to_numeric(new_df['stock'], errors='coerce').fillna(0).astype(int)
    new_df['price'] = pd.to_numeric(new_df['price'], errors='coerce').fillna(0.0)
    
    # 2. Get old state from DB
    old_df = get_all_products_df()
    
    if old_df.empty:
        # If DB is empty, there are no changes to compare.
        # Just return empty files and an empty list of changes.
        in_stock_path = os.path.join(DOWNLOADS_DIR, 'in_stock.xlsx')
        out_stock_path = os.path.join(DOWNLOADS_DIR, 'out_of_stock.xlsx')
        price_changed_path = os.path.join(DOWNLOADS_DIR, 'price_changed.xlsx')
        
        pd.DataFrame().to_excel(in_stock_path, index=False)
        pd.DataFrame().to_excel(out_stock_path, index=False)
        pd.DataFrame().to_excel(price_changed_path, index=False)
        
        return {
            'in_stock_file': 'in_stock.xlsx',
            'out_of_stock_file': 'out_of_stock.xlsx',
            'price_changed_file': 'price_changed.xlsx',
            'changes': [],
            'is_initial': True,
            'total_rows': len(new_df)
        }

    old_df['barcode'] = old_df['barcode'].astype(str)
    old_df['stock'] = pd.to_numeric(old_df['stock'], errors='coerce').fillna(0).astype(int)
    old_df['price'] = pd.to_numeric(old_df['price'], errors='coerce').fillna(0.0)

    # 3. Merge old and new data on barcode
    # how='right' means we only keep rows that are in the new file.
    # indicator=True adds a '_merge' column with 'both' or 'right_only'
    merged = pd.merge(old_df, new_df, on='barcode', how='right', suffixes=('_old', '_new'), indicator=True)
    
    # Handle NaNs that appear due to right join
    merged['stock_old'] = merged['stock_old'].fillna(0)
    merged['stock_new'] = merged['stock_new'].fillna(0)
    merged['price_old'] = merged['price_old'].fillna(0.0)
    merged['price_new'] = merged['price_new'].fillna(0.0)
    
    # Use new values for reporting and fill NaNs with empty strings to avoid JSON errors
    merged['title'] = merged['title_new'].fillna('')
    merged['artist'] = merged['artist_new'].fillna('')
    merged['format'] = merged['format_new'].fillna('')

    # 4. Find condition: In Stock
    # Was in DB (both), was out of stock (<=0) and now in stock (>0)
    in_stock_mask = (merged['_merge'] == 'both') & (merged['stock_old'] <= 0) & (merged['stock_new'] > 0)
    in_stock_df = merged[in_stock_mask][['barcode', 'artist', 'title', 'price_new', 'stock_new', 'format']]
    in_stock_df = in_stock_df.rename(columns={'price_new': 'price', 'stock_new': 'stock'})

    # 5. Find condition: Out of Stock
    # Was in DB (both), was in stock (>0) and now out of stock (<=0)
    out_stock_mask = (merged['_merge'] == 'both') & (merged['stock_old'] > 0) & (merged['stock_new'] <= 0)
    out_stock_df = merged[out_stock_mask][['barcode', 'artist', 'title', 'price_new', 'stock_new', 'format']]
    out_stock_df = out_stock_df.rename(columns={'price_new': 'price', 'stock_new': 'stock'})

    # 6. Find condition: Price Changed
    # Was in DB (both), prices differ, both prices are valid
    price_changed_mask = (merged['_merge'] == 'both') & (merged['price_old'] != merged['price_new']) & (merged['price_old'] > 0)
    price_changed_df = merged[price_changed_mask][['barcode', 'artist', 'title', 'price_old', 'price_new', 'stock_new', 'format']]
    price_changed_df = price_changed_df.rename(columns={'stock_new': 'stock', 'price_old': 'old_price', 'price_new': 'new_price'})

    # 7. Find condition: New Products
    # NOT in DB (right_only) AND stock > 0
    new_products_mask = (merged['_merge'] == 'right_only') & (merged['stock_new'] > 0)
    new_products_df = merged[new_products_mask][['barcode', 'artist', 'title', 'price_new', 'stock_new', 'format']]
    new_products_df = new_products_df.rename(columns={'price_new': 'price', 'stock_new': 'stock'})

    # 8. Write Excel files
    in_stock_path = os.path.join(DOWNLOADS_DIR, 'in_stock.xlsx')
    out_stock_path = os.path.join(DOWNLOADS_DIR, 'out_of_stock.xlsx')
    price_changed_path = os.path.join(DOWNLOADS_DIR, 'price_changed.xlsx')
    new_products_path = os.path.join(DOWNLOADS_DIR, 'new_products.xlsx')

    in_stock_df.to_excel(in_stock_path, index=False)
    out_stock_df.to_excel(out_stock_path, index=False)
    price_changed_df.to_excel(price_changed_path, index=False)
    new_products_df.to_excel(new_products_path, index=False)

    # 9. Prepare changes for the UI
    changes = []
    
    # Format changes for UI Table
    for _, row in in_stock_df.iterrows():
        changes.append({
            'barcode': row['barcode'],
            'title': str(row['title'])[:50] + '...' if len(str(row['title'])) > 50 else row['title'],
            'change_type': 'In Stock',
            'details': f"Stock became {row['stock']}"
        })
        
    for _, row in out_stock_df.iterrows():
        changes.append({
            'barcode': row['barcode'],
            'title': str(row['title'])[:50] + '...' if len(str(row['title'])) > 50 else row['title'],
            'change_type': 'Out of Stock',
            'details': f"Stock dropped to 0"
        })
        
    for _, row in price_changed_df.iterrows():
        changes.append({
            'barcode': row['barcode'],
            'title': str(row['title'])[:50] + '...' if len(str(row['title'])) > 50 else row['title'],
            'change_type': 'Price Changed',
            'details': f"Price changed from {row['old_price']} to {row['new_price']}"
        })
        
    for _, row in new_products_df.iterrows():
        changes.append({
            'barcode': row['barcode'],
            'title': str(row['title'])[:50] + '...' if len(str(row['title'])) > 50 else row['title'],
            'change_type': 'New Product',
            'details': f"New item added with stock {row['stock']}"
        })

    return {
        'in_stock_file': 'in_stock.xlsx',
        'out_of_stock_file': 'out_of_stock.xlsx',
        'price_changed_file': 'price_changed.xlsx',
        'new_products_file': 'new_products.xlsx',
        'changes': changes,
        'is_initial': False,
        'total_rows': len(new_df)
    }

