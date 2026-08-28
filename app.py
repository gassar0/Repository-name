import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, make_response
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)
app.secret_key = 'smart_store_secret_key_12345'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    try:
        conn = sqlite3.connect('store.db')
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
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                vendor TEXT,
                image TEXT
            )
        ''')
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN image TEXT')
        except sqlite3.OperationalError:
            pass

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                total_amount REAL NOT NULL,
                payment_id TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                product_name TEXT,
                price REAL,
                quantity INTEGER,
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Init Error:", e)

init_db()

INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>المتجر الإلكتروني الذكي</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #fff; padding: 15px; margin: 0; box-sizing: border-box; }
        .container { max-width: 900px; margin: auto; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px; }
        h1, h2, h3 { text-align: center; color: #38bdf8; }
        .btn { background-color: #10b981; color: white; padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; text-align: center; font-size: 14px; transition: background 0.2s; white-space: nowrap; }
        .btn:hover { opacity: 0.9; }
        .btn-primary { background-color: #2563eb; }
        .btn-danger { background-color: #ef4444; }
        .btn-warning { background-color: #f59e0b; color: #000; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; background: #0f172a; border: 1px solid #334155; color: white; border-radius: 6px; box-sizing: border-box; }
        
        /* تنسيق الهيدر العلوي */
        .top-bar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }
        .top-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; width: 100%; justify-content: flex-end; }
        @media(min-width: 600px) {
            .top-actions { width: auto; }
        }

        /* تنسيق البحث */
        .search-box-container { display: flex; gap: 10px; margin-bottom: 15px; }
        .search-box-container input { margin: 0; flex: 1; }
        
        /* تنسيق كروت المنتجات */
        .products-grid { display: flex; flex-direction: column; gap: 20px; margin-top: 15px; }
        .product-card { background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 15px; display: flex; flex-direction: column; gap: 12px; }
        .product-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; }
        .product-title { font-size: 18px; font-weight: bold; color: #38bdf8; margin: 0 0 5px 0; }
        .product-price { font-size: 20px; font-weight: bold; color: #60a5fa; white-space: nowrap; }
        .product-info { color: #94a3b8; font-size: 14px; }
        .product-img { width: 100%; height: 200px; object-fit: contain; background: #0b0f19; border-radius: 8px; border: 1px solid #334155; }
        .product-actions { display: flex; gap: 10px; margin-top: 5px; flex-wrap: wrap; }
        .product-actions .btn { flex: 1; min-width: 100px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- هيدر المتجر -->
        <div class="card top-bar">
            <h2 style="margin: 0; font-size: 22px;">🛍️ المتجر الإلكتروني الذكي</h2>
            <div class="top-actions">
                {% if session.get('username') %}
                    <span style="font-size: 14px; color: #38bdf8; word-break: break-all;">أهلاً، {{ session['username'] }}</span>
                    <a href="{{ url_for('logout') }}" class="btn btn-danger" style="padding: 6px 12px; font-size: 13px;">خروج</a>
                {% endif %}
                {% if is_admin %}
                    <a href="{{ url_for('view_orders') }}" class="btn" style="background-color: #9333ea; padding: 8px 12px;">الطلبات</a>
                {% endif %}
                <a href="{{ url_for('export_csv') }}" class="btn" style="background-color: #d97706; padding: 8px 12px;">تصدير CSV</a>
                <a href="{{ url_for('view_cart') }}" class="btn" style="padding: 8px 14px;">🛒 السلة ({{ cart_count }})</a>
            </div>
        </div>

        <!-- المنتجات المتاحة للشراء -->
        <div class="card">
            <h2>🔥 المنتجات المتوفرة</h2>
            <div class="search-box-container">
                <input type="text" id="searchBox" placeholder="🔍 ابحث عن اسم المنتج أو البائع..." onkeyup="filterProducts()">
            </div>
            
            {% if products %}
            <div class="products-grid" id="productsContainer">
                {% for product in products %}
                <div class="product-card" data-name="{{ product[1]|lower }}" data-vendor="{{ product[4]|lower }}">
                    {% if product[5] %}
                        <img src="{{ url_for('static', filename='uploads/' + product[5]) }}" alt="{{ product[1] }}" class="product-img">
                    {% endif %}
                    <div class="product-header">
                        <div>
                            <h3 class="product-title" style="text-align: right;">{{ product[1] }}</h3>
                            <span class="product-info">البائع: {{ product[4] or 'غير متوفر' }} | الكمية المتاحة: {{ product[2] }}</span>
                        </div>
                        <div class="product-price">{{ product[3] }} ر.س</div>
                    </div>
                    
                    <div class="product-actions">
                        <a href="{{ url_for('add_to_cart', product_id=product[0]) }}" class="btn btn-primary">أضف للسلة 🛒</a>
                        {% if is_admin %}
                            <a href="{{ url_for('edit_product', product_id=product[0]) }}" class="btn btn-warning">تعديل</a>
                            <a href="{{ url_for('delete_product', product_id=product[0]) }}" onclick="return confirm('هل أنت متأكد من الحذف؟');" class="btn btn-danger">حذف</a>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p style="text-align: center; color: #94a3b8; margin-top: 20px;">لا توجد منتجات متاحة حالياً.</p>
            {% endif %}
        </div>

        <!-- بوابة إدارة المتجر (للمسؤولين) -->
        <div class="card">
            <h2>🔒 بوابة إدارة المتجر (للمسؤولين)</h2>
            {% if is_admin %}
                <h3 style="color: #38bdf8; margin-top: 20px; text-align: right;">📦 إضافة منتج جديد</h3>
                <form action="{{ url_for('add_product') }}" method="POST" enctype="multipart/form-data">
                    <input type="text" name="name" placeholder="اسم المنتج" required>
                    <input type="number" name="quantity" placeholder="الكمية" required>
                    <input type="number" step="0.01" name="price" placeholder="السعر (ر.س)" required>
                    <input type="text" name="vendor" placeholder="اسم البائع">
                    <div style="margin: 10px 0; text-align: right;">
                        <label style="font-size: 14px; color: #94a3b8; display: block; margin-bottom: 5px;">صورة المنتج:</label>
                        <input type="file" name="image" accept="image/*" style="padding: 6px;">
                    </div>
                    <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 10px;">إضافة المنتج للمخزن</button>
                </form>
            {% else %}
                <div style="display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap;">
                    <a href="{{ url_for('login') }}" class="btn btn-primary" style="flex: 1; min-width: 130px;">تسجيل الدخول</a>
                    <a href="{{ url_for('register') }}" class="btn" style="flex: 1; background-color: #0284c7; min-width: 130px;">إنشاء حساب جديد</a>
                </div>
            {% endif %}
        </div>
    </div>

    <script>
        function filterProducts() {
            let input = document.getElementById('searchBox').value.toLowerCase();
            let cards = document.querySelectorAll('.product-card');
            cards.forEach(card => {
                let name = card.getAttribute('data-name');
                let vendor = card.getAttribute('data-vendor');
                if (name.includes(input) || vendor.includes(input)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #fff; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 15px; box-sizing: border-box; }
        .card { background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 100%; max-width: 400px; box-sizing: border-box; }
        h2 { text-align: center; color: #38bdf8; margin-top: 0; }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #0f172a; border: 1px solid #334155; color: white; border-radius: 6px; box-sizing: border-box; }
        .btn { background-color: #2563eb; color: white; padding: 12px; border: none; border-radius: 6px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; margin-top: 10px; }
        .btn:hover { opacity: 0.9; }
        p { text-align: center; color: #94a3b8; font-size: 14px; }
        a { color: #38bdf8; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="card">
        <h2>تسجيل الدخول</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="اسم المستخدم" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit" class="btn">دخول</button>
        </form>
        <p style="margin-top: 20px;">ليس لديك حساب؟ <a href="/register">سجل الآن</a></p>
        <p><a href="/">العودة للرئيسية</a></p>
    </div>
</body>
</html>
'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>إنشاء حساب جديد</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #fff; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 15px; box-sizing: border-box; }
        .card { background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 100%; max-width: 400px; box-sizing: border-box; }
        h2 { text-align: center; color: #38bdf8; margin-top: 0; }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #0f172a; border: 1px solid #334155; color: white; border-radius: 6px; box-sizing: border-box; }
        .btn { background-color: #2563eb; color: white; padding: 12px; border: none; border-radius: 6px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; margin-top: 10px; }
        .btn:hover { opacity: 0.9; }
        p { text-align: center; color: #94a3b8; font-size: 14px; }
        a { color: #38bdf8; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="card">
        <h2>إنشاء حساب جديد</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="اسم المستخدم" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit" class="btn">تسجيل</button>
        </form>
        <p style="margin-top: 20px;">لديك حساب بالفعل؟ <a href="/login">سجل دخولك</a></p>
        <p><a href="/">العودة للرئيسية</a></p>
    </div>
</body>
</html>
'''

EDIT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تعديل المنتج</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #fff; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 15px; box-sizing: border-box; }
        .card { background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 100%; max-width: 450px; box-sizing: border-box; }
        h2 { text-align: center; color: #38bdf8; margin-top: 0; }
        input { width: 100%; padding: 12px; margin: 8px 0; background: #0f172a; border: 1px solid #334155; color: white; border-radius: 6px; box-sizing: border-box; }
        .btn { background-color: #2563eb; color: white; padding: 12px; border: none; border-radius: 6px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; margin-top: 10px; text-decoration: none; display: inline-block; text-align: center; box-sizing: border-box; }
        .btn-secondary { background-color: #64748b; margin-top: 5px; }
        .btn:hover { opacity: 0.9; }
    </style>
</head>
<body>
    <div class="card">
        <h2>✏️ تعديل بيانات المنتج</h2>
        <form method="POST" enctype="multipart/form-data">
            <label style="font-size: 14px; color: #94a3b8;">اسم المنتج</label>
            <input type="text" name="name" value="{{ product[1] }}" required>
            
            <label style="font-size: 14px; color: #94a3b8;">الكمية</label>
            <input type="number" name="quantity" value="{{ product[2] }}" required>
            
            <label style="font-size: 14px; color: #94a3b8;">السعر (ر.س)</label>
            <input type="number" step="0.01" name="price" value="{{ product[3] }}" required>
            
            <label style="font-size: 14px; color: #94a3b8;">البائع</label>
            <input type="text" name="vendor" value="{{ product[4] or '' }}">
            
            <label style="font-size: 14px; color: #94a3b8;">صورة جديدة (اختياري)</label>
            <input type="file" name="image" accept="image/*">

            <button type="submit" class="btn">حفظ التعديلات</button>
            <a href="/" class="btn btn-secondary">إلغاء</a>
        </form>
    </div>
</body>
</html>
'''

CART_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سلة المشتريات</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #fff; padding: 15px; margin: 0; box-sizing: border-box; }
        .container { max-width: 800px; margin: auto; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px; }
        h1, h2 { text-align: center; color: #38bdf8; }
        .btn { background-color: #10b981; color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; text-align: center; font-size: 14px; }
        .btn-danger { background-color: #ef4444; }
        .btn-primary { background-color: #2563eb; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; overflow-x: auto; display: block; }
        th, td { padding: 12px; text-align: right; border-bottom: 1px solid #334155; white-space: nowrap; }
        th { color: #38bdf8; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <h2 style="margin: 0;">🛒 سلة المشتريات</h2>
            <a href="/" class="btn btn-primary" style="padding: 8px 15px;">العودة للمتجر</a>
        </div>

        <div class="card">
            {% if cart_items %}
                <table>
                    <thead>
                        <tr>
                            <th>المنتج</th>
                            <th>السعر</th>
                            <th>الكمية</th>
                            <th>الإجمالي</th>
                            <th>إجراء</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in cart_items %}
                            <tr>
                                <td>{{ item.name }}</td>
                                <td>{{ item.price }} ر.س</td>
                                <td>{{ item.quantity }}</td>
                                <td style="color: #60a5fa; font-weight: bold;">{{ item.total }} ر.س</td>
                                <td><a href="/remove-from-cart/{{ item.id }}" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">حذف</a></td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>

                <div style="margin-top: 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                    <div style="font-size: 20px; font-weight: bold;">
                        المجموع الكلي: <span style="color: #60a5fa;">{{ total_price }} ر.س</span>
                    </div>
                    <button onclick="payWithMoyasar({{ total_price }})" class="btn" style="background-color: #16a34a; font-size: 16px; padding: 12px 25px;">إتمام الدفع عبر ميسر</button>
                </div>
            {% else %}
                <p style="text-align: center; color: #94a3b8; padding: 20px;">سلة المشتريات فارغة حالياً.</p>
            {% endif %}
        </div>
    </div>

    <script>
        function payWithMoyasar(amount) {
            fetch('/create-payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount: amount })
            })
            .then(res => res.json())
            .then(data => {
                if (data.source && data.source.transaction_url) {
                    window.location.href = data.source.transaction_url;
                } else {
                    alert('خطأ في إنشاء عملية الدفع: ' + JSON.stringify(data));
                }
            })
            .catch(err => alert('حدث خطأ الاتصال: ' + err));
        }
    </script>
</body>
</html>
'''

SUCCESS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نجاح الدفع</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #fff; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 15px; box-sizing: border-box; }
        .card { background: #1e293b; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); text-align: center; max-width: 450px; width: 100%; box-sizing: border-box; }
        .btn { background-color: #2563eb; color: white; padding: 12px 25px; border-radius: 6px; text-decoration: none; display: inline-block; font-weight: bold; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="card">
        <div style="font-size: 50px; margin-bottom: 10px;">✅</div>
        <h2 style="color: #38bdf8; margin-top: 0;">تمت عملية الدفع بنجاح!</h2>
        <p style="color: #94a3b8;">شكراً لك، تم تسجيل طلبك وحفظه بنظام المتجر بنجاح.</p>
        <p style="font-size: 13px; color: #64748b; font-family: monospace;">رقم العملية: {{ payment_id }}</p>
        <a href="/" class="btn">العودة للمتجر الرئيسي</a>
    </div>
</body>
</html>
'''

ORDERS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>إدارة الطلبات</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #fff; padding: 15px; margin: 0; box-sizing: border-box; }
        .container { max-width: 800px; margin: auto; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px; }
        h1, h2 { text-align: center; color: #38bdf8; }
        .btn { background-color: #2563eb; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; display: inline-block; font-size: 14px; }
        .order-box { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 15px; margin-bottom: 15px; }
        .order-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 10px; flex-wrap: wrap; gap: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <h2 style="margin: 0;">📋 سجل الطلبات (لوحة المدير)</h2>
            <a href="/" class="btn">العودة للمتجر</a>
        </div>

        {% if orders %}
            <div class="card">
                {% for order in orders %}
                    <div class="order-box">
                        <div class="order-header">
                            <div>
                                <span style="font-weight: bold; color: #38bdf8;">طلب #{{ order.id }}</span>
                                <span style="color: #94a3b8; font-size: 14px; margin-right: 15px;">المستخدم: {{ order.username }}</span>
                            </div>
                            <div style="text-align: left;">
                                <span style="font-weight: bold; color: #60a5fa; font-size: 18px;">{{ order.total_amount }} ر.س</span>
                                <div style="font-size: 12px; color: #64748b;">{{ order.created_at }}</div>
                            </div>
                        </div>
                        <div style="font-size: 14px; color: #cbd5e1;">
                            <strong>المنتجات:</strong>
                            <ul style="margin: 5px 0 0 0; padding-right: 20px;">
                                {% for item in order.items %}
                                    <li>{{ item[0] }} (الكمية: {{ item[2] }}) - <span style="color: #60a5fa;">{{ item[1] * item[2] }} ر.س</span></li>
                                {% endfor %}
                            </ul>
                        </div>
                        <div style="font-size: 11px; color: #64748b; margin-top: 10px; font-family: monospace;">
                            رقم الدفع: {{ order.payment_id }}
                        </div>
                    </div>
                {% endfor %}
            </div>
        {% else %}
            <div class="card">
                <p style="text-align: center; color: #94a3b8;">لا توجد طلبات مسجلة حتى الآن.</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

def check_admin():
    username = str(session.get('username', '')).strip().lower()
    return 'mmm319' in username

@app.route('/')
def index():
    try:
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, quantity, price, vendor, image FROM products')
        products = cursor.fetchall()
        conn.close()
        
        cart = session.get('cart', {})
        if not isinstance(cart, dict):
            cart = {}
        cart_count = sum(int(v) for v in cart.values() if str(v).isdigit())
        
        is_admin = check_admin()
        
        return render_template_string(INDEX_TEMPLATE, products=products, cart_count=cart_count, is_admin=is_admin)
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        try:
            conn = sqlite3.connect('store.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "اسم المستخدم موجود مسبقاً!"
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return "خطأ في اسم المستخدم أو كلمة المرور!"
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/add-product', methods=['POST'])
def add_product():
    if not check_admin():
        return redirect(url_for('login'))
    try:
        name = request.form.get('name')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        vendor = request.form.get('vendor')
        
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
        
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO products (name, quantity, price, vendor, image) VALUES (?, ?, ?, ?, ?)', 
                       (name, quantity, price, vendor, image_filename))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    except Exception as e:
        return f"خطأ أثناء الإضافة: {str(e)}"

@app.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not check_admin():
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        vendor = request.form.get('vendor')
        
        cursor.execute('SELECT image FROM products WHERE id = ?', (product_id,))
        old_img = cursor.fetchone()
        image_filename = old_img[0] if old_img else None

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename

        cursor.execute('UPDATE products SET name = ?, quantity = ?, price = ?, vendor = ?, image = ? WHERE id = ?',
                       (name, quantity, price, vendor, image_filename, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    cursor.execute('SELECT id, name, quantity, price, vendor, image FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    if not product:
        return "المنتج غير موجود!"
    return render_template_string(EDIT_TEMPLATE, product=product)

@app.route('/delete-product/<int:product_id>')
def delete_product(product_id):
    if not check_admin():
        return redirect(url_for('login'))
    try:
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    except Exception as e:
        return f"خطأ في الحذف: {str(e)}"

@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session or not isinstance(session['cart'], dict):
        session['cart'] = {}
    
    cart = session['cart']
    str_id = str(product_id)
    
    if str_id in cart:
        cart[str_id] += 1
    else:
        cart[str_id] = 1
        
    session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    try:
        cart = session.get('cart', {})
        if not isinstance(cart, dict):
            cart = {}
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        
        cart_items = []
        total_price = 0
        
        for product_id, quantity in cart.items():
            cursor.execute('SELECT id, name, price, vendor FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            if product:
                item_total = product[2] * int(quantity)
                total_price += item_total
                cart_items.append({
                    'id': product[0],
                    'name': product[1],
                    'price': product[2],
                    'quantity': quantity,
                    'total': item_total
                })
                
        conn.close()
        return render_template_string(CART_TEMPLATE, cart_items=cart_items, total_price=total_price)
    except Exception as e:
        return f"خطأ في السلة: {str(e)}"

@app.route('/remove-from-cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    str_id = str(product_id)
    if str_id in cart:
        del cart[str_id]
        session['cart'] = cart
    return redirect(url_for('view_cart'))

@app.route('/export-csv')
def export_csv():
    conn = sqlite3.connect('store.db')
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
        callback_url = request.host_url + "payment-callback"
        
        payload = {
            "amount": int(float(amount) * 100),
            "currency": "SAR",
            "description": "Smart Store Order",
            "callback_url": callback_url
        }
        
        response = requests.post(moyasar_url, json=payload, headers={"Content-Type": "application/json"}, auth=(api_key, ""))
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/payment-callback')
def payment_callback():
    payment_id = request.args.get('id')
    status = request.args.get('status')
    
    if status == 'paid':
        try:
            username = session.get('username', 'زائر')
            cart = session.get('cart', {})
            
            conn = sqlite3.connect('store.db')
            cursor = conn.cursor()
            
            total_amount = 0
            order_items_data = []
            
            for product_id, qty in cart.items():
                cursor.execute('SELECT name, price FROM products WHERE id = ?', (product_id,))
                prod = cursor.fetchone()
                if prod:
                    p_name, p_price = prod[0], prod[1]
                    item_total = p_price * int(qty)
                    total_amount += item_total
                    order_items_data.append((p_name, p_price, int(qty)))
            
            cursor.execute('INSERT INTO orders (username, total_amount, payment_id, status) VALUES (?, ?, ?, ?)',
                           (username, total_amount, payment_id, 'paid'))
            order_id = cursor.lastrowid
            
            for item in order_items_data:
                cursor.execute('INSERT INTO order_items (order_id, product_name, price, quantity) VALUES (?, ?, ?, ?)',
                               (order_id, item[0], item[1], item[2]))
                
            conn.commit()
            conn.close()
            session.pop('cart', None)
        except Exception as e:
            print("Order Save Error:", e)
            
        return render_template_string(SUCCESS_TEMPLATE, payment_id=payment_id)
    else:
        return "فشلت عملية الدفع أو تم إلغاؤها."

@app.route('/orders')
def view_orders():
    if not check_admin():
        return redirect(url_for('login'))
    try:
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, total_amount, payment_id, created_at FROM orders ORDER BY id DESC')
        raw_orders = cursor.fetchall()
        
        orders = []
        for row in raw_orders:
            order_id = row[0]
            cursor.execute('SELECT product_name, price, quantity FROM order_items WHERE order_id = ?', (order_id,))
            items = cursor.fetchall()
            orders.append({
                'id': order_id,
                'username': row[1],
                'total_amount': row[2],
                'payment_id': row[3],
                'created_at': row[4],
                'items': items
            })
            
        conn.close()
        return render_template_string(ORDERS_TEMPLATE, orders=orders)
    except Exception as e:
        return f"خطأ في عرض الطلبات: {str(e)}"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
