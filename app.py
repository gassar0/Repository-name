import requests
import csv
import io
import sqlite3
from flask import Flask, jsonify, make_response, render_template, request, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'smart_warehouse_secret_key_2026'

def init_db():
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            vendor TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('store.html')

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"message": "يرجى إدخال البريد الإلكتروني وكلمة المرور"}), 400

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
        conn.commit()
        conn.close()

        session['user_email'] = email
        return jsonify({"message": "تم إنشاء الحساب بنجاح"})
    except sqlite3.IntegrityError:
        return jsonify({"message": "البريد الإلكتروني مستخدم مسبقاً"}), 400
    except Exception as e:
        return jsonify({"message": f"حدث خطأ: {str(e)}"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"message": "يرجى إدخال البريد الإلكتروني وكلمة المرور"}), 400

        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session['user_email'] = email
            return jsonify({"message": "تم تسجيل الدخول بنجاح"})
        else:
            return jsonify({"message": "البيانات غير صحيحة"}), 401
    except Exception as e:
        return jsonify({"message": f"حدث خطأ: {str(e)}"}), 500

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user_email' in session:
        return jsonify({"logged_in": True, "email": session['user_email']})
    return jsonify({"logged_in": False})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_email', None)
    return jsonify({"message": "تم تسجيل الخروج بنجاح"})

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, quantity, price, vendor FROM products")
    rows = cursor.fetchall()
    conn.close()
    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "quantity": row[2],
            "price": row[3],
            "vendor": row[4]
        })
    return jsonify(products)

@app.route('/api/products', methods=['POST'])
def add_product():
    if 'user_email' not in session:
        return jsonify({"message": "أولاً لإضافة منتجات"}), 401
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name')
        quantity = data.get('quantity', 0)
        price = data.get('price', 0.0)
        vendor = data.get('vendor', '')

        if not name:
            return jsonify({"message": "أدخل اسم المنتج"}), 400

        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, quantity, price, vendor) VALUES (?, ?, ?, ?)", (name, quantity, price, vendor))
        conn.commit()
        conn.close()
        return jsonify({"message": "تم إضافة المنتج بنجاح"})
    except Exception as e:
        return jsonify({"message": f"حدث خطأ: {str(e)}"}), 500

@app.route('/api/export-excel', methods=['GET'])
def export_excel():
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, quantity, price, vendor FROM products")
    rows = cursor.fetchall()
    conn.close()

    csv_data = "اسم المنتج,الكمية,السعر (ر.س),البائع\n"
    for row in rows:
        csv_data += f"{row[0]},{row[1]},{row[2]},{row[3]}\n"

    response = make_response(csv_data.encode('utf-8-sig'))
    response.headers["Content-Disposition"] = "attachment; filename=products.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return response

@app.route('/create-payment', methods=['POST'])
def create_payment():
    try:
        data = request.json or {}
        amount = data.get('amount')
        
        moyasar_url = "https://api.moyasar.com/v1/payments"
        api_key = "sk_live_QmHZnPZeYcQeupUZqbLHKYftGE3AjqVpQbnMik7Y"
        
        payload = {
            "amount": int(float(amount) * 100),
            "currency": "SAR",
            "description": "Smart Store Order"
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(moyasar_url, json=payload, headers=headers, auth=(api_key, ""))
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

        # ضع مفتاح ميسر الفعلي الكامل هنا
api_key = "sk_live_QmHZnPZeYcQeupUZqbLHKYftGE3AjqVpQbnMik7Y"
        
        
        payload = {
            "amount": int(float(amount) * 100),
            "currency": "SAR",
            "description": "Smart Store Order"
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(moyasar_url, json=payload, headers=headers, auth=(api_key, ""))
        
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
