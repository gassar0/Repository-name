import os
import sqlite3
import hashlib
import time
import base64
import json
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret-jwt-key-2026"
jwt = JWTManager(app)

def hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'salt_2026', 100000).hex()

def generate_jwt(user_id: int, username: str) -> str:
    header = json.dumps({"alg": "HS256", "typ": "JWT"}).encode('utf-8')
    payload = json.dumps({"sub": user_id, "username": username, "exp": int(time.time()) + 3600}).encode('utf-8')
    b64_header = base64.urlsafe_b64encode(header).decode('utf-8').rstrip('=')
    b64_payload = base64.urlsafe_b64encode(payload).decode('utf-8').rstrip('=')
    signature = hashlib.sha256(f"{b64_header}.{b64_payload}".encode('utf-8')).hexdigest()
    return f"{b64_header}.{b64_payload}.{signature}"

# إعداد قاعدة البيانات
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, name TEXT, price REAL, stock INTEGER)')
conn.commit()
conn.close()

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "السيرفر يعمل بنجاح على الاستضافة السحابية!"})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                       (data.get('username'), hash_password(data.get('password', ''))))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "تم إنشاء الحساب"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status": "fail", "message": "المستخدم موجود مسبقاً"}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (data.get('username'),))
    row = cursor.fetchone()
    conn.close()

    if row and row[1] == hash_password(data.get('password', '')):
        token = generate_jwt(row[0], data.get('username'))
        return jsonify({"status": "success", "access_token": token}), 200
    
    return jsonify({"status": "fail", "message": "بيانات الدخول خطأ"}), 401

@app.route('/api/protected', methods=['GET'])

def protected_route():
    current_user = get_jwt_identity()
    return jsonify({
        "status": "success",
        "message": f"لقد وصلت إلى مسار محمي بنجاح، مرحباً {current_user}"
    }), 200
# 1. مسار لجلب وعرض كل المنتجات في المخزون (متاح للجميع)
@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, stock FROM inventory")
    items = cursor.fetchall()
    conn.close()
    
    # تحويل البيانات إلى شكل يفهمه الـ API
    inventory_list = []
    for item in items:
        inventory_list.append({
            "id": item[0],
            "name": item[1],
            "price": item[2],
            "stock": item[3]
        })
        
    return jsonify({"status": "success", "data": inventory_list}), 200


# 2. مسار لإضافة منتج جديد (محمي بالـ Token الذي استخرجناه)
@app.route('/api/inventory/add', methods=['GET'])
def add_test_item():     # دالة الاختبار القديمة
    return jsonify({"status": "success", "message": "تم إضافة منتج تجريبي"})

@app.route('/api/inventory/add-item', methods=['POST'])
def add_real_item():
    data = request.get_json() or {}
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO inventory (name, price, stock) VALUES (?, ?, ?)", (name, price, stock))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": "تم إضافة المنتج بنجاح!"})

    name = "شاشة كمبيوتر"
    price = 1200
    stock = 5

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO inventory (name, price, stock) VALUES (?, ?, ?)", (name, price, stock))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "تم إضافة المنتج بنجاح!", "data": {"name": name, "price": price, "stock": stock}})
    
@app.route('/api/inventory/add-item', methods=['POST'])
def add_real_item():
    data = request.get_json() or {}
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO inventory (name, price, stock) VALUES (?, ?, ?)", (name, price, stock))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": "تم إضافة المنتج بنجاح!"})
  
