import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pv_training.db')

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            name TEXT NOT NULL,
            image_filename TEXT,
            image_filename_2 TEXT,
            image_filename_3 TEXT,
            description TEXT DEFAULT '',
            item_barcode TEXT,
            tracking_id TEXT,
            myntra_sku TEXT,
            style_id TEXT,
            article_no TEXT,
            size TEXT,
            mrp REAL,
            color TEXT,
            category TEXT,
            return_type TEXT DEFAULT 'NORMAL',
            return_mode TEXT DEFAULT 'OPEN_BOX_PICKUP',
            eligible_brand_tag INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            warehouse TEXT DEFAULT '',
            carton_code TEXT DEFAULT '',
            login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            logout_time DATETIME,
            total_products_done INTEGER DEFAULT 0,
            total_time_seconds REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS pv_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            started_at DATETIME,
            completed_at DATETIME,
            time_seconds REAL DEFAULT 0,
            gtin_result TEXT,
            issue_selected TEXT,
            qc_result TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS product_expected_answers (
            product_id INTEGER PRIMARY KEY,
            expected_qc_result TEXT NOT NULL,
            expected_issue TEXT NOT NULL DEFAULT 'no-issues',
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    ''')
    conn.commit()

    # Migration: add tracking_id column if it doesn't exist
    try:
        cursor.execute("SELECT tracking_id FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE products ADD COLUMN tracking_id TEXT")
        conn.commit()

    # Migration: add warehouse column if it doesn't exist (for existing DBs)
    try:
        cursor.execute("SELECT warehouse FROM sessions LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE sessions ADD COLUMN warehouse TEXT DEFAULT ''")
        conn.commit()

    # Migration: add carton_code column if it doesn't exist
    try:
        cursor.execute("SELECT carton_code FROM sessions LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE sessions ADD COLUMN carton_code TEXT DEFAULT ''")
        conn.commit()

    # Migration: add image_filename_2 column if it doesn't exist
    try:
        cursor.execute("SELECT image_filename_2 FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE products ADD COLUMN image_filename_2 TEXT")
        conn.commit()

    # Migration: add image_filename_3 column if it doesn't exist
    try:
        cursor.execute("SELECT image_filename_3 FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE products ADD COLUMN image_filename_3 TEXT")
        conn.commit()

    # Migration: add description column if it doesn't exist
    try:
        cursor.execute("SELECT description FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE products ADD COLUMN description TEXT DEFAULT ''")
        conn.commit()

    conn.close()

# ===== USER FUNCTIONS =====

def create_user(email, password, name, is_admin=0):
    """Create a new user. Returns user id or None if email exists."""
    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO users (email, password_hash, name, is_admin) VALUES (?, ?, ?, ?)',
            (email, generate_password_hash(password), name, is_admin)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def create_users_bulk(users_list):
    """Create multiple users from a list of dicts. Returns (success_count, errors)."""
    success = 0
    errors = []
    for u in users_list:
        email = u.get('email', '').strip()
        password = u.get('password', '').strip()
        name = u.get('name', '').strip()
        if not email or not password:
            errors.append(f"Missing email/password for: {email or 'unknown'}")
            continue
        if not name:
            name = email.split('@')[0]
        result = create_user(email, password, name)
        if result:
            success += 1
        else:
            errors.append(f"Duplicate email: {email}")
    return success, errors

def verify_login(email, password):
    """Verify login credentials. Returns user dict or None."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def get_all_users():
    """Get all users (without password hash)."""
    conn = get_db()
    users = conn.execute('SELECT id, email, name, is_admin, created_at FROM users').fetchall()
    conn.close()
    return [dict(u) for u in users]

# ===== PRODUCT FUNCTIONS =====

def get_product(product_id):
    """Get a single product by ID."""
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    return dict(product) if product else None

def get_product_by_tracking_id(tracking_id):
    """Get a single product by its Tracking ID."""
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE tracking_id = ?', (tracking_id,)).fetchone()
    conn.close()
    return dict(product) if product else None

def get_all_products():
    """Get all products."""
    conn = get_db()
    products = conn.execute('SELECT * FROM products ORDER BY id').fetchall()
    conn.close()
    return [dict(p) for p in products]

def delete_product_by_tracking_id(tracking_id):
    """Delete a product and its related records by Tracking ID."""
    conn = get_db()
    product = conn.execute('SELECT id FROM products WHERE tracking_id = ?', (tracking_id,)).fetchone()
    if not product:
        conn.close()
        return False
    
    product_id = product['id']
    # Delete related records
    conn.execute('DELETE FROM pv_logs WHERE product_id = ?', (product_id,))
    conn.execute('DELETE FROM product_expected_answers WHERE product_id = ?', (product_id,))
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return True

def get_product_count():
    """Get total number of products."""
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) as cnt FROM products').fetchone()['cnt']
    conn.close()
    return count

def get_next_product_for_user(user_id, session_id):
    """Get a product the user hasn't processed in this session yet."""
    conn = get_db()
    product = conn.execute('''
        SELECT p.* FROM products p
        WHERE p.id NOT IN (
            SELECT product_id FROM pv_logs WHERE session_id = ? AND completed_at IS NOT NULL
        )
        ORDER BY p.id
        LIMIT 1
    ''', (session_id,)).fetchone()
    conn.close()
    return dict(product) if product else None

# ===== SESSION FUNCTIONS =====

def create_session(user_id, warehouse='', carton_code=''):
    """Create a new login session. Returns session id."""
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO sessions (user_id, warehouse, carton_code) VALUES (?, ?, ?)',
        (user_id, warehouse, carton_code)
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id

def end_session(session_id):
    """End a session — record logout time and totals."""
    conn = get_db()
    # Calculate totals
    stats = conn.execute('''
        SELECT COUNT(*) as total_done,
               COALESCE(SUM(time_seconds), 0) as total_time
        FROM pv_logs WHERE session_id = ? AND completed_at IS NOT NULL
    ''', (session_id,)).fetchone()

    conn.execute('''
        UPDATE sessions SET logout_time = CURRENT_TIMESTAMP,
        total_products_done = ?, total_time_seconds = ?
        WHERE id = ?
    ''', (stats['total_done'], stats['total_time'], session_id))
    conn.commit()
    conn.close()

# ===== PV LOG FUNCTIONS =====

def start_pv(session_id, user_id, product_id):
    """Record start of PV for a product. Returns log id."""
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO pv_logs (session_id, user_id, product_id, started_at) VALUES (?, ?, ?, ?)',
        (session_id, user_id, product_id, datetime.now().isoformat())
    )
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    return log_id

def complete_pv(log_id, gtin_result, issue_selected, qc_result):
    """Record completion of PV for a product."""
    conn = get_db()
    now = datetime.now().isoformat()
    # Get start time to calculate duration
    log = conn.execute('SELECT started_at FROM pv_logs WHERE id = ?', (log_id,)).fetchone()
    if log:
        started = datetime.fromisoformat(log['started_at'])
        elapsed = (datetime.now() - started).total_seconds()
    else:
        elapsed = 0

    conn.execute('''
        UPDATE pv_logs SET completed_at = ?, time_seconds = ?,
        gtin_result = ?, issue_selected = ?, qc_result = ?
        WHERE id = ?
    ''', (now, round(elapsed, 1), gtin_result, issue_selected, qc_result, log_id))
    conn.commit()
    conn.close()
    return elapsed

# ===== STATS / DASHBOARD FUNCTIONS =====

def get_user_stats(user_id):
    """Get performance stats for a specific user."""
    conn = get_db()
    stats = conn.execute('''
        SELECT
            COUNT(*) as total_products,
            COALESCE(ROUND(AVG(time_seconds), 1), 0) as avg_time,
            COALESCE(ROUND(MIN(time_seconds), 1), 0) as fastest_time,
            COALESCE(ROUND(MAX(time_seconds), 1), 0) as slowest_time,
            COALESCE(ROUND(SUM(time_seconds), 1), 0) as total_time,
            SUM(CASE WHEN qc_result = 'pass' THEN 1 ELSE 0 END) as pass_count,
            SUM(CASE WHEN qc_result = 'fail' THEN 1 ELSE 0 END) as fail_count
        FROM pv_logs
        WHERE user_id = ? AND completed_at IS NOT NULL
    ''', (user_id,)).fetchone()
    conn.close()
    return dict(stats) if stats else {}

def get_overall_stats():
    """Get performance stats across all users."""
    conn = get_db()
    stats = conn.execute('''
        SELECT
            COUNT(*) as total_products,
            COALESCE(ROUND(AVG(time_seconds), 1), 0) as avg_time,
            COALESCE(ROUND(MIN(time_seconds), 1), 0) as fastest_time,
            COALESCE(ROUND(MAX(time_seconds), 1), 0) as slowest_time,
            COALESCE(ROUND(SUM(time_seconds), 1), 0) as total_time,
            SUM(CASE WHEN qc_result = 'pass' THEN 1 ELSE 0 END) as pass_count,
            SUM(CASE WHEN qc_result = 'fail' THEN 1 ELSE 0 END) as fail_count
        FROM pv_logs
        WHERE completed_at IS NOT NULL
    ''').fetchone()
    conn.close()
    return dict(stats) if stats else {}

def get_all_users_stats():
    """Get performance stats for all users (dashboard) with PV accuracy."""
    conn = get_db()
    stats = conn.execute('''
        SELECT
            u.id, u.name, u.email,
            COUNT(pv.id) as total_products,
            MIN(pv.started_at) as carton_scan_start,
            MAX(pv.completed_at) as carton_scan_end,
            COALESCE(ROUND(SUM(pv.time_seconds), 1), 0) as total_scan_duration,
            COALESCE(SUM(
                CASE WHEN ea.expected_qc_result IS NOT NULL
                     AND pv.qc_result = ea.expected_qc_result
                     AND pv.issue_selected = ea.expected_issue
                THEN 1 ELSE 0 END
            ), 0) as correct_count,
            (
                SELECT s.warehouse FROM sessions s
                WHERE s.user_id = u.id
                ORDER BY s.login_time DESC LIMIT 1
            ) as warehouse
        FROM users u
        LEFT JOIN pv_logs pv ON u.id = pv.user_id AND pv.completed_at IS NOT NULL
        LEFT JOIN product_expected_answers ea ON pv.product_id = ea.product_id
        GROUP BY u.id
        ORDER BY total_scan_duration ASC
    ''').fetchall()
    conn.close()
    results = []
    for s in stats:
        d = dict(s)
        total = d['total_products']
        correct = d['correct_count']
        d['pv_accuracy'] = round((correct / total) * 100, 1) if total > 0 else 0
        results.append(d)
    return results

def get_user_pv_history(user_id):
    """Get detailed PV history for a user."""
    conn = get_db()
    logs = conn.execute('''
        SELECT pv.*, p.brand, p.name as product_name, p.category
        FROM pv_logs pv
        JOIN products p ON pv.product_id = p.id
        WHERE pv.user_id = ? AND pv.completed_at IS NOT NULL
        ORDER BY pv.completed_at DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return [dict(l) for l in logs]

def get_overall_pv_history():
    """Get detailed PV history across all users."""
    conn = get_db()
    logs = conn.execute('''
        SELECT pv.*, p.brand, p.name as product_name, p.category, u.name as user_name
        FROM pv_logs pv
        JOIN products p ON pv.product_id = p.id
        JOIN users u ON pv.user_id = u.id
        WHERE pv.completed_at IS NOT NULL
        ORDER BY pv.completed_at DESC
        LIMIT 100
    ''').fetchall()
    conn.close()
    return [dict(l) for l in logs]

# ===== EXPORT DATA FUNCTION =====

def get_export_data(date_from=None, date_to=None, name=None, carton_code=None, warehouse=None):
    """Get filtered PV log data for export. No limit on rows."""
    conn = get_db()
    query = '''
        SELECT
            pv.id,
            u.name,
            u.email,
            s.warehouse,
            s.carton_code,
            p.brand,
            p.name as product_name,
            p.category,
            p.item_barcode,
            p.tracking_id,
            p.myntra_sku,
            p.size,
            p.mrp,
            p.color,
            pv.started_at,
            pv.completed_at,
            pv.time_seconds,
            pv.gtin_result,
            pv.issue_selected,
            pv.qc_result,
            ea.expected_qc_result,
            ea.expected_issue,
            CASE
                WHEN ea.expected_qc_result IS NOT NULL
                     AND pv.qc_result = ea.expected_qc_result
                     AND pv.issue_selected = ea.expected_issue
                THEN 'Correct'
                ELSE 'Incorrect'
            END as accuracy_result
        FROM pv_logs pv
        JOIN users u ON pv.user_id = u.id
        JOIN sessions s ON pv.session_id = s.id
        JOIN products p ON pv.product_id = p.id
        LEFT JOIN product_expected_answers ea ON pv.product_id = ea.product_id
        WHERE pv.completed_at IS NOT NULL
    '''
    params = []

    if date_from:
        query += " AND DATE(pv.started_at) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND DATE(pv.started_at) <= ?"
        params.append(date_to)
    if name:
        query += " AND u.name LIKE ?"
        params.append(f'%{name}%')
    if carton_code:
        query += " AND s.carton_code LIKE ?"
        params.append(f'%{carton_code}%')
    if warehouse:
        query += " AND s.warehouse LIKE ?"
        params.append(f'%{warehouse}%')

    query += " ORDER BY pv.completed_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ===== ADMIN PRODUCT UPLOAD FUNCTIONS =====

# Hardcoded admin credentials for product management
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin@123'

def verify_admin(username, password):
    """Verify admin credentials. Returns True/False."""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def create_products_from_csv(products_list):
    """Create multiple products from a list of dicts (from CSV). Returns (success_count, errors, skipped)."""
    import random
    conn = get_db()
    success = 0
    errors = []
    skipped = 0

    for i, p in enumerate(products_list, 1):
        try:
            # Mandatory fields
            tracking_id = str(p.get('tracking_id', '') or '').strip()
            myntra_sku = str(p.get('myntra_sku', '') or '').strip()
            item_barcode = str(p.get('item_barcode', '') or '').strip()
            style_id = str(p.get('style_id', '') or '').strip()
            article_no = str(p.get('article_no', '') or '').strip()

            missing = []
            if not tracking_id: missing.append('tracking_id')
            if not myntra_sku: missing.append('myntra_sku')
            if not item_barcode: missing.append('item_barcode')
            if not style_id: missing.append('style_id')
            if not article_no: missing.append('article_no')
            if missing:
                errors.append(f"Row {i}: Missing mandatory columns: {', '.join(missing)}")
                continue

            # Optional fields
            brand = str(p.get('brand', '') or '').strip()
            name = str(p.get('name', '') or '').strip()
            image_filename = str(p.get('image_filename', '') or '').strip()
            image_filename_2 = str(p.get('image_filename_2', '') or '').strip() or None
            image_filename_3 = str(p.get('image_filename_3', '') or '').strip() or None
            description = str(p.get('description', '') or '').strip()
            size = str(p.get('size', '') or '').strip()
            color = str(p.get('color', '') or '').strip()
            category = str(p.get('category', '') or '').strip()
            return_type = str(p.get('return_type', 'NORMAL') or 'NORMAL').strip()
            return_mode = str(p.get('return_mode', 'OPEN_BOX_PICKUP') or 'OPEN_BOX_PICKUP').strip()

            try:
                mrp = float(p.get('mrp', 0) or 0)
            except (ValueError, TypeError):
                mrp = 0

            try:
                eligible_brand_tag = int(p.get('eligible_brand_tag', 0) or 0)
            except (ValueError, TypeError):
                eligible_brand_tag = 0


            cursor = conn.execute('''
                INSERT INTO products (brand, name, image_filename, image_filename_2, image_filename_3,
                    description, item_barcode, tracking_id, myntra_sku, style_id, article_no,
                    size, mrp, color, category, return_type, return_mode, eligible_brand_tag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                brand, name, image_filename, image_filename_2, image_filename_3,
                description, item_barcode, tracking_id, myntra_sku, style_id,
                article_no, size, mrp, color, category, return_type, return_mode,
                eligible_brand_tag
            ))
            product_id = cursor.lastrowid

            # Add expected answer if provided
            expected_qc = str(p.get('expected_qc_result', '') or '').strip()
            expected_issue = str(p.get('expected_issue', '') or '').strip()
            if expected_qc:
                if not expected_issue:
                    expected_issue = 'no-issues'
                conn.execute(
                    'INSERT INTO product_expected_answers (product_id, expected_qc_result, expected_issue) VALUES (?, ?, ?)',
                    (product_id, expected_qc, expected_issue)
                )

            success += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    conn.commit()
    conn.close()
    return success, errors

# Initialize DB on import
init_db()
