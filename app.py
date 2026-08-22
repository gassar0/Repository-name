from flask import Flask, jsonify, request
import sqlite3
import hashlib
import hmac
import base64
import time
import os
import json

app = Flask(__name__)
SECRET_KEY = "super-secret-jwt-key-2026"

def hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'salt_2026', 100000).hex()

def generate_jwt(user_id: int, username: str) -> str:
    header = json.dumps({"alg": "HS256", "typ": "JWT"}).encode('utf-8')
    payload = json.dumps({"user_id": user_id, "username": username, "exp": int(time.time()) + 3600}).encode('utf-8')
    b64_header = base64.urlsafe_b64encode(header).decode('utf-8').rstrip('=')
    b64_payload = base64.urlsafe_b64encode(payload).decode('utf-8').rstrip('=')
    sig_input = f"{b64_header}.{b64_payload}".encode('utf-8')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), sig_input, hashlib.sha256).digest()
    b64_sig = base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('=')
    return f"{b64_header}.{b64_payload}.{b64_sig}"

def init_db():
    conn = sqlite3.connect('database.db')
    with conn:
        conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, name TEXT, price REAL, stock INTEGER)')
    conn.close()

init_db()

@app.route('/')
def home():
    return jsonify({"status": "online", "message": "السيرفر يعمل بنجاح على الاستضافة السحابية!"})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    conn = sqlite3.connect('database.db')
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                           (data.get('username'), hash_password(data.get('password', ''))))
            return jsonify({"status": "success", "message": "تم إنشاء الحساب!"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status": "fail", "message": "المستخدم موجود مسبقاً"}), 400
    finally:
        conn.close()

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
@app.route('/api/auth/login', methods=['POST'])
def login():
    # ... كود تسجيل الدخول الخاص بك ...

# 1. ضع المسار المحمي هنا أولاً
@app.route('/api/protected', methods=['GET'])
@jwt_required()
def protected_route():
    current_user = get_jwt_identity()
    return {
        "status": "success",
        "message": f"لقد وصلت إلى مسار محمي بنجاح، مرحباً {current_user}"
    }, 200

# 2. اجعل جملة التشغيل في النهاية تماماً ولا تكتب تحتها شيئاً
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    

    
