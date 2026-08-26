from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, make_response
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "smart_store_secret_key_2026"

# إعداد قاعدة البيانات والجداول
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
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO products (name, price) VALUES ('منتج تجريبي 1', 50.0)")
        cursor.execute("INSERT INTO products (name, price) VALUES ('منتج تجريبي 2', 100.0)")
    conn.commit()
    conn.close()

# تشغيل قاعدة البيانات فوراً عند بدء تشغيل التطبيق على السيرفر
init_db()

# الصفحة الرئيسية للمتجر ودفع ميسر
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    conn.close()
    
    html = '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>المتجر الذكي - Smart Store</title>
        <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
        <style>
            body { font-family: Tahoma, sans-serif; background: #f4f7f6; padding: 20px; text-align: center; }
            .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            h2 { color: #333; }
            table { width: 100%; margin-top: 20px; border-collapse: collapse; }
            th, td { padding: 10px; border: 1px solid #ddd; }
            th { background: #007bff; color: white; }
            .btn { background: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 10px; }
            .btn-danger { background: #dc3545; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>مرحباً بك يا, {{ username }} 👋</h2>
            <a href="/export-csv" class="btn">تصدير المنتجات CSV 📊</a>
            <a href="/logout" class="btn btn-danger">تسجيل الخروج 🚪</a>
            
            <h3>قائمة المنتجات</h3>
            <table>
                <tr><th>الرقم</th><th>اسم المنتج</th><th>السعر (ر.س)</th><th>الإجراء</th></tr>
                {% for p in products %}
                <tr>
                    <td>{{ p[0] }}</td>
                    <td>{{ p[1] }}</td>
                    <td>{{ p[2] }}</td>
                    <td><button class="btn" onclick="pay({{ p[2] }})">ادفع الآن</button></td>
                </tr>
                {% endfor %}
            </table>
        </div>
        <script>
            function pay(amount) {
                axios.post('/create-payment', { amount: amount })
                .then(response => {
                    if(response.data.url) {
                        window.location.href = response.data.url;
                    } else {
                        alert("حدث خطأ في إنشاء الدفع: " + JSON.stringify(response.data));
                    }
                })
                .catch(err => alert("خطأ في الاتصال: " + err));
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, products=products, username=session['username'])

# صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
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
        error = "خطأ في اسم المستخدم أو كلمة المرور!"
        
    html = '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تسجيل الدخول</title>
        <style>
            body { font-family: Tahoma; background: #f4f7f6; padding: 50px; text-align: center; }
            .box { max-width: 400px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; width: 100%; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>تسجيل الدخول للمتجر</h2>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
            <form method="POST">
                <input type="text" name="username" placeholder="اسم المستخدم" required><br>
                <input type="password" name="password" placeholder="كلمة المرور" required><br>
                <button type="submit">دخول</button>
            </form>
            <p>ليس لديك حساب؟ <a href="/register">انشئ حساب جديد</a></p>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, error=error)

# صفحة إنشاء حساب
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ""
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
            error = "اسم المستخدم مستخدم مسبقاً!"
            
    html = '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>إنشاء حساب</title>
        <style>
            body { font-family: Tahoma; background: #f4f7f6; padding: 50px; text-align: center; }
            .box { max-width: 400px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; }
            button { background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; width: 100%; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>إنشاء حساب جديد</h2>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
            <form method="POST">
                <input type="text" name="username" placeholder="اسم المستخدم" required><br>
                <input type="password" name="password" placeholder="كلمة المرور" required><br>
                <button type="submit">تسجيل</button>
            </form>
            <p>لديك حساب بالفعل؟ <a href="/login">سجل دخولك</a></p>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, error=error)

# تصدير CSV
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

# معالج الدفع عبر ميسر
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

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
