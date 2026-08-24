import os
import sqlite3
import hashlib
import hmac
import time
import base64
import json
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret-jwt-key"
jwt = JWTManager(app)

# إعداد وتجهيز قواعد البيانات والجداول
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# جدول المستخدمين
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
''')

# جدول المخزن
cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        user_id INTEGER
    )
''')
conn.commit()
conn.close()

def hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'salt', 100000).hex()

def generate_jwt(user_id: int, username: str) -> str:
    header = json.dumps({"alg": "HS256", "typ": "JWT"})
    payload = json.dumps({"sub": user_id, "username": username, "exp": int(time.time()) + 3600})
    b64_header = base64.urlsafe_b64encode(header.encode()).decode().rstrip("=")
    b64_payload = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    signature = hmac.new(app.config["JWT_SECRET_KEY"].encode(), f"{b64_header}.{b64_payload}".encode(), hashlib.sha256).digest()
    b64_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{b64_header}.{b64_payload}.{b64_signature}"

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "Server is running"})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    try:
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"status": "error", "message": "اسم المستخدم وكلمة المرور مطلوبان"}), 400

        hashed_pw = hash_password(password)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "تم تسجيل المستخدم بنجاح"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"status": "error", "message": "اسم المستخدم وكلمة المرور مطلوبان"}), 400

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"status": "error", "message": "اسم المستخدم غير مسجل"}), 401

    stored_password_hash = user[2]
    input_password_hash = hash_password(password)

    if hmac.compare_digest(stored_password_hash, input_password_hash):
        token = generate_jwt(user[0], user[1])
        return jsonify({"status": "success", "message": "تم تسجيل الدخول بنجاح", "token": token}), 200
    else:
        return jsonify({"status": "error", "message": "كلمة المرور غير صحيحة"}), 401

# مسارات إدارة المخزن (Inventory)
@app.route('/api/inventory', methods=['POST'])
def add_product():
    data = request.get_json() or {}
    name = data.get('name')
    quantity = data.get('quantity')
    price = data.get('price')
    
    if not name or quantity is None or price is None:
        return jsonify({"status": "error", "message": "جميع الحقول مطلوبة"}), 400
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO inventory (name, quantity, price) VALUES (?, ?, ?)', (name, quantity, price))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": "تم إضافة المنتج بنجاح"}), 200

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, quantity, price FROM inventory')
    rows = cursor.fetchall()
    conn.close()
    
    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "quantity": row[2],
            "price": row[3]
        })
        
    return jsonify({"status": "success", "products": products}), 200

@app.route('/api/inventory/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM inventory WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": "تم حذف المنتج بنجاح"}), 200
    
    
