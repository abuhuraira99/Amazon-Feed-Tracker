import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd

from database import init_db
from processor import process_feed, DOWNLOADS_DIR

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max

# Initialize database on startup
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process the feed and compare with db
            result = process_feed(filepath)
            # Store the uploaded filepath in app context or session if needed
            # For this simple single-user app, we can just save the filename globally
            app.config['LAST_UPLOADED_FILE'] = filepath
            
            return jsonify({
                'success': True,
                'is_initial': result['is_initial'],
                'changes': result['changes'],
                'in_stock_file': result['in_stock_file'],
                'out_of_stock_file': result['out_of_stock_file'],
                'price_changed_file': result['price_changed_file'],
                'new_products_file': result.get('new_products_file', ''),
                'total_rows': result.get('total_rows', 0)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/push', methods=['POST'])
def push_changes():
    filepath = app.config.get('LAST_UPLOADED_FILE')
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'No recently uploaded file found to push.'}), 400
        
    try:
        # Read the newly uploaded file entirely
        new_df = pd.read_csv(filepath, sep='|', dtype={'barcode': str})
        
        # Ensure correct types
        new_df['stock'] = pd.to_numeric(new_df['stock'], errors='coerce').fillna(0).astype(int)
        new_df['price'] = pd.to_numeric(new_df['price'], errors='coerce').fillna(0.0)
        
        # Get old database state
        from database import get_all_products_df, apply_updates
        old_df = get_all_products_df()
        
        if not old_df.empty:
            old_df['barcode'] = old_df['barcode'].astype(str)
            
            # Existing products to update (in old_df AND new_df)
            existing_mask = new_df['barcode'].isin(old_df['barcode'])
            updates_df = new_df[existing_mask]
            
            # New products to insert (NOT in old_df AND stock > 0)
            new_mask = ~new_df['barcode'].isin(old_df['barcode'])
            inserts_df = new_df[new_mask & (new_df['stock'] > 0)]
            
            apply_updates(updates_df, inserts_df)
        else:
            # Initial push: only insert new products that have stock > 0
            inserts_df = new_df[new_df['stock'] > 0]
            apply_updates(pd.DataFrame(), inserts_df)
        
        return jsonify({'success': True, 'message': 'Database updated successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)

@app.route('/search/<barcode>')
def search_barcode(barcode):
    from database import get_product_by_barcode
    product = get_product_by_barcode(barcode)
    if product:
        return jsonify({'success': True, 'product': product})
    else:
        return jsonify({'success': False, 'message': 'Barcode not found in database.'})

@app.route('/export_current_stock', methods=['GET'])
def export_current_stock():
    try:
        from database import get_db_connection
        conn = get_db_connection()
        # Query only products where stock is greater than 0
        df = pd.read_sql_query("SELECT barcode, artist, title, price, stock, format FROM products WHERE stock > 0", conn)
        conn.close()
        
        filename = "CURRENT_IN_STOCK_DATABASE.xlsx"
        filepath = os.path.join(DOWNLOADS_DIR, filename)
        df.to_excel(filepath, index=False)
        
        return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
