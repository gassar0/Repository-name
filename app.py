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
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
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

def get_db_connection():
    conn = sqlite3.connect(DB_Name)
    conn.row_factory = sqlite3.Row  # ضروري جداً لقراءة البيانات بالأسماء لتجنب أخطاء 500
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

# دالة إرسال الإشعار مع الأزرار التفاعلية
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
        conn = get_db_connection()
        products = conn.execute("SELECT * FROM products").fetchall()
        orders = conn.execute("SELECT * FROM orders").fetchall()
        conn.close()
        
        cart = session.get('cart', [])
        user = session.get('user', None)
        return render_template('store.html', products=products, cart=cart, orders=orders, user=user)
    except Exception as e:
        print("--- TEMPLATE RENDERING ERROR TRACEBACK ---")
        traceback.print_exc()
        return f"حدث خطأ في عرض الصفحة: {e}", 500

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
            
    return render_template('auth.html', mode='login', error=error)

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
            
    return render_template('auth.html', mode='register', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/view-cart')
def view_cart():
    try:
        conn = get_db_connection()
        products = conn.execute("SELECT * FROM products").fetchall()
        orders = conn.execute("SELECT * FROM orders").fetchall()
        conn.close()
        cart = session.get('cart', [])
        user = session.get('user', None)
        return render_template('store.html', products=products, cart=cart, orders=orders, user=user)
    except Exception as e:
        print(f"View cart error: {e}")
        return redirect(url_for('index'))

@app.route('/add-product', methods=['POST'])
def add_product():
    try:
        name = request.form.get('name')
        quantity = request.form.get('quantity', 1)
        price = request.form.get('price', 0.0)
        seller = request.form.get('seller', 'محمد رجب')
        
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
        traceback.print_exc()
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
        total = float(request.form.get('total', 1500.0))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (customer_email, total, status) VALUES (?, ?, ?)", 
                       (customer_email, total, 'جديد'))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        msg = f"🛒 طلب شراء جديد تم تنفيذه!\n👤 العميل: {customer_email}\n\n- لاب توب ديل (الكمية: 1) - السعر: {total} ر.س\n\n💰 الإجمالي الكلي: {total} ر.س"
        send_telegram_order_notification(msg, order_id)
        
        session['cart'] = []
    except Exception as e:
        print(f"Checkout error: {e}")
        traceback.print_exc()
        
    return redirect(url_for('index'))

@app.route('/export-csv')
def export_csv():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Quantity', 'Price', 'Seller', 'Image'])
    for p in products:
        cw.writerow([p['id'], p['name'], p['quantity'], p['price'], p['seller'], p['image']])
        
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=products.csv"}
    )

@app.route('/test-telegram', methods=['GET', 'POST'])
def test_telegram():
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read().decode('utf-8'))
        
        if data.get('ok'):
            bot_name = data['result'].get('first_name', 'Bot')
            bot_username = data['result'].get('username', '')
            
            test_msg = f"🚀 اختبار فوري من المتجر يا محمد! يعمل بنجاح ✅"
            send_telegram_order_notification(test_msg, 999)
            
            return jsonify({
                "status": "success", 
                "message": f"تم الاتصال بنجاح بالبوت: {bot_name} (@{bot_username})"
            })
        else:
            return jsonify({"status": "error", "message": "توكن غير صالح"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
