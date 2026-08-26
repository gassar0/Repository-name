from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "smart_store_secret_key_2026"

# إعداد قاعدة البيانات محلياً والجداول الأساسية
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')
    # إضافة منتجات تجريبية لو الجدول فاضي
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO products (name, price) VALUES ('منتج تجريبي 1', 50.0)")
        cursor.execute("INSERT INTO products (name, price) VALUES ('منتج تجريبي 2', 100.0)")
    conn.commit()
    conn.close()

# الصفحة الرئيسية (عرض المنتجات والتحكم للمستخدم المسجل)
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', products=products, username=session['username'])

# صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['username'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error="خطأ في اسم المستخدم أو كلمة المرور!")
    return render_template('login.html')

# صفحة إنشاء حساب جديد
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except:
            return render_template('register.html', error="اسم المستخدم مستخدم مسبقاً!")
    return render_template('register.html')

# إضافة منتج جديد للمتجر
@app.route('/add-product', methods=['POST'])
def add_product():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    name = request.form.get('name')
    price = request.form.get('price')
    
    if name and price:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO products (name, price) VALUES (?, ?)', (name, float(price)))
        conn.commit()
        conn.close()
        
    return redirect(url_for('index'))

# تصدير البيانات إلى ملف CSV
@app.route('/export-csv')
def export_csv():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    rows = cursor.fetchall()
    conn.close()
    
    csv_data = "ID,Name,Price (SAR)\n"
    for row in rows:
        csv_data += f"{row[0]},{row[1]},{row[2]}\n"
        
    response = make_response(csv_data.encode('utf-8'))
    response.headers["Content-Disposition"] = "attachment; filename=products.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

# معالج الدفع عبر بوابة ميسر (Moyasar API Integration)
@app.route('/create-payment', methods=['POST'])
def create_payment():
    try:
        data = request.json or {}
        amount = data.get('amount')
        
        moyasar_url = "https://api.moyasar.com/v1/payments"
        api_key = "sk_test_L2TWqryWAP3MPr..."
        
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
        return jsonify({"error": str(e)}), 500

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
