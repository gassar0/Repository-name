import os
import sqlite3
import urllib.request
import json
import traceback
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'smart_store_secret_key_12345'

# إعدادات تيليجرام
TELEGRAM_BOT_TOKEN = '8969435828:AAEsccn8O8KuiqaVLQSERnxY2rstA8SF8JQ'
TELEGRAM_CHAT_ID = '8508616708'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('templates', exist_ok=True)

DB_Name = 'store.db'

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
            phone TEXT,
            address TEXT,
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
    
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN phone TEXT")
        cursor.execute("ALTER TABLE orders ADD COLUMN address TEXT")
    except sqlite3.OperationalError:
        pass
        
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
    cart_count = len(cart)
    user = session.get('username', None)
    return render_template('index.html', products=products, cart_count=cart_count, orders=orders, username=user)

@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    total = sum(float(item['price']) for item in cart)
    user = session.get('username', None)
    return render_template('cart.html', cart=cart, total=total, username=user)

@app.route('/add-to-cart/<int:id>')
def add_to_cart(id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    conn.close()
    
    if product and product['quantity'] > 0:
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

@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        customer_email = request.form.get('email', 'mmmmm_mmmmm319@yahoo.com')
        phone = request.form.get('phone', 'غير متوفر')
        address = request.form.get('address', 'غير متوفر')
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
        
        # 1. تسجيل الطلب
        cursor.execute("INSERT INTO orders (customer_email, phone, address, total, status) VALUES (?, ?, ?, ?, ?)", 
                       (customer_email, phone, address, total, 'جديد'))
        order_id = cursor.lastrowid
        
        # 2. خصم الكمية تلقائياً من المخزون
        for item in cart:
            product_id = item['id']
            cursor.execute("UPDATE products SET quantity = quantity - 1 WHERE id = ? AND quantity > 0", (product_id,))
        
        conn.commit()
        conn.close()
        
        items_summary = "\n".join([f"- {item['name']} ({item['price']} ر.س)" for item in cart])
        msg = f"🛒 طلب شراء جديد عبر المتجر!\n👤 البريد: {customer_email}\n📞 الهاتف: {phone}\n📍 العنوان: {address}\n\nالمنتجات المطلوبة:\n{items_summary}\n\n💰 الإجمالي الكلي: {total} ر.س"
        
        send_telegram_order_notification(msg, order_id)
        
        session['cart'] = []
    except Exception as e:
        print(f"Checkout error: {e}")
        traceback.print_exc()
        
    return redirect(url_for('index'))

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
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            error = "اسم المستخدم أو كلمة المرور غير صحيحة"
    return render_template('login.html', error=error)

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
            session['username'] = username
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            error = "اسم المستخدم مستخدم بالفعل."
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/add-product', methods=['POST'])
def add_product():
    try:
        name = request.form.get('name')
        quantity = request.form.get('quantity', 1)
        price = request.form.get('price', 0.0)
        vendor = request.form.get('vendor', session.get('username', 'محمد رجب'))
        
        image_filename = ""
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                
        conn = get_db_connection()
        conn.execute("INSERT INTO products (name, quantity, price, seller, image) VALUES (?, ?, ?, ?, ?)",
                     (name, quantity, price, vendor, image_filename))
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

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.get_json()
        if not data or 'callback_query' not in data:
            return jsonify({"status": "ok"})
            
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
            status_suffix = "\n\n✨ حالة الطلب: تم التأكيد بنجاح ✅"
            response_text = f"تم تأكيد الطلب #{order_id} بنجاح!"
            if order_id.isdigit():
                conn = get_db_connection()
                conn.execute("UPDATE orders SET status = 'مؤكد' WHERE id = ?", (order_id,))
                conn.commit()
                conn.close()
            
        elif action == 'cancel':
            status_suffix = "\n\n🚫 حالة الطلب: تم إلغاء الطلب ❌"
            response_text = f"تم إلغاء الطلب #{order_id}."
            if order_id.isdigit():
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
            "text": original_text + status_suffix
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

@app.route('/test-telegram')
def test_telegram():
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "🧪 تجربة إرسال رسالة من المتجر الإلكتروني الذكي ✅"
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        res = urllib.request.urlopen(req)
        return f"<h3>✅ نجح الإرسال! راجع تيليجرام.</h3><p>{res.read().decode('utf-8')}</p>"
    except Exception as e:
        return f"<h3>❌ فشل الإرسال:</h3><p style='color:red;'>{e}</p>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
