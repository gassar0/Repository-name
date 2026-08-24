from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import sqlite3
import hashlib

app = Flask(__name__)

# إعدادات الـ JWT (سِر تشفير التوكن)
app.config["JWT_SECRET_KEY"] = "super-secret-key-change-this"  # يمكنك تغييرها لاحقاً
jwt = JWTManager(app)

# دالة لإنشاء الاتصال بقاعدة البيانات
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# تهيئة قاعدة البيانات والجداول
def init_db():
    conn = get_db_connection()
    # جدول المستخدمين
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # جدول المخزن (مربوط باسم المستخدم)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            username TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# تشغيل إنشاء الجداول أول ما السيرفر يقوم
init_db()

# ==================== مسارات المصادقة (Auth) ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"status": "error", "message": "اسم المستخدم وكلمة المرور مطلوبان"}), 400

    username = data['username']
    password = hashlib.sha256(data['password'].encode()).hexdigest()

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": "اسم المستخدم مستخدم من قبل"}), 400
    
    conn.close()
    return jsonify({"status": "success", "message": "تم تسجيل المستخدم بنجاح"}), 200

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"status": "error", "message": "اسم المستخدم وكلمة المرور مطلوبان"}), 400

    username = data['username']
    password = hashlib.sha256(data['password'].encode()).hexdigest()

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    conn.close()

    if user is None:
        return jsonify({"status": "error", "message": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401

    # إنشاء الـ Token وإرجاعه للمستخدم
    access_token = create_access_token(identity=username)
    return jsonify({"status": "success", "message": "تم تسجيل الدخول بنجاح", "token": access_token}), 200

# ==================== مسارات المخزن (Inventory - المحمية) ====================

# إضافة منتج (محمي بالـ Token)
@app.route('/api/inventory', methods=['POST'])
@jwt_required()
def add_product():
    current_user = get_jwt_identity() # معرفة المستخدم الحالي من الـ Token
    data = request.get_json()
    
    if not data or 'name' not in data or 'quantity' not in data or 'price' not in data:
        return jsonify({"status": "error", "message": "بيانات المنتج غير مكتملة"}), 400

    name = data['name']
    quantity = data['quantity']
    price = data['price']

    conn = get_db_connection()
    conn.execute('INSERT INTO inventory (name, quantity, price, username) VALUES (?, ?, ?, ?)',
                 (name, quantity, price, current_user))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "تم إضافة المنتج بنجاح بواسطة " + current_user}), 201

# عرض المنتجات الخاصة بالمستخدم أو كل المنتجات (محمي بالـ Token)
@app.route('/api/inventory', methods=['GET'])
@jwt_required()
def get_products():
    current_user = get_jwt_identity()
    conn = get_db_connection()
    # جلب منتجات المستخدم الحالي فقط
    products = conn.execute('SELECT * FROM inventory WHERE username = ?', (current_user,)).fetchall()
    conn.close()

    product_list = []
    for p in products:
        product_list.append({
            "id": p["id"],
            "name": p["name"],
            "quantity": p["quantity"],
            "price": p["price"]
        })

    return jsonify({"status": "success", "products": product_list}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
