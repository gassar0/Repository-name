import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, make_response
import requests

app = Flask(__name__)
app.secret_key = 'smart_store_secret_key_12345'

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
                vendor TEXT
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
            <!-- Add Product Form -->
            <div class="bg-white p-6 rounded-xl shadow-md h-fit">
                <h2 class="text-xl font-bold mb-4 text-gray-800">➕ إضافة منتج جديد</h2>
                <form action="/add-product" method="POST" class="space-y-4">
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
                    <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-bold">إضافة المنتج</button>
                </form>
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
                                        <h3 class="font-bold text-lg text-gray-800">{{ product[1] }}</h3>
                                        <p class="text-gray-600 text-sm">البائع: {{ product[4] or 'غير متوفر' }}</p>
                                        <p class="text-blue-600 font-bold mt-2 text-xl">{{ product[3] }} ر.س</p>
                                        <p class="text-gray-500 text-xs mt-1">الكمية المتاحة: {{ product[2] }}</p>
                                    </div>
                                    <div class="flex gap-2 mt-4">
                                        <a href="/add-to-cart/{{ product[0] }}" class="flex-1 text-center bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition text-sm font-semibold">أضف للسلة</a>
                                        <a href="/edit-product/{{ product[0] }}" class="bg-amber-500 text-white px-3 py-2 rounded-lg hover:bg-amber-600 transition text-sm font-semibold">تعديل</a>
                                        <a href="/delete-product/{{ product[0] }}" onclick="return confirm('هل أنت متأكد من حذف هذا المنتج؟');" class="bg-red-500 text-white px-3 py-2 rounded-lg hover:bg-red-600 transition text-sm font-semibold">حذف</a>
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
        <form method="POST" class="space-y-4">
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

@app.route('/')
def index():
    try:
        search_query = request.args.get('q', '').strip()
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        
        if search_query:
            cursor.execute('SELECT * FROM products WHERE name LIKE ? OR vendor LIKE ?', 
                           (f'%{search_query}%', f'%{search_query}%'))
        else:
            cursor.execute('SELECT * FROM products')
            
        products = cursor.fetchall()
        conn.close()
        
        cart = session.get('cart', {})
        if not isinstance(cart, dict):
            cart = {}
        cart_count = sum(int(v) for v in cart.values() if str(v).isdigit())
        
        return render_template_string(INDEX_TEMPLATE, products=products, cart_count=cart_count, search_query=search_query)
    except Exception as e:
        return f"حدث خطأ في الصفحة الرئيسية: {str(e)}"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
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
        username = request.form.get('username')
        password = request.form.get('password')
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
    try:
        name = request.form.get('name')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        vendor = request.form.get('vendor')
        
        conn = sqlite3.connect('store.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO products (name, quantity, price, vendor) VALUES (?, ?, ?, ?)', 
                       (name, quantity, price, vendor))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    except Exception as e:
        return f"خطأ أثناء إضافة المنتج: {str(e)}"

@app.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        vendor = request.form.get('vendor')
        
        cursor.execute('UPDATE products SET name = ?, quantity = ?, price = ?, vendor = ? WHERE id = ?',
                       (name, quantity, price, vendor, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    if not product:
        return "المنتج غير موجود!"
    return render_template_string(EDIT_TEMPLATE, product=product)

@app.route('/delete-product/<int:product_id>')
def delete_product(product_id):
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
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            if product:
                item_total = product[3] * int(quantity)
                total_price += item_total
                cart_items.append({
                    'id': product[0],
                    'name': product[1],
                    'price': product[3],
                    'quantity': quantity,
                    'total': item_total,
                    'vendor': product[4]
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

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
