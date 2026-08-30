import csv
import io
import os
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
import json
import traceback
import threading
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'smart_store_secret_key_12345'

# ط¥ط¹ط¯ط§ط¯ ظ…ط¬ظ„ط¯ ط±ظپط¹ ط§ظ„طµظˆط±
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_Name = 'store.db'

# ط¥ط¹ط¯ط§ط¯ط§طھ ط¨ظˆطھ طھظٹظ„ظٹط¬ط±ط§ظ…
TELEGRAM_BOT_TOKEN = '8969435828:AAEsccn8O8KuiqaVLQSERnxY2rstA8SF8JQ'
TELEGRAM_CHAT_ID = '8508616708'

# ظ‚ط§ظ„ط¨ طµظپط­ط© ط§ظ„ط¯ط®ظˆظ„ ظˆط§ظ„طھط³ط¬ظٹظ„
AUTH_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>{% if mode == 'login' %}طھط³ط¬ظٹظ„ ط§ظ„ط¯ط®ظˆظ„{% else %}ط¥ظ†ط´ط§ط، ط­ط³ط§ط¨ ط¬ط¯ظٹط¯{% endif %}</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: Tahoma, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #161b22; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 350px; text-align: center; border: 1px solid #30363d; }
        input { width: 90%; padding: 12px; margin: 10px 0; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #238636; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        button:hover { background: #2ea043; }
        a { color: #58a6ff; text-decoration: none; display: block; margin-top: 15px; }
        .error { color: #f85149; margin-bottom: 10px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>{% if mode == 'login' %}ًں”‘ طھط³ط¬ظٹظ„ ط§ظ„ط¯ط®ظˆظ„{% else %}ًں“‌ ط¥ظ†ط´ط§ط، ط­ط³ط§ط¨ ط¬ط¯ظٹط¯{% endif %}</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="ط§ط³ظ… ط§ظ„ظ…ط³طھط®ط¯ظ…" required autocomplete="off"><br>
            <input type="password" name="password" placeholder="ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط±" required><br>
            <button type="submit">{% if mode == 'login' %}ط¯ط®ظˆظ„{% else %}طھط³ط¬ظٹظ„{% endif %}</button>
        </form>
        {% if mode == 'login' %}
            <a href="{{ url_for('register') }}">ظ„ظٹط³ ظ„ط¯ظٹظƒ ط­ط³ط§ط¨طں ط¥ظ†ط´ط§ط، ط­ط³ط§ط¨ ط¬ط¯ظٹط¯</a>
        {% else %}
            <a href="{{ url_for('login') }}">ظ„ط¯ظٹظƒ ط­ط³ط§ط¨ ط¨ط§ظ„ظپط¹ظ„طں طھط³ط¬ظٹظ„ ط§ظ„ط¯ط®ظˆظ„</a>
        {% endif %}
        <a href="{{ url_for('index') }}">ط§ظ„ط¹ظˆط¯ط© ظ„ظ„ط±ط¦ظٹط³ظٹط©</a>
    </div>
</body>
</html>
"""

# ظ‚ط§ظ„ط¨ ط§ظ„ظ…طھط¬ط± ط§ظ„ط±ط¦ظٹط³ظٹ ظ…ط¹ ط§ظ„ط³ظ„ط© ظˆطھظٹظ„ظٹط¬ط±ط§ظ…
STORE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ط§ظ„ظ…طھط¬ط± ط§ظ„ط¥ظ„ظƒطھط±ظˆظ†ظٹ ط§ظ„ط°ظƒظٹ</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; direction: rtl; }
        .container { max-width: 800px; margin: auto; }
        .card { background: #161b22; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 20px; border: 1px solid #30363d; }
        h1, h2 { color: #58a6ff; text-align: center; }
        .btn { display: inline-block; padding: 8px 16px; background: #238636; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; border: none; cursor: pointer; text-align: center; font-size: 14px; }
        .btn:hover { background: #2ea043; }
        .btn-danger { background: #da3633; }
        .btn-danger:hover { background: #f85149; }
        .btn-secondary { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; }
        .btn-secondary:hover { background: #30363d; }
        input, select { width: 100%; padding: 10px; margin: 8px 0; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 6px; box-sizing: border-box; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #30363d; padding: 10px; text-align: center; font-size: 14px; }
        th { background: #21262d; color: #58a6ff; }
        .user-bar { display: flex; justify-content: space-between; align-items: center; background: #21262d; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #30363d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="user-bar">
            <div>
                {% if user %}
                    <span>ظ…ط±ط­ط¨ط§ظ‹طŒ <b>{{ user }}</b></span>
                {% else %}
                    <span>ظ…ط±ط­ط¨ط§ظ‹ ط¨ظƒ ط²ط§ط¦ط±ظ†ط§ ط§ظ„ظƒط±ظٹظ…</span>
                {% endif %}
            </div>
            <div>
                {% if user %}
                    <a href="{{ url_for('logout') }}" class="btn btn-danger" style="padding: 6px 12px; font-size: 13px;">طھط³ط¬ظٹظ„ ط§ظ„ط®ط±ظˆط¬</a>
                {% else %}
                    <a href="{{ url_for('login') }}" class="btn" style="padding: 6px 12px; font-size: 13px; margin-left: 5px;">طھط³ط¬ظٹظ„ ط§ظ„ط¯ط®ظˆظ„</a>
                    <a href="{{ url_for('register') }}" class="btn btn-secondary" style="padding: 6px 12px; font-size: 13px;">ط¥ظ†ط´ط§ط، ط­ط³ط§ط¨</a>
                {% endif %}
            </div>
        </div>

        <div class="card">
            <h1>ًں›چï¸ڈ ط§ظ„ظ…طھط¬ط± ط§ظ„ط¥ظ„ظƒطھط±ظˆظ†ظٹ ط§ظ„ط°ظƒظٹ</h1>
            <div style="text-align: center;">
                <a href="{{ url_for('view_cart') }}" class="btn">ًں›’ ط¹ط±ط¶ ط³ظ„ط© ط§ظ„ط´ط±ط§ط، ({{ cart|length }})</a>
            </div>
        </div>

        <!-- ظ‚ط³ظ… ط¹ط±ط¶ ط§ظ„ط³ظ„ط© -->
        {% if show_cart %}
        <div class="card" style="border-color: #58a6ff;">
            <h2>ًں›’ ط³ظ„ط© ط§ظ„ط´ط±ط§ط، ط§ظ„ط®ط§طµط© ط¨ظƒ</h2>
            {% if cart %}
                <table>
                    <tr>
                        <th>ط§ط³ظ… ط§ظ„ظ…ظ†طھط¬</th>
                        <th>ط§ظ„ط³ط¹ط±</th>
                        <th>ط¥ط¬ط±ط§ط،</th>
                    </tr>
                    {% set ns = namespace(total=0) %}
                    {% for item in cart %}
                    {% set ns.total = ns.total + item.price %}
                    <tr>
                        <td>{{ item.name }}</td>
                        <td>{{ item.price }} ط±.ط³</td>
                        <td>
                            <a href="{{ url_for('remove_from_cart', index=loop.index0) }}" class="btn btn-danger" style="padding: 4px 8px; font-size: 12px;">ط­ط°ظپ ظ…ظ† ط§ظ„ط³ظ„ط©</a>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
                <h3 style="margin-top: 15px; color: #3fb950;">ط§ظ„ط¥ط¬ظ…ط§ظ„ظٹ ط§ظ„ظƒظ„ظٹ: {{ ns.total }} ط±.ط³</h3>
                
                <form action="{{ url_for('checkout') }}" method="POST" onsubmit="alert('ًںڑ€ طھظ… ط¥ط±ط³ط§ظ„ ط§ظ„ط·ظ„ط¨ ظˆطھط³ط¬ظٹظ„ظ‡ ط¨ظ†ط¬ط§ط­!');" style="margin-top: 15px;">
                    <input type="email" name="email" placeholder="ط¨ط±ظٹط¯ظƒ ط§ظ„ط¥ظ„ظƒطھط±ظˆظ†ظٹ (ط§ط®طھظٹط§ط±ظٹ)" value="mmmmm_mmmmm319@yahoo.com">
                    <input type="hidden" name="total" value="{{ ns.total }}">
                    <button type="submit" class="btn" style="width: 100%; background-color: #238636; padding: 12px; font-size: 16px;">ًںڑ€ ط¥طھظ…ط§ظ… ط§ظ„ط´ط±ط§ط، ظˆط¥ط±ط³ط§ظ„ ط§ظ„ط·ظ„ط¨ ظ„طھظٹظ„ظٹط¬ط±ط§ظ…</button>
                </form>
            {% else %}
                <p style="text-align: center; color: #8b949e;">ط³ظ„ط© ط§ظ„ط´ط±ط§ط، ظپط§ط±ط؛ط© ط­ط§ظ„ظٹط§ظ‹.</p>
            {% endif %}
            <div style="text-align: center; margin-top: 15px;">
                <a href="{{ url_for('index') }}" class="btn btn-secondary">ط§ظ„ط¹ظˆط¯ط© ظ„ظ„ظ…ظ†طھط¬ط§طھ</a>
            </div>
        </div>
        {% endif %}

        <div class="card">
            <h2>ًں”¥ ط§ظ„ظ…ظ†طھط¬ط§طھ ط§ظ„ظ…طھظˆظپط±ط©</h2>
            <form method="GET" action="/" style="display: flex; gap: 10px; margin-bottom: 15px;">
                <input type="text" name="search" placeholder="ط§ط¨ط­ط« ط¹ظ† ط§ط³ظ… ط§ظ„ظ…ظ†طھط¬ ط£ظˆ ط§ظ„ط¨ط§ط¦ط¹..." value="{{ request.args.get('search', '') }}">
                <button type="submit" class="btn" style="width: auto;">ط¨ط­ط«</button>
            </form>

            {% if products %}
                <table>
                    <tr>
                        <th>ط§ظ„طµظˆط±ط©</th>
                        <th>ط§ط³ظ… ط§ظ„ظ…ظ†طھط¬</th>
                        <th>ط§ظ„ط³ط¹ط±</th>
                        <th>ط§ظ„ظƒظ…ظٹط©</th>
                        <th>ط§ظ„ط¨ط§ط¦ط¹</th>
                        <th>ط§ظ„ط¥ط¬ط±ط§ط،ط§طھ</th>
                    </tr>
                    {% for p in products %}
                    <tr>
                        <td>
                            {% if p.image %}
                                <img src="{{ url_for('static', filename='uploads/' + p.image) }}" width="45" style="border-radius: 4px;">
                            {% else %}
                                <span style="font-size: 12px; color: #8b949e;">ظ„ط§ طھظˆط¬ط¯</span>
                            {% endif %}
                        </td>
                        <td>{{ p.name }}</td>
                        <td>{{ p.price }} ط±.ط³</td>
                        <td>{{ p.quantity }}</td>
                        <td>{{ p.seller }}</td>
                        <td>
                            <a href="{{ url_for('add_to_cart', id=p.id) }}" class="btn" style="padding: 5px 10px; font-size: 12px; margin-bottom: 4px; display: inline-block;">ًں›’ ط´ط±ط§ط،</a>
                            {% if user %}
                                <a href="{{ url_for('delete_product', id=p.id) }}" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px; display: inline-block;">ط­ط°ظپ</a>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            {% else %}
                <p style="text-align: center; color: #8b949e;">ظ„ط§ طھظˆط¬ط¯ ظ…ظ†طھط¬ط§طھ ظ…طھط§ط­ط© ط­ط§ظ„ظٹط§ظ‹.</p>
            {% endif %}
        </div>

        {% if user %}
        <div class="card">
            <h2>â‍• ط¥ط¶ط§ظپط© ظ…ظ†طھط¬ ط¬ط¯ظٹط¯</h2>
            <form action="{{ url_for('add_product') }}" method="POST" enctype="multipart/form-data">
                <input type="text" name="name" placeholder="ط§ط³ظ… ط§ظ„ظ…ظ†طھط¬" required>
                <input type="number" name="price" placeholder="ط§ظ„ط³ط¹ط± (ط±.ط³)" step="0.01" required>
                <input type="number" name="quantity" placeholder="ط§ظ„ظƒظ…ظٹط©" value="1" required>
                <input type="text" name="seller" placeholder="ط§ط³ظ… ط§ظ„ط¨ط§ط¦ط¹" value="{{ user }}">
                <input type="file" name="image" accept="image/*">
                <button type="submit" class="btn" style="width: 100%; margin-top: 10px;">ط¥ط¶ط§ظپط© ط§ظ„ظ…ظ†طھط¬ ظ„ظ„ظ…طھط¬ط±</button>
            </form>
        </div>

        <div class="card">
            <h2>ًں“¦ ط·ظ„ط¨ط§طھ ط§ظ„ط¹ظ…ظ„ط§ط، ط§ظ„ظ…ط³ط¬ظ„ط©</h2>
            {% if orders %}
                <table>
                    <tr>
                        <th>ط±ظ‚ظ… ط§ظ„ط·ظ„ط¨</th>
                        <th>ط§ظ„ط¨ط±ظٹط¯ ط§ظ„ط¥ظ„ظƒطھط±ظˆظ†ظٹ</th>
                        <th>ط§ظ„ط¥ط¬ظ…ط§ظ„ظٹ</th>
                        <th>ط§ظ„ط­ط§ظ„ط©</th>
                    </tr>
                    {% for o in orders %}
                    <tr>
                        <td>#{{ o.id }}</td>
                        <td>{{ o.customer_email }}</td>
                        <td>{{ o.total }} ط±.ط³</td>
                        <td>{{ o.status if o.status else 'ط¬ط¯ظٹط¯' }}</td>
                    </tr>
                    {% endfor %}
                </table>
            {% else %}
                <p style="text-align: center; color: #8b949e;">ظ„ط§ طھظˆط¬ط¯ ط·ظ„ط¨ط§طھ ط­طھظ‰ ط§ظ„ط¢ظ†.</p>
            {% endif %}
        </div>
        {% endif %}

    </div>
</body>
</html>
"""

def get_db_connection():
    conn = sqlite3.connect(DB_Name)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            seller TEXT,
            image TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_email TEXT,
            total REAL,
            status TEXT DEFAULT 'ط¬ط¯ظٹط¯'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # ط§ظ„طھط£ظƒط¯ ظ…ظ† ط¥ط¶ط§ظپط© ط¹ظ…ظˆط¯ status طھظ„ظ‚ط§ط¦ظٹط§ظ‹ ظ„ظˆ ط§ظ„ط¬ط¯ظˆظ„ ظ‚ط¯ظٹظ…
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'ط¬ط¯ظٹط¯'")
    except sqlite3.OperationalError:
        pass # ط§ظ„ط¹ظ…ظˆط¯ ظ…ظˆط¬ظˆط¯ ط¨ط§ظ„ظپط¹ظ„
        
    conn.commit()
    conn.close()

init_db()

def send_telegram_order_notification(order_details, order_id):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": order_details,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "âœ… طھط£ظƒظٹط¯ ط§ظ„ط·ظ„ط¨", "callback_data": f"confirm_{order_id}"},
                    {"text": "â‌Œ ط¥ظ„ط؛ط§ط، ط§ظ„ط·ظ„ط¨", "callback_data": f"cancel_{order_id}"}
                ]
            ]
        }
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram notification error: {e}")

@app.route('/')
def index():
    try:
        search_query = request.args.get('search', '').strip()
        conn = get_db_connection()
        if search_query:
            products = conn.execute("SELECT * FROM products WHERE name LIKE ? OR seller LIKE ?", 
                                    (f'%{search_query}%', f'%{search_query}%')).fetchall()
        else:
            products = conn.execute("SELECT * FROM products").fetchall()
        orders = conn.execute("SELECT * FROM orders").fetchall()
        conn.close()
        
        cart = session.get('cart', [])
        user = session.get('user', None)
        return render_template_string(STORE_HTML_TEMPLATE, products=products, cart=cart, orders=orders, user=user, show_cart=False)
    except Exception as e:
        print("--- TEMPLATE ERROR ---")
        traceback.print_exc()
        return f"ط­ط¯ط« ط®ط·ط£: {e}", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user'] = user['username']
            return redirect(url_for('index'))
        else:
            error = "ط§ط³ظ… ط§ظ„ظ…ط³طھط®ط¯ظ… ط£ظˆ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط؛ظٹط± طµط­ظٹط­ط©"
            
    return render_template_string(AUTH_HTML_TEMPLATE, mode='login', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            session['user'] = username
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            error = "ط§ط³ظ… ط§ظ„ظ…ط³طھط®ط¯ظ… ظ…ط³طھط®ط¯ظ… ط¨ط§ظ„ظپط¹ظ„طŒ ط§ط®طھط± ط§ط³ظ…ظ‹ط§ ط¢ط®ط±."
            
    return render_template_string(AUTH_HTML_TEMPLATE, mode='register', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/add-to-cart/<int:id>')
def add_to_cart(id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    conn.close()
    
    if product:
        if 'cart' not in session:
            session['cart'] = []
        cart = session['cart']
        cart.append({'id': product['id'], 'name': product['name'], 'price': product['price']})
        session['cart'] = cart
    return redirect(url_for('view_cart'))

@app.route('/remove-from-cart/<int:index>')
def remove_from_cart(index):
    cart = session.get('cart', [])
    if 0 <= index < len(cart):
        cart.pop(index)
        session['cart'] = cart
    return redirect(url_for('view_cart'))

@app.route('/view-cart')
def view_cart():
    try:
        conn = get_db_connection()
        products = conn.execute("SELECT * FROM products").fetchall()
        orders = conn.execute("SELECT * FROM orders").fetchall()
        conn.close()
        cart = session.get('cart', [])
        user = session.get('user', None)
        return render_template_string(STORE_HTML_TEMPLATE, products=products, cart=cart, orders=orders, user=user, show_cart=True)
    except Exception as e:
        print(f"View cart error: {e}")
        return redirect(url_for('index'))

@app.route('/add-product', methods=['POST'])
def add_product():
    try:
        name = request.form.get('name')
        quantity = request.form.get('quantity', 1)
        price = request.form.get('price', 0.0)
        seller = request.form.get('seller', session.get('user', 'ظ…ط­ظ…ط¯ ط±ط¬ط¨'))
        
        image_filename = ""
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                
        conn = get_db_connection()
        conn.execute("INSERT INTO products (name, quantity, price, seller, image) VALUES (?, ?, ?, ?, ?)",
                     (name, quantity, price, seller, image_filename))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Add product error: {e}")
    return redirect(url_for('index'))

@app.route('/delete-product/<int:id>')
def delete_product(id):
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM products WHERE id = ?", (id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Delete error: {e}")
    return redirect(url_for('index'))

@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        customer_email = request.form.get('email', 'mmmmm_mmmmm319@yahoo.com')
        total_val = request.form.get('total', '0')
        try:
            total = float(total_val)
        except ValueError:
            total = 0.0
            
        cart = session.get('cart', [])
        if not cart:
            return redirect(url_for('index'))
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (customer_email, total, status) VALUES (?, ?, ?)", 
                       (customer_email, total, 'ط¬ط¯ظٹط¯'))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        items_summary = "\n".join([f"- {item['name']} ({item['price']} ط±.ط³)" for item in cart])
        msg = f"ًں›’ ط·ظ„ط¨ ط´ط±ط§ط، ط¬ط¯ظٹط¯ ط¹ط¨ط± ط§ظ„ظ…طھط¬ط±!\nًں‘¤ ط§ظ„ط¹ظ…ظٹظ„: {customer_email}\n\nط§ظ„ظ…ظ†طھط¬ط§طھ ط§ظ„ظ…ط·ظ„ظˆط¨ط©:\n{items_summary}\n\nًں’° ط§ظ„ط¥ط¬ظ…ط§ظ„ظٹ ط§ظ„ظƒظ„ظٹ: {total} ط±.ط³"
        
        threading.Thread(target=send_telegram_order_notification, args=(msg, order_id)).start()
        
        session['cart'] = []
    except Exception as e:
        print(f"Checkout error: {e}")
        traceback.print_exc()
        
    return redirect(url_for('index'))

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "ok"})
            
        if 'callback_query' in data:
            callback = data['callback_query']
            callback_data = callback['data']
            chat_id = callback['message']['chat']['id']
            message_id = callback['message']['message_id']
            callback_query_id = callback['id']
            original_text = callback['message']['text']
            
            action, order_id = callback_data.split('_', 1)
            
            response_text = ""
            status_suffix = ""
            
            if action == 'confirm':
                status_suffix = "\n\nâœ¨ **ط­ط§ظ„ط© ط§ظ„ط·ظ„ط¨:** طھظ… ط§ظ„طھط£ظƒظٹط¯ ط¨ظ†ط¬ط§ط­ âœ…"
                response_text = f"طھظ… طھط£ظƒظٹط¯ ط§ظ„ط·ظ„ط¨ #{order_id} ط¨ظ†ط¬ط§ط­!"
                if order_id != '999':
                    conn = get_db_connection()
                    conn.execute("UPDATE orders SET status = 'ظ…ط¤ظƒط¯' WHERE id = ?", (order_id,))
                    conn.commit()
                    conn.close()
                
            elif action == 'cancel':
                status_suffix = "\n\nًںڑ« **ط­ط§ظ„ط© ط§ظ„ط·ظ„ط¨:** طھظ… ط¥ظ„ط؛ط§ط، ط§ظ„ط·ظ„ط¨ â‌Œ"
                response_text = f"طھظ… ط¥ظ„ط؛ط§ط، ط§ظ„ط·ظ„ط¨ #{order_id}."
                if order_id != '999':
                    conn = get_db_connection()
                    conn.execute("UPDATE orders SET status = 'ظ…ظ„ط؛ظٹ' WHERE id = ?", (order_id,))
                    conn.commit()
                    conn.close()

            answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            answer_payload = {"callback_query_id": callback_query_id, "text": response_text}
            try:
                req = urllib.request.Request(answer_url, data=json.dumps(answer_payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req)
            except:
                pass

            edit_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
            edit_payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": original_text + status_suffix,
                "parse_mode": "Markdown"
            }
            try:
                req = urllib.request.Request(edit_url, data=json.dumps(edit_payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req)
            except:
                pass
    except Exception as e:
        print(f"Webhook error: {e}")
        traceback.print_exc()

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
