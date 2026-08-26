import csv
import io
import sqlite3
from flask import Flask, jsonify, make_response, request, render_template

app = Flask(__name__)

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

@app.route('/api/users', methods=['GET'])
def get_users():
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, email FROM users")
    rows = cursor.fetchall()
    conn.close()
    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "email": row[1]
        })
    return jsonify(users)

@app.route('/api/products', methods=['POST'])
def add_product():
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name')
        quantity = data.get('quantity', 0)
        price = data.get('price', 0.0)
        vendor = data.get('vendor', '')
        
        if not name:
            return jsonify({"message": "يرجى إدخال اسم المنتج"}), 400
        
        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, quantity, price, vendor) VALUES (?, ?, ?, ?)", (name, quantity, price, vendor))
        conn.commit()
        conn.close()
        return jsonify({"message": "تم إضافة المنتج بنجاح"})
    except Exception as e:
        return jsonify({"message": f"حدث خطأ: {str(e)}"}), 500

@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name')
        quantity = data.get('quantity', 0)
        price = data.get('price', 0.0)
        vendor = data.get('vendor', '')
        
        if not name:
            return jsonify({"message": "يرجى إدخال اسم المنتج"}), 400
        
        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET name = ?, quantity = ?, price = ?, vendor = ? WHERE id = ?", (name, quantity, price, vendor, id))
        conn.commit()
        conn.close()
        return jsonify({"message": "تم تعديل المنتج بنجاح"})
    except Exception as e:
        return jsonify({"message": f"حدث خطأ: {str(e)}"}), 500

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    try:
        conn = sqlite3.connect("store.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "تم حذف المنتج بنجاح"})
    except Exception as e:
        return jsonify({"message": f"حدث خطأ: {str(e)}"}), 500

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')
    if email == "mmmmm_mmmmm319@yahoo.com":
        return jsonify({"message": "تم تسجيل الدخول بنجاح"})
    return jsonify({"message": "بيانات غير صالحة"}), 401

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
    response.headers["Content-Disposition"] = "attachment; filename=store_report.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



 
  
