"""
PV Tool Training — Flask Server
Run: python server.py
Access: http://localhost:5000
"""
import os
import csv
import io
from flask import Flask, request, jsonify, send_from_directory, session, Response
from database import (
    init_db, create_user, create_users_bulk, verify_login, get_all_users,
    get_product, get_product_by_tracking_id, get_product_by_item_barcode, get_all_products, get_product_count, get_next_product_for_user,
    create_session, end_session,
    start_pv, complete_pv,
    get_user_stats, get_all_users_stats, get_user_pv_history,
    get_export_data,
    verify_admin, create_products_from_csv
)

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'pv-training-secret-key-2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ===== SERVE FRONTEND =====

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/styles.css')
def styles():
    return send_from_directory(BASE_DIR, 'styles.css')

@app.route('/app.js')
def appjs():
    return send_from_directory(BASE_DIR, 'app.js')

@app.route('/earth-bg.png')
def earth_bg():
    return send_from_directory(BASE_DIR, 'earth-bg.png')

@app.route('/product.png')
def product_img():
    return send_from_directory(BASE_DIR, 'product.png')

@app.route('/static/products/<path:filename>')
def product_images(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static', 'products'), filename)

# ===== AUTH API =====

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    name = data.get('name', '').strip()

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    if not name:
        name = email.split('@')[0]

    user_id = create_user(email, password, name)
    if user_id:
        return jsonify({'success': True, 'message': f'Account created for {email}', 'user_id': user_id})
    else:
        return jsonify({'error': 'Email already registered'}), 409

@app.route('/api/register/bulk', methods=['POST'])
def register_bulk():
    """Bulk register users from CSV upload. CSV format: email,password,name"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files are accepted'}), 400

    try:
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        users_list = list(reader)

        if not users_list:
            return jsonify({'error': 'CSV is empty'}), 400

        # Check required columns
        required = {'email', 'password'}
        headers = set(users_list[0].keys())
        if not required.issubset(headers):
            return jsonify({'error': f'CSV must have columns: email, password (and optionally name). Found: {list(headers)}'}), 400

        success, errors = create_users_bulk(users_list)
        return jsonify({
            'success': True,
            'created': success,
            'errors': errors,
            'total_in_csv': len(users_list)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to parse CSV: {str(e)}'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = verify_login(email, password)
    if user:
        # Create session
        sess_id = create_session(user['id'])
        session['user_id'] = user['id']
        session['session_id'] = sess_id
        session['user_email'] = user['email']
        session['user_name'] = user['name']
        return jsonify({
            'success': True,
            'user': {'id': user['id'], 'email': user['email'], 'name': user['name']},
            'session_id': sess_id,
            'total_products': get_product_count()
        })
    else:
        return jsonify({'error': 'Invalid email or password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    sess_id = session.get('session_id')
    if sess_id:
        end_session(sess_id)
    session.clear()
    return jsonify({'success': True})

@app.route('/api/warehouse', methods=['POST'])
def update_warehouse():
    """Update warehouse for the current session."""
    user_id = session.get('user_id')
    sess_id = session.get('session_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    warehouse = data.get('warehouse', '').strip()
    session['warehouse'] = warehouse

    # Update the session record in DB
    from database import get_db
    conn = get_db()
    conn.execute('UPDATE sessions SET warehouse = ? WHERE id = ?', (warehouse, sess_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/carton_code', methods=['POST'])
def update_carton_code():
    """Update carton code for the current session."""
    user_id = session.get('user_id')
    sess_id = session.get('session_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    carton_code = data.get('carton_code', '').strip()
    session['carton_code'] = carton_code

    from database import get_db
    conn = get_db()
    conn.execute('UPDATE sessions SET carton_code = ? WHERE id = ?', (carton_code, sess_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ===== PRODUCT API =====

@app.route('/api/product/next', methods=['GET'])
def next_product():
    user_id = session.get('user_id')
    sess_id = session.get('session_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    product = get_next_product_for_user(user_id, sess_id)
    if product:
        # Count how many done in this session
        from database import get_db
        conn = get_db()
        done = conn.execute(
            'SELECT COUNT(*) as cnt FROM pv_logs WHERE session_id = ? AND completed_at IS NOT NULL',
            (sess_id,)
        ).fetchone()['cnt']
        conn.close()

        return jsonify({
            'product': product,
            'products_done': done,
            'total_products': get_product_count()
        })
    else:
        return jsonify({'product': None, 'message': 'All products processed!', 'products_done': get_product_count(), 'total_products': get_product_count()})

@app.route('/api/product/<int:product_id>', methods=['GET'])
def get_single_product(product_id):
    product = get_product(product_id)
    if product:
        return jsonify({'product': product})
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/product/by-tracking-id/<path:tracking_id>', methods=['GET'])
def get_product_by_tracking_id_route(tracking_id):
    """Look up a product by its Tracking ID."""
    product = get_product_by_tracking_id(tracking_id.strip())
    if product:
        return jsonify({'product': product})
    return jsonify({'error': 'Product not found for Tracking ID: ' + tracking_id}), 404

@app.route('/api/product/by-item-barcode/<path:barcode>', methods=['GET'])
def get_product_by_item_barcode_route(barcode):
    """Look up a product by its Item Barcode."""
    product = get_product_by_item_barcode(barcode.strip())
    if product:
        return jsonify({'product': product})
    return jsonify({'error': 'Product not found for Item Barcode: ' + barcode}), 404

# ===== PV TRACKING API =====

@app.route('/api/pv/start', methods=['POST'])
def pv_start():
    user_id = session.get('user_id')
    sess_id = session.get('session_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    product_id = data.get('product_id')
    if not product_id:
        return jsonify({'error': 'product_id required'}), 400

    log_id = start_pv(sess_id, user_id, product_id)
    return jsonify({'success': True, 'log_id': log_id})

@app.route('/api/pv/complete', methods=['POST'])
def pv_complete():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    log_id = data.get('log_id')
    gtin_result = data.get('gtin_result', 'PASS')
    issue_selected = data.get('issue_selected', 'no-issues')
    qc_result = data.get('qc_result', 'pass')

    if not log_id:
        return jsonify({'error': 'log_id required'}), 400

    elapsed = complete_pv(log_id, gtin_result, issue_selected, qc_result)
    return jsonify({'success': True, 'time_seconds': round(elapsed, 1)})

# ===== STATS / DASHBOARD API =====

@app.route('/api/stats', methods=['GET'])
def overall_stats():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    from database import get_overall_stats, get_overall_pv_history
    stats = get_overall_stats()
    history = get_overall_pv_history()
    return jsonify({'stats': stats, 'history': history})

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    all_stats = get_all_users_stats()
    return jsonify({'users': all_stats, 'total_products': get_product_count()})

@app.route('/api/users', methods=['GET'])
def users_list():
    users = get_all_users()
    return jsonify({'users': users})

# ===== SESSION CHECK API =====

@app.route('/api/me', methods=['GET'])
def me():
    """Return current logged-in user info (used to restore state after page refresh)."""
    user_id = session.get('user_id')
    if user_id:
        return jsonify({
            'logged_in': True,
            'user': {
                'id': user_id,
                'email': session.get('user_email', ''),
                'name': session.get('user_name', '')
            },
            'session_id': session.get('session_id'),
            'total_products': get_product_count()
        })
    return jsonify({'logged_in': False}), 401

# ===== EXPORT DATA API =====

@app.route('/api/export', methods=['GET'])
def export_data():
    """Return filtered PV log data as JSON."""
    date_from = request.args.get('date_from', '').strip() or None
    date_to = request.args.get('date_to', '').strip() or None
    name = request.args.get('name', '').strip() or None
    carton_code = request.args.get('carton_code', '').strip() or None
    warehouse = request.args.get('warehouse', '').strip() or None

    data = get_export_data(date_from, date_to, name, carton_code, warehouse)
    return jsonify({'data': data, 'total': len(data)})

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Download filtered PV log data as CSV file."""
    date_from = request.args.get('date_from', '').strip() or None
    date_to = request.args.get('date_to', '').strip() or None
    name = request.args.get('name', '').strip() or None
    carton_code = request.args.get('carton_code', '').strip() or None
    warehouse = request.args.get('warehouse', '').strip() or None

    data = get_export_data(date_from, date_to, name, carton_code, warehouse)

    if not data:
        return jsonify({'error': 'No data found for the given filters'}), 404

    output = io.StringIO()
    headers = [
        'Name', 'Email', 'Warehouse', 'Carton Code', 'Brand', 'Product',
        'Category', 'Item Barcode', 'Tracking ID', 'Myntra SKU', 'Size', 'MRP', 'Color',
        'Started At', 'Completed At', 'Time (seconds)',
        'GTIN Result', 'Issue Selected', 'QC Result',
        'Expected QC', 'Expected Issue', 'Accuracy'
    ]
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()

    for row in data:
        writer.writerow({
            'Name': row.get('name', ''),
            'Email': row.get('email', ''),
            'Warehouse': row.get('warehouse', ''),
            'Carton Code': row.get('carton_code', ''),
            'Brand': row.get('brand', ''),
            'Product': row.get('product_name', ''),
            'Category': row.get('category', ''),
            'Item Barcode': row.get('item_barcode', ''),
            'Tracking ID': row.get('tracking_id', ''),
            'Myntra SKU': row.get('myntra_sku', ''),
            'Size': row.get('size', ''),
            'MRP': row.get('mrp', ''),
            'Color': row.get('color', ''),
            'Started At': row.get('started_at', ''),
            'Completed At': row.get('completed_at', ''),
            'Time (seconds)': row.get('time_seconds', ''),
            'GTIN Result': row.get('gtin_result', ''),
            'Issue Selected': row.get('issue_selected', ''),
            'QC Result': row.get('qc_result', ''),
            'Expected QC': row.get('expected_qc_result', ''),
            'Expected Issue': row.get('expected_issue', ''),
            'Accuracy': row.get('accuracy_result', ''),
        })

    csv_content = output.getvalue()
    output.close()

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=pv_export_data.csv'}
    )

# ===== ADMIN PRODUCT UPLOAD API =====

@app.route('/api/admin/products/upload', methods=['POST'])
def admin_upload_products():
    """Upload products via CSV with admin authentication."""
    admin_username = request.form.get('admin_username', '').strip()
    admin_password = request.form.get('admin_password', '').strip()

    if not admin_username or not admin_password:
        return jsonify({'error': 'Admin username and password are required'}), 400

    if not verify_admin(admin_username, admin_password):
        return jsonify({'error': 'Invalid admin credentials'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No CSV file uploaded'}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files are accepted'}), 400

    try:
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        products_list = list(reader)

        if not products_list:
            return jsonify({'error': 'CSV is empty'}), 400

        # Check minimum required columns
        required = {'tracking_id', 'myntra_sku', 'item_barcode', 'style_id', 'article_no'}
        headers = set(products_list[0].keys())
        if not required.issubset(headers):
            missing = required - headers
            return jsonify({
                'error': f'CSV is missing mandatory columns: {", ".join(sorted(missing))}. Required: tracking_id, myntra_sku, item_barcode, style_id, article_no'
            }), 400

        success, errors = create_products_from_csv(products_list)
        return jsonify({
            'success': True,
            'created': success,
            'errors': errors,
            'total_in_csv': len(products_list),
            'new_total_products': get_product_count()
        })
    except Exception as e:
        return jsonify({'error': f'Failed to parse CSV: {str(e)}'}), 400

@app.route('/api/admin/products/count', methods=['GET'])
def admin_product_count():
    """Get current product count."""
    return jsonify({'total_products': get_product_count()})

@app.route('/api/admin/products/delete', methods=['POST'])
def admin_delete_product():
    """Delete a product by Tracking ID with admin authentication."""
    data = request.json
    admin_username = data.get('admin_username', '').strip()
    admin_password = data.get('admin_password', '').strip()
    tracking_id = data.get('tracking_id', '').strip()

    if not admin_username or not admin_password:
        return jsonify({'error': 'Admin username and password are required'}), 400

    if not verify_admin(admin_username, admin_password):
        return jsonify({'error': 'Invalid admin credentials'}), 401

    if not tracking_id:
        return jsonify({'error': 'Tracking ID is required'}), 400

    from database import delete_product_by_tracking_id, get_product_count
    success = delete_product_by_tracking_id(tracking_id)
    if success:
        return jsonify({
            'success': True,
            'message': f'Product {tracking_id} deleted successfully',
            'new_total_products': get_product_count()
        })
    else:
        return jsonify({'error': f'Product with Tracking ID {tracking_id} not found'}), 404

# ===== MAIN =====

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("  PV Tool Training Server")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
