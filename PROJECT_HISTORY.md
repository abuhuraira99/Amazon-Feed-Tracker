# Amazon Vendor Inventory Feed Tracker - Project History & Architecture

## 1. Project Overview
This project is a high-performance, locally-hosted inventory management web application designed for processing massive Amazon vendor feed files (up to 1.6 million rows per file). Its primary purpose is to compare a newly uploaded feed file against an existing local database to determine which items are newly in stock, out of stock, had price changes, or are entirely new products. It then allows the user to securely push those updates into the database and download structured Excel reports.

## 2. Technology Stack
- **Backend**: Python, Flask, Pandas
- **Database**: SQLite (Highly optimized for speed and portability)
- **Frontend**: HTML5, Vanilla JavaScript, CSS3 (Glassmorphic, premium UI design)

## 3. Core Architecture & Business Logic
Based on strict customer requirements, the application handles data in a very specific, non-destructive way:
- **Barcode as Primary Key**: The `barcode` column is strictly enforced as the unique identifier for all items.
- **Updates (Existing Products)**: If a barcode already exists in the database, its data (price, stock, etc.) is updated in-place without changing its physical row order.
- **Insertions (New Products)**: If a barcode is completely new to the feed, it is appended to the bottom of the database, **but only if its stock is strictly greater than 0**.
- **Exclusions (Missing Products)**: If a product exists in the database but is missing from the newly uploaded feed file, it is **completely ignored and left completely untouched**. We do not delete missing items.

## 4. Database Optimization & Safeguards (CRITICAL)
Handling 1.6 million rows via Python into SQLite normally takes minutes, but the engine has been hyper-optimized to process in under 10 seconds:
- **Pragmas**: `PRAGMA synchronous = OFF`, `PRAGMA journal_mode = OFF`, and a massive memory cache are executed before bulk inserts to force SQLite to use RAM for B-Tree index updates.
- **Execution Engine**: We strictly use Python's raw `c.executemany` loop instead of Pandas' `to_sql` or SQLite's `UPDATE ... FROM` subqueries.
- **Why Executemany?**: SQLite has a quirk called "Dynamic Typing / Type Affinity". If you insert barcodes that look like numbers into a temp table, SQLite might silently convert them to Integers, which breaks subquery comparisons against the main `TEXT` table (0 rows updated silently). Using Python's `executemany` ensures all data types stay strictly as strings/text throughout the entire pipeline.
- **Self-Healing**: If the `inventory.db` file is ever manually deleted by the user while the server is running, the `get_db_connection()` function in `database.py` is configured to automatically recreate the table schema on the fly to prevent crashes.

## 5. UI/UX Features
- **Pagination**: The changes table handles infinite rows flawlessly by using client-side Javascript pagination (50 rows per page), preventing browser memory crashes.
- **Data Sanitization**: Blank/missing fields in the vendor feed (like blank Titles or Artists) are intercepted by Pandas and explicitly converted to empty strings (`""`). This prevents `NaN` errors from crashing the browser's JSON parser.
- **Real-time Search**: A search bar allows instantaneous lookups of any barcode in the database.
- **Global Export**: A "Download Current Database" button is permanently available in the UI, which executes a simple `SELECT * FROM products WHERE stock > 0` and delivers it as an Excel snapshot.
- **Report Downloads**: The application utilizes Pandas to generate beautifully formatted `.xlsx` files for `In Stock`, `Out of Stock`, `Price Changed`, and `New Products`.

## 6. Deployment Notes
- The database is stored entirely within `inventory.db`. Because SQLite is portable, migrating the project state to another machine only requires transferring this single file alongside the code.
- Dependencies are minimal (`flask`, `pandas`, `openpyxl`, `werkzeug`).
- Execution is handled via `setup.bat`/`run.bat` (Windows) or `setup.sh`/`run.sh` (Linux), which handle the automatic generation of virtual environments.
