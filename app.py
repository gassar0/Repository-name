import os
import sqlite3
import hashlib
import hmac
import time
import base64
import json
from flask import Flask, request, jsonify

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

# حذف الجدول القديم لضمان إنشاء الأعمدة الجديدة صح
cursor.execute('DROP TABLE IF EXISTS users;')

# إنشاء جدول المستخدمين بالأعمدة الكاملة (username و password)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
''')

# إنشاء جدول المخزن
cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        quantity INTEGER
    )
''')

conn.commit()
conn.close()


@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "السيرفر يعمل بنجاح على الاستضافة السحابية!"})
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
        
        return jsonify({"status": "success", "message": "تم تسجيل المستخدم بنجاح!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"status": "error", "message": "الرجاء إدخال اسم المستخدم وكلمة المرور"}), 400
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({"status": "error", "message": "اسم المستخدم غير مسجل"}), 401
        
    stored_password_hash = user[2]
    input_password_hash = hash_password(password)
    
    if hmac.compare_digest(input_password_hash, stored_password_hash):
        token = generate_jwt(user[0], user[1])
        return jsonify({
            "status": "success",
            "message": "تم تسجيل الدخول بنجاح",
            "token": token
        })
    else:
        return jsonify({"status": "error", "message": "كلمة المرور غير صحيحة"}), 401
        

