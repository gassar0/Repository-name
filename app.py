from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "your_smart_store_secret_key"

# إعداد قاعدة البيانات محلياً
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
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html') if 'username' in session else redirect(url_for('login'))

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
        return "خطأ في اسم المستخدم أو كلمة المرور!"
    return "صفحة تسجيل الدخول (Login)"

# صفحة التسجيل (Register)
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
            return "اسم المستخدم موجود مسبقاً!"
    return "صفحة إنشاء حساب جديد (Register)"

# تصدير البيانات إلى CSV (كما ظهرت في الكود لديك)
@app.route('/export-csv')
def export_csv():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    rows = cursor.fetchall()
    conn.close()
    
    csv_data = "ID,Name,Price\n"
    for row in rows:
        csv_data += f"{row[0]},{row[1]},{row[2]}\n"
        
    response = make_response(csv_data.encode('utf-8'))
    response.headers["Content-Disposition"] = "attachment; filename=products.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

# معالج الدفع عبر ميسر (Moyasar Integration)
@app.route('/create-payment', methods=['POST'])
def create_payment():
    try:
        data = request.json or {}
        amount = data.get('amount')
        
        moyasar_url = "https://api.moyasar.com/v1/payments"
        api_key = "sk_test_L2TWqryWAP3Mr..."
        
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

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
