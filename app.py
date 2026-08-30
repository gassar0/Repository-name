import csv
import io
import os
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
import json
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

# إعدادات بوت تيليجرام المحدثة
TELEGRAM_BOT_TOKEN = '8969435828:AAEsccn8O8KuiqaVLQSERnxY2rstA8SF8JQ'
TELEGRAM_CHAT_ID = '8508616708'

def init_db():
    conn = sqlite3.connect(DB_Name)
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
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/add-product', methods=['POST'])
def add_product():
    name = request.form.get('name')
    quantity = request.form.get('quantity')
    price = request.form.get('price')
    seller = request.form.get('seller')
    
    image_filename = ""
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '':
            image_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, quantity, price, seller, image) VALUES (?, ?, ?, ?, ?)",
                   (name, quantity, price, seller, image_filename))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

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
            
            # إرسال رسالة اختبارية فورية مع الأزرار
            test_msg = f"🚀 اختبار فوري من المتجر يا محمد! يعمل بنجاح"
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
    data = request.get_json()
    
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
            
            # تحديث حالة الطلب في قاعدة البيانات إذا وجد
            if order_id != '999':
                conn = sqlite3.connect(DB_Name)
                cursor = conn.cursor()
                cursor.execute("UPDATE orders SET status = 'مؤكد' WHERE id = ?", (order_id,))
                conn.commit()
                conn.close()
            
        elif action == 'cancel':
            status_suffix = "\n\n🚫 **حالة الطلب:** تم إلغاء الطلب ❌"
            response_text = f"تم إلغاء الطلب #{order_id}."
            
            if order_id != '999':
                conn = sqlite3.connect(DB_Name)
                cursor = conn.cursor()
                cursor.execute("UPDATE orders SET status = 'ملغي' WHERE id = ?", (order_id,))
                conn.commit()
                conn.close()

        # الرد على ضغطة الزر
        answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        answer_payload = {"callback_query_id": callback_query_id, "text": response_text}
        try:
            req = urllib.request.Request(answer_url, data=json.dumps(answer_payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req)
        except:
            pass

        # تعديل رسالة تيليجرام لإظهار الحالة وإزالة الأزرار
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

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
