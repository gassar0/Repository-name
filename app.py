import csv
import io
import os
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
import json
import traceback
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'smart_store_secret_key_12345'

# إعداد مجلد رفع الصور
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_Name = 'store.db'

# إعدادات بوت تيليجرام المحدثة بالأزرار التفاعلية
TELEGRAM_BOT_TOKEN = '8969435828:AAEsccn8O8KuiqaVLQSERnxY2rstA8SF8JQ'
TELEGRAM_CHAT_ID = '8508616708'

# قالب صفحة الدخول والتسجيل
AUTH_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>{% if mode == 'login' %}تسجيل الدخول{% else %}إنشاء حساب جديد{% endif %}</title>
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
        <h2>{% if mode == 'login' %}🔑 تسجيل الدخول{% else %}📝 إنشاء حساب جديد{% endif %}</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="اسم المستخدم" required autocomplete="off"><br>
            <input type="password" name="password" placeholder="كلمة المرور" required><br>
            <button type="submit">{% if mode == 'login' %}دخول{% else %}تسجيل{% endif %}</button>
        </form>
        {% if mode == 'login' %}
            <a href="{{ url_for('register') }}">ليس لديك حساب؟ إنشاء حساب جديد</a>
        {% else %}
            <a href="{{ url_for('login') }}">لديك حساب بالفعل؟ تسجيل الدخول</a>
        {% endif %}
        <a href="{{ url_for('index') }}">العودة للرئيسية</a>
    </div>
</body>
</html>
"""

# قالب المتجر الرئيسي مع السلة وتيليجرام
STORE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>المتجر الإلكتروني الذكي</title>
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
                    <span>مرحباً، <b>{{ user }}</b></span>
                {% else %}
                    <span>مرحباً بك زائرنا الكريم</span>
                {% endif %}
            </div>
            <div>
                {% if user %}
                    <a href="{{ url_for('logout') }}" class="btn btn-danger" style="padding: 6px 12px; font-size: 13px;">تسجيل الخروج</a>
                {% else %}
                    <a href="{{ url_for('login') }}" class="btn" style="padding: 6px 12px; font-size: 13px; margin-left: 5px;">تسجيل الدخول</a>
                    <a href="{{ url_for('register') }}" class="btn btn-secondary" style="padding: 6px 12px; font-size: 13px;">إنشاء حساب</a>
                {% endif %}
            </div>
        </div>

        <div class="card">
            <h1>🛍️ المتجر الإلكتروني الذكي</h1>
            <div style="text-align: center;">
                <a href="{{ url_for('view_cart') }}" class="btn">🛒 عرض سلة الشراء ({{ cart|length }})</a>
            </div>
        </div>

        <!-- قسم عرض السلة إذا كان العميل داخل صفحة السلة -->
        {% if show_cart %}
        <div class="card" style="border-color: #58a6ff;">
            <h2>🛒 سلة الشراء الخاصة بك</h2>
            {% if cart %}
                <table>
                    <tr>
                        <th>اسم المنتج</th>
                        <th>السعر</th>
                        <th>إجراء</th>
                    </tr>
                    {% set ns = namespace(total=0) %}
                    {% for item in cart %}
                    {% set ns.total = ns.total + item.price %}
                    <tr>
                        <td>{{ item.name }}</td>
                        <td>{{ item.price }} ر.س</td>
                        <td>
                            <a href="{{ url_for('remove_from_cart', index=loop.index0) }}" class="btn btn-danger" style="padding: 4px 8px; font-size: 12px;">حذف من السلة</a>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
                <h3 style="margin-top: 15px; color: #3fb950;">الإجمالي الكلي: {{ ns.total }} ر.س</h3>
                
                <form action="{{ url_for('checkout') }}" method="POST" style="margin-top: 15px;">
                    <input type="email" name="email" placeholder="بريدك الإلكتروني (اختياري)" value="mmmmm_mmmmm319@yahoo.com">
                    <input type="hidden" name="total" value="{{ ns.total }}">
                    <button type="submit" class="btn" style="width: 100%; background-color: #238636; padding: 12px; font-size: 16px;">🚀 إتمام الشراء وإرسال الطلب لتيليجرام</button>
                </form>
            {% else %}
                <p style="text-align: center; color: #8b949e;">سلة الشراء فارغة حالياً.</p>
            {% endif %}
            <div style="text-align: center; margin-top: 15px;">
                <a href="{{ url_for('index') }}" class="btn btn-secondary">العودة للمنتجات</a>
            </div>
        </div>
        {% endif %}

        <div class="card">
            <h2>🔥 المنتجات المتوفرة</h2>
            <form method="GET" action="/" style="display: flex; gap: 10px; margin-bottom: 15px;">
                <input type="text" name="search" placeholder="ابحث عن اسم المنتج أو البائع..." value="{{ request.args.get('search', '') }}">
                <button type="submit" class="btn" style="width: auto;">بحث</button>
            </form>

            {% if products %}
                <table>
                    <tr>
                        <th>الصورة</th>
                        <th>اسم المنتج</th>
                        <th>السعر</th>
                        <th>الكمية</th>
                        <th>البائع</th>
                        <th>الإجراءات</th>
                    </tr>
                    {% for p in products %}
                    <tr>
                        <td>
                            {% if p.image %}
                                <img src="{{ url_for('static', filename='uploads/' + p.image) }}" width="45" style="border-radius: 4px;">
                            {% else %}
                                <span style="font-size: 12px; color: #8b949e;">لا توجد</span>
                            {% endif %}
                        </td>
                        <td>{{ p.name }}</td>
                        <td>{{ p.price }} ر.س</td>
                        <td>{{ p.quantity }}</td>
                        <td>{{ p.seller }}</td>
                        <td>
                            <a href="{{ url_for('add_to_cart', id=p.id) }}" class="btn" style="padding: 5px 10px; font-size: 12px; margin-bottom: 4px; display: inline-block;">🛒 شراء</a>
                            {% if user %}
                                <a href="{{ url_for('delete_product', id=p.id) }}" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px; display: inline-block;">حذف</a>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            {% else %}
                <p style="text-align: center; color: #8b949e;">لا توجد منتجات متاحة حالياً.</p>
            {% endif %}
        </div>

        {% if user %}
        <div class="card">
            <h2>➕ إضافة منتج جديد</h2>
            <form action="{{ url_for('add_product') }}" method="POST" enctype="multipart/form-data">
                <input type="text" name="name" placeholder="اسم المنتج" required>
                <input type="number" name="price" placeholder="السعر (ر.س)" step="0.01" required>
                <input type="number" name="quantity" placeholder="الكمية" value="1" required>
                <input type="text" name="seller" placeholder="اسم البائع" value="{{ user }}">
                <input type="file" name="image" accept="image/*">
                <button type="submit" class="btn" style="width: 100%; margin-top: 10px;">إضافة المنتج للمتجر</button>
            </form>
        </div>

        <div class="card">
            <h2>📦 طلبات العملاء المسجلة</h2>
            {% if orders %}
                <table>
                    <tr>
                        <th>رقم الطلب</th>
                        <th>البريد الإلكتروني</th>
                        <th>الإجمالي</th>
                        <th>الحالة</th>
                    </tr>
                    {% for o in orders %}
                    <tr>
                        <td>#{{ o.id }}</td>
                        <td>{{ o.customer_email }}</td>
                        <td>{{ o.total }} ر.س</td>
                        <td>{{ o.status }}</td>
                    </tr>
                    {% endfor %}
                </table>
            {% else %}
                <p style="text-align: center; color: #8b949e;">لا توجد طلبات حتى الآن.</p>
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
            status TEXT DEFAULT 'جديد'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
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
                    {"text": "✅ تأكيد الطلب", "callback_data": f"confirm_{order_id}"},
                    {"text": "❌ إلغاء الطلب", "callback_data": f"cancel_{order_id}"}
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
        return f"حدث خطأ: {e}", 500

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
            error = "اسم المستخدم أو كلمة المرور غير صحيحة"
            
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
            error = "اسم المستخدم مستخدم بالفعل، اختر اسمًا آخر."
            
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
        seller = request.form.get('seller', session.get('user', 'محمد رجب'))
        
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
        total = float(request.form.get('total', 0.0))
        cart = session.get('cart', [])
        
        if not cart:
            return redirect(url_for('index'))
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (customer_email, total, status) VALUES (?, ?, ?)", 
                       (customer_email, total, 'جديد'))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        items_summary = "\n".join([f"- {item['name']} ({item['price']} ر.س)" for item in cart])
        msg = f"🛒 طلب شراء جديد عبر المتجر!\n👤 العميل: {customer_email}\n\nالمنتجات المطلوبة:\n{items_summary}\n\n💰 الإجمالي الكلي: {total} ر.س"
        
        send_telegram_order_notification(msg, order_id)
        
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
                status_suffix = "\n\n✨ **حالة الطلب:** تم التأكيد بنجاح ✅"
                response_text = f"تم تأكيد الطلب #{order_id} بنجاح!"
                if order_id != '999':
                    conn = get_db_connection()
                    conn.execute("UPDATE orders SET status = 'مؤكد' WHERE id = ?", (order_id,))
                    conn.commit()
                    conn.close()
                
            elif action == 'cancel':
                status_suffix = "\n\n🚫 **حالة الطلب:** تم إلغاء الطلب ❌"
                response_text = f"تم إلغاء الطلب #{order_id}."
                if order_id != '999':
                    conn = get_db_connection()
                    conn.execute("UPDATE orders SET status = 'ملغي' WHERE id = ?", (order_id,))
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
