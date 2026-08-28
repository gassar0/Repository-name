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
        # التأكد من وجود عمود الصورة لو القاعدة قديمة
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
    <title>المتجر الذكي - Smart Store</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 font-sans">
    <nav class="bg-blue-600 text-white shadow-lg">
        <div class="container mx-auto px-4 py-4 flex justify-between items-center">
            <a href="/" class="text-2xl font-bold">🛒 المتجر الذكي</a>
            <div class="flex items-center gap-4">
                <a href="/cart" class="bg-blue-700 px-4 py-2 rounded-lg hover:bg-blue-800 transition">السلة ({{ cart_count }})</a>
                <a href="/export-csv" class="bg-green-600 px-4 py-2 rounded-lg hover:bg-green-700 transition">تصدير CSV</a>
                {% if is_admin %}
                    <a href="/orders" class="bg-purple-600 px-4 py-2 rounded-lg hover:bg-purple-700 transition">الطلبات</a>
                {% endif %}
                {% if session.get('username') %}
                    <span class="font-semibold">أهلاً، {{ session['username'] }}</span>
                    <a href="/logout" class="bg-red-500 px-3 py-1 rounded hover:bg-red-600 transition">خروج</a>
                {% else %}
                    <a href="/login" class="bg-white text-blue-600 px-4 py-2 rounded-lg font-semibold hover:bg-gray-100 transition">دخول</a>
                    <a href="/register" class="bg-blue-500 px-4 py-2 rounded-lg hover:bg-blue-600 transition">حساب جديد</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="container mx-auto px-4 py-8">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
            <!-- Add Product Form (Admin Only) -->
            <div class="bg-white p-6 rounded-xl shadow-md h-fit">
                <h2 class="text-xl font-bold mb-4 text-gray-800">➕ إضافة منتج جديد</h2>
                {% if is_admin %}
                    <form action="/add-product" method="POST" enctype="multipart/form-data" class="space-y-4">
                        <div>
                            <label class="block text-gray-700 mb-1">اسم المنتج</label>
                            <input type="text" name="name" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-gray-700 mb-1">الكمية</label>
                            <input type="number" name="quantity" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-gray-700 mb-1">السعر (ر.س)</label>
                            <input type="number" step="0.01" name="price" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-gray-700 mb-1">البائع</label>
                            <input type="text" name="vendor" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-gray-700 mb-1">صورة المنتج</label>
                            <input type="file" name="image" accept="image/*" class="w-full border rounded-lg px-3 py-2 text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
                        </div>
                        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-bold">إضافة المنتج</button>
                    </form>
                {% else %}
                    <div class="bg-blue-50 border border-blue-200 text-blue-800 p-4 rounded-lg text-center text-sm">
                        عذراً، لوحة إضافة المنتجات مخصصة للمدير (الأدمن) فقط.
                    </div>
                {% endif %}
            </div>

            <!-- Products List & Search -->
            <div class="md:col-span-2 space-y-6">
                <!-- Search Bar -->
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <form method="GET" action="/" class="flex gap-2">
                        <input type="text" name="q" value="{{ search_query }}" placeholder="ابحث عن اسم المنتج أو البائع..." class="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <button type="submit" class="bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700 transition font-semibold">بحث</button>
                        {% if search_query %}
                            <a href="/" class="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition flex items-center font-semibold">إلغاء</a>
                        {% endif %}
                    </form>
                </div>

                <div class="bg-white p-6 rounded-xl shadow-md">
                    <h2 class="text-xl font-bold mb-4 text-gray-800">📦 المنتجات المتوفرة</h2>
                    {% if products %}
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {% for product in products %}
                                <div class="border rounded-lg p-4 flex flex-col justify-between bg-gray-50 hover:shadow-md transition">
                                    <div>
                                        {% if product[5] %}
                                            <img src="{{ url_for('static', filename='uploads/' + product[5]) }}" alt="{{ product[1] }}" class="w-full h-40 object-cover rounded-lg mb-3">
                                        {% else %}
                                            <div class="w-full h-40 bg-gray-200 rounded-lg mb-3 flex items-center justify-center text-gray-400 text-sm">لا توجد صورة</div>
                                        {% endif %}
                                        <h3 class="font-bold text-lg text-gray-800">{{ product[1] }}</h3>
                                        <p class="text-gray-600 text-sm">البائع: {{ product[4] or 'غير متوفر' }}</p>
                                        <p class="text-blue-600 font-bold mt-2 text-xl">{{ product[3] }} ر.س</p>
                                        <p class="text-gray-500 text-xs mt-1">الكمية المتاحة: {{ product[2] }}</p>
                                    </div>
                                    <div class="flex gap-2 mt-4">
                                        <a href="/add-to-cart/{{ product[0] }}" class="flex-1 text-center bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition text-sm font-semibold">أضف للسلة</a>
                                        {% if is_admin %}
                                            <a href="/edit-product/{{ product[0] }}" class="bg-amber-500 text-white px-3 py-2 rounded-lg hover:bg-amber-600 transition text-sm font-semibold">تعديل</a>
                                            <a href="/delete-product/{{ product[0] }}" onclick="return confirm('هل أنت متأكد من حذف هذا المنتج؟');" class="bg-red-500 text-white px-3 py-2 rounded-lg hover:bg-red-600 transition text-sm font-semibold">حذف</a>
                                        {% endif %}
                                    </div>
                                </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <p class="text-gray-500 text-center py-8">لا توجد منتجات مطابقة للبحث أو مضافة حتى الآن.</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
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
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center h-screen">
    <div class="bg-white p-8 rounded-xl shadow-md w-full max-w-md">
        <h2 class="text-2xl font-bold mb-6 text-center text-blue-600">تسجيل الدخول</h2>
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-gray-700 mb-1">اسم المستخدم</label>
                <input type="text" name="username" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <div>
                <label class="block text-gray-700 mb-1">كلمة المرور</label>
                <input type="password" name="password" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-bold">دخول</button>
        </form>
        <p class="text-center mt-4 text-gray-600">ليس لديك حساب؟ <a href="/register" class="text-blue-600 font-bold hover:underline">سجل الآن</a></p>
        <p class="text-center mt-2"><a href="/" class="text-gray-500 text-sm hover:underline">العودة للرئيسية</a></p>
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
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center h-screen">
    <div class="bg-white p-8 rounded-xl shadow-md w-full max-w-md">
        <h2 class="text-2xl font-bold mb-6 text-center text-blue-600">إنشاء حساب جديد</h2>
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-gray-700 mb-1">اسم المستخدم</label>
                <input type="text" name="username" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <div>
                <label class="block text-gray-700 mb-1">كلمة المرور</label>
                <input type="password" name="password" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-bold">تسجيل</button>
        </form>
        <p class="text-center mt-4 text-gray-600">لديك حساب بالفعل؟ <a href="/login" class="text-blue-600 font-bold hover:underline">سجل دخولك</a></p>
        <p class="text-center mt-2"><a href="/" class="text-gray-500 text-sm hover:underline">العودة للرئيسية</a></p>
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
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center h-screen">
    <div class="bg-white p-8 rounded-xl shadow-md w-full max-w-md">
        <h2 class="text-2xl font-bold mb-6 text-center text-blue-600">✏️ تعديل بيانات المنتج</h2>
        <form method="POST" enctype="multipart/form-data" class="space-y-4">
            <div>
                <label class="block text-gray-700 mb-1">اسم المنتج</label>
                <input type="text" name="name" value="{{ product[1] }}" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <div>
                <label class="block text-gray-700 mb-1">الكمية</label>
                <input type="number" name="quantity" value="{{ product[2] }}" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <div>
                <label class="block text-gray-700 mb-1">السعر (ر.س)</label>
                <input type="number" step="0.01" name="price" value="{{ product[3] }}" required class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <div>
                <label class="block text-gray-700 mb-1">البائع</label>
                <input type="text" name="vendor" value="{{ product[4] or '' }}" class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <div>
                <label class="block text-gray-700 mb-1">تحديث صورة المنتج (اختياري)</label>
                <input type="file" name="image" accept="image/*" class="w-full border rounded-lg px-3 py-2 text-sm text-gray-500">
            </div>
            <div class="flex gap-2 pt-2">
                <button type="submit" class="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-bold">حفظ التعديلات</button>
                <a href="/" class="bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400 transition text-center flex items-center justify-center font-semibold">إلغاء</a>
            </div>
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
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 font-sans">
    <nav class="bg-blue-600 text-white shadow-lg">
        <div class="container mx-auto px-4 py-4 flex justify-between items-center">
            <a href="/" class="text-2xl font-bold">🛒 المتجر الذكي</a>
            <a href="/" class="bg-blue-700 px-4 py-2 rounded-lg hover:bg-blue-800 transition">العودة للمتجر</a>
        </div>
    </nav>

    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <h1 class="text-2xl font-bold mb-6 text-gray-800">🛍️ سلة المشتريات</h1>
        {% if cart_items %}
            <div class="bg-white rounded-xl shadow-md overflow-hidden mb-6">
                <table class="w-full text-right border-collapse">
                    <thead>
                        <tr class="bg-gray-100 border-b">
                            <th class="p-4">المنتج</th>
                            <th class="p-4">السعر</th>
                            <th class="p-4">الكمية</th>
                            <th class="p-4">الإجمالي</th>
                            <th class="p-4">إجراء</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in cart_items %}
                            <tr class="border-b hover:bg-gray-50">
                                <td class="p-4 font-semibold">{{ item.name }}</td>
                                <td class="p-4">{{ item.price }} ر.س</td>
                                <td class="p-4">{{ item.quantity }}</td>
                                <td class="p-4 font-bold text-blue-600">{{ item.total }} ر.س</td>
                                <td class="p-4">
                                    <a href="/remove-from-cart/{{ item.id }}" class="text-red-500 hover:text-red-700 font-bold">حذف</a>
                                </td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            <div class="bg-white p-6 rounded-xl shadow-md flex justify-between items-center">
                <div class="text-xl font-bold text-gray-800">
                    المجموع الكلي: <span class="text-blue-600">{{ total_price }} ر.س</span>
                </div>
                <button onclick="payWithMoyasar({{ total_price }})" class="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition font-bold text-lg">إتمام الدفع عبر ميسر</button>
            </div>
        {% else %}
            <div class="bg-white p-12 rounded-xl shadow-md text-center">
                <p class="text-gray-500 text-lg mb-4">سلة المشتريات فارغة حالياً.</p>
                <a href="/" class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition font-bold">تصفح المنتجات</a>
            </div>
        {% endif %}
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
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 flex items-center justify-center h-screen">
    <div class="bg-white p-8 rounded-xl shadow-md w-full max-w-md text-center">
        <div class="text-green-500 text-6xl mb-4">✅</div>
        <h2 class="text-2xl font-bold mb-2 text-gray-800">تمت عملية الدفع بنجاح!</h2>
        <p class="text-gray-600 mb-6">شكراً لك، تم تسجّيل طلبك ومحتوياته وحفظه بنظام المتجر.</p>
        <p class="text-sm text-gray-500 mb-6">رقم عملية الدفع: <span class="font-mono font-bold">{{ payment_id }}</span></p>
        <a href="/" class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition font-bold block">العودة للمتجر الرئيسي</a>
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
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 font-sans">
    <nav class="bg-blue-600 text-white shadow-lg">
        <div class="container mx-auto px-4 py-4 flex justify-between items-center">
            <a href="/" class="text-2xl font-bold">🛒 المتجر الذكي</a>
            <a href="/" class="bg-blue-700 px-4 py-2 rounded-lg hover:bg-blue-800 transition">العودة للمتجر</a>
        </div>
    </nav>

    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <h1 class="text-2xl font-bold mb-6 text-gray-800">📋 سجل الطلبات وتفاصيلها (لوحة المدير)</h1>
        {% if orders %}
            <div class="space-y-6">
                {% for order in orders %}
                    <div class="bg-white rounded-xl shadow-md p-6 border border-gray-100">
                        <div class="flex justify-between items-center border-b pb-4 mb-4">
                            <div>
                                <span class="text-lg font-bold text-blue-600">طلب #{{ order.id }}</span>
                                <span class="text-gray-500 text-sm mr-4">المستخدم: {{ order.username }}</span>
                            </div>
                            <div class="text-left">
                                <span class="font-bold text-gray-800 text-lg">{{ order.total_amount }} ر.س</span>
                                <p class="text-xs text-gray-400">{{ order.created_at }}</p>
                            </div>
                        </div>
                        <div class="mb-4">
                            <h4 class="text-sm font-bold text-gray-700 mb-2">المنتجات المطلوبة:</h4>
                            <ul class="bg-gray-50 rounded-lg p-3 space-y-2">
                                {% for item in order.items %}
                                    <li class="flex justify-between text-sm text-gray-700 border-b pb-1 last:border-0">
                                        <span>{{ item[0] }} (الكمية: {{ item[2] }})</span>
                                        <span class="font-semibold">{{ item[1] * item[2] }} ر.س</span>
                                    </li>
                                {% endfor %}
                            </ul>
                        </div>
                        <div class="text-xs text-gray-500 font-mono">
                            رقم عملية الدفع: {{ order.payment_id }}
                        </div>
                    </div>
                {% endfor %}
            </div>
        {% else %}
            <div class="bg-white p-12 rounded-xl shadow-md text-center">
                <p class="text-gray-500 text-lg">لا توجد طلبات مسجلة حتى الآن.</p>
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
        search_query = request.args.get('q', '').strip()
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        
        if search_query:
            cursor.execute('SELECT id, name, quantity, price, vendor, image FROM products WHERE name LIKE ? OR vendor LIKE ?', 
                           (f'%{search_query}%', f'%{search_query}%'))
        else:
            cursor.execute('SELECT id, name, quantity, price, vendor, image FROM products')
            
        products = cursor.fetchall()
        conn.close()
        
        cart = session.get('cart', {})
        if not isinstance(cart, dict):
            cart = {}
        cart_count = sum(int(v) for v in cart.values() if str(v).isdigit())
        
        is_admin = check_admin()
        
        return render_template_string(INDEX_TEMPLATE, products=products, cart_count=cart_count, search_query=search_query, is_admin=is_admin)
    except Exception as e:
        return f"حدث خطأ في الصفحة الرئيسية: {str(e)}"

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
        return f"خطأ أثناء إضافة المنتج: {str(e)}"

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
        
        image_filename = request.form.get('existing_image')
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
        return f"خطأ أثناء حذف المنتج: {str(e)}"

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
                    'total': item_total,
                    'vendor': product[3]
                })
                
        conn.close()
        return render_template_string(CART_TEMPLATE, cart_items=cart_items, total_price=total_price)
    except Exception as e:
        return f"خطأ في عرض السلة: {str(e)}"

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
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(moyasar_url, json=payload, headers=headers, auth=(api_key, ""))
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
        return "فشلت عملية الدفع أو تم إلغاؤها من قبل البنك."

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
