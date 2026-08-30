import csv
import io
import sqlite3
from datetime import datetime
from flask import Flask, Response, flash, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = 'smart_store_secret_key_12345'

DB_Name = 'store.db'

def init_db():
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            seller TEXT NOT NULL,
            image TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

COMMON_STYLE = '''
<style>
    body { background-color: #0d1117; color: #e6edf3; font-family: Tahoma, sans-serif; direction: rtl; margin: 0; padding: 20px; }
    .container { max-width: 950px; margin: auto; }
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    h1, h2, h3 { color: #58a6ff; }
    input, select, textarea { width: 100%; padding: 10px; margin: 8px 0; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 6px; box-sizing: border-box; }
    button, .btn { padding: 10px 15px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; text-decoration: none; display: inline-block; text-align: center; }
    .btn-primary { background: #238636; color: #fff; }
    .btn-primary:hover { background: #2ea043; }
    .btn-danger { background: #da3633; color: #fff; }
    .btn-danger:hover { background: #f85149; }
    .btn-warning { background: #d29922; color: #000; }
    .btn-warning:hover { background: #e3b341; }
    .btn-info { background: #1f6feb; color: #fff; }
    .btn-info:hover { background: #388bfd; }
    .flex { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { border: 1px solid #30363d; padding: 10px; text-align: right; }
    th { background: #21262d; color: #58a6ff; }
    .alert { padding: 10px; margin-bottom: 15px; border-radius: 6px; }
    .alert-success { background: #113822; border: 1px solid #238636; color: #3fb950; }
    .alert-danger { background: #3d1214; border: 1px solid #da3633; color: #f85149; }
    .alert-warning { background: #33270a; border: 1px solid #d29922; color: #e3b341; }
    .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 15px; }
    .product-card { background: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 15px; text-align: center; }
    .product-img { width: 100%; height: 160px; object-fit: cover; border-radius: 6px; background: #30363d; margin-bottom: 10px; }
</style>
'''

INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>المتجر الإلكتروني الذكي</title>
    ''' + COMMON_STYLE + '''
</head>
<body>
<div class="container">
    <div class="card flex" style="justify-content: space-between;">
        <div>
            <h2>🛍️ المتجر الإلكتروني الذكي</h2>
            <p style="margin:0; color: #8b949e;">أهلاً، {{ session.get('user_email', 'mmmmm_mmmmm319@yahoo.com') }}</p>
        </div>
        <div class="flex">
            <a href="{{ url_for('cart_view') }}" class="btn btn-info">🛒 السلة ({{ cart_count }})</a>
            <a href="{{ url_for('orders_view') }}" class="btn btn-warning">📦 الطلبات</a>
            <a href="{{ url_for('export_csv') }}" class="btn btn-primary">📁 تصدير CSV</a>
            <a href="{{ url_for('logout') }}" class="btn btn-danger">خروج</a>
        </div>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ 'success' if category == 'success' else ('warning' if category == 'warning' else 'danger') }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <div class="card">
        <form method="GET" action="{{ url_for('index') }}" class="flex">
            <input type="text" name="q" value="{{ request.args.get('q', '') }}" placeholder="🔍 ابحث عن اسم المنتج أو البائع..." style="flex:1; margin:0;">
            <button type="submit" class="btn btn-info">بحث</button>
        </form>
    </div>

    <div class="card">
        <h3>🔥 المنتجات المتوفرة</h3>
        {% if products %}
            <div class="product-grid">
                {% for p in products %}
                <div class="product-card">
                    <img src="{{ p[5] if p[5] else 'https://via.placeholder.com/250x160?text=Product' }}" class="product-img" alt="{{ p[1] }}">
                    <h3 style="margin: 5px 0;">{{ p[1] }}</h3>
                    <p style="margin: 5px 0; color: #8b949e;">البائع: {{ p[4] }} | الكمية المتاحة: {{ p[2] }}</p>
                    <p style="font-size: 1.2em; color: #3fb950; font-weight: bold; margin: 5px 0;">{{ p[3] }} ر.س</p>
                    <div class="flex" style="justify-content: center; margin-top: 10px;">
                        <form action="{{ url_for('add_to_cart', id=p[0]) }}" method="POST" style="margin:0;">
                            <button type="submit" class="btn btn-primary" style="padding: 6px 12px;">أضف للسلة</button>
                        </form>
                        <a href="{{ url_for('edit_product', id=p[0]) }}" class="btn btn-warning" style="padding: 6px 12px;">تعديل</a>
                        <form action="{{ url_for('delete_product', id=p[0]) }}" method="POST" style="margin:0;" onsubmit="return confirm('هل أنت متأكد من الحذف؟');">
                            <button type="submit" class="btn btn-danger" style="padding: 6px 12px;">حذف</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            </div>
        {% else %}
            <p style="text-align: center; color: #8b949e;">لا توجد منتجات متاحة حالياً.</p>
        {% endif %}
    </div>

    <div class="card">
        <h3>🔒 بوابة إدارة المتجر (للمسؤولين)</h3>
        <h4 style="margin-bottom: 5px;">📦 إضافة منتج جديد</h4>
        <form action="{{ url_for('add_product') }}" method="POST">
            <input type="text" name="name" placeholder="اسم المنتج" required>
            <input type="number" name="quantity" placeholder="الكمية" required min="1">
            <input type="number" step="0.01" name="price" placeholder="السعر (ر.س)" required min="0">
            <input type="text" name="seller" placeholder="اسم البائع" value="محمد رجب" required>
            <label style="display:block; margin-top:10px; color:#8b949e;">صورة المنتج (رابط أو مسار):</label>
            <input type="text" name="image" placeholder="مثال: رابط الصورة أو اسم الملف">
            <button type="submit" class="btn btn-primary" style="width:100%; margin-top:10px;">إضافة المنتج للمخزن</button>
        </form>
    </div>
</div>
</body>
</html>
'''

CART_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>سلة المشتريات</title>
    ''' + COMMON_STYLE + '''
</head>
<body>
<div class="container">
    <div class="card flex" style="justify-content: space-between;">
        <h2>🛒 سلة المشتريات</h2>
        <a href="{{ url_for('index') }}" class="btn btn-info">العودة للمتجر</a>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ 'success' if category == 'success' else 'danger' }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <div class="card">
        {% if cart_items %}
            <table>
                <tr>
                    <th>اسم المنتج</th>
                    <th>السعر</th>
                    <th>الكمية</th>
                    <th>الإجمالي</th>
                    <th>إجراء</th>
                </tr>
                {% for item in cart_items %}
                <tr>
                    <td>{{ item.name }}</td>
                    <td>{{ item.price }} ر.س</td>
                    <td>{{ item.quantity }}</td>
                    <td>{{ item.price * item.quantity }} ر.س</td>
                    <td>
                        <form action="{{ url_for('remove_from_cart', id=item.id) }}" method="POST" style="margin:0;">
                            <button type="submit" class="btn btn-danger" style="padding: 4px 8px;">حذف</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
            <h3 style="text-align: left; margin-top: 20px;">الإجمالي الكلي: {{ total_sum }} ر.س</h3>
            
            <form action="{{ url_for('checkout') }}" method="POST" style="margin-top: 20px;">
                <button type="submit" class="btn btn-primary" style="width: 100%; font-size: 1.2em;">💳 إتمام الشراء وتأكيد الطلب</button>
            </form>
        {% else %}
            <p style="text-align: center; color: #8b949e;">سلة المشتريات فارغة حالياً.</p>
        {% endif %}
    </div>
</div>
</body>
</html>
'''

ORDERS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>طلبات العملاء</title>
    ''' + COMMON_STYLE + '''
</head>
<body>
<div class="container">
    <div class="card flex" style="justify-content: space-between;">
        <h2>📦 سجل الطلبات</h2>
        <a href="{{ url_for('index') }}" class="btn btn-info">العودة للمتجر</a>
    </div>

    <div class="card">
        {% if orders %}
            <table>
                <tr>
                    <th>رقم الطلب</th>
                    <th>البريد / العميل</th>
                    <th>اسم المنتج</th>
                    <th>الكمية</th>
                    <th>الإجمالي</th>
                    <th>تاريخ الطلب</th>
                </tr>
                {% for o in orders %}
                <tr>
                    <td>#{{ o[0] }}</td>
                    <td>{{ o[1] }}</td>
                    <td>{{ o[2] }}</td>
                    <td>{{ o[3] }}</td>
                    <td>{{ o[4] }} ر.س</td>
                    <td>{{ o[5] }}</td>
                </tr>
                {% endfor %}
            </table>
        {% else %}
            <p style="text-align: center; color: #8b949e;">لا توجد طلبات مسجلة حتى الآن.</p>
        {% endif %}
    </div>
</div>
</body>
</html>
'''

EDIT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تعديل منتج</title>
    ''' + COMMON_STYLE + '''
</head>
<body>
<div class="container">
    <div class="card">
        <h2>✏️ تعديل المنتج</h2>
        <form method="POST">
            <input type="text" name="name" value="{{ product[1] }}" required placeholder="اسم المنتج">
            <input type="number" name="quantity" value="{{ product[2] }}" required placeholder="الكمية" min="0">
            <input type="number" step="0.01" name="price" value="{{ product[3] }}" required placeholder="السعر" min="0">
            <input type="text" name="seller" value="{{ product[4] }}" required placeholder="اسم البائع">
            <input type="text" name="image" value="{{ product[5] }}" placeholder="رابط الصورة">
            <div class="flex" style="margin-top: 15px;">
                <button type="submit" class="btn btn-primary" style="flex:1;">حفظ التعديلات</button>
                <a href="{{ url_for('index') }}" class="btn btn-danger" style="flex:1; text-align:center;">إلغاء</a>
            </div>
        </form>
    </div>
</div>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تسجيل الدخول</title>
    ''' + COMMON_STYLE + '''
</head>
<body>
<div class="container" style="max-width: 400px; margin-top: 80px;">
    <div class="card">
        <h2 style="text-align: center;">🔐 تسجيل الدخول</h2>
        <form method="POST">
            <input type="email" name="email" placeholder="البريد الإلكتروني" value="mmmmm_mmmmm319@yahoo.com" required>
            <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 10px;">دخول</button>
        </form>
    </div>
</div>
</body>
</html>
'''

@app.route('/')
def index():
    if 'user_email' not in session:
        session['user_email'] = 'mmmmm_mmmmm319@yahoo.com'
    
    query = request.args.get('q', '').strip()
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    if query:
        cursor.execute("SELECT * FROM products WHERE name LIKE ? OR seller LIKE ?", (f'%{query}%', f'%{query}%'))
    else:
        cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    
    cart = session.get('cart', [])
    cart_count = sum(item['quantity'] for item in cart)
    
    return render_template_string(INDEX_TEMPLATE, products=products, cart_count=cart_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        if email:
            session['user_email'] = email
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('index'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    flash('تم تسجيل الخروج', 'info')
    return redirect(url_for('index'))

@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form.get('name')
    quantity = int(request.form.get('quantity', 0))
    price = float(request.form.get('price', 0))
    seller = request.form.get('seller', 'محمد رجب')
    image = request.form.get('image', '')
    
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, quantity, price, seller, image) VALUES (?, ?, ?, ?, ?)",
                   (name, quantity, price, seller, image))
    conn.commit()
    conn.close()
    
    flash('تم إضافة المنتج بنجاح للمخزن', 'success')
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name')
        quantity = int(request.form.get('quantity', 0))
        price = float(request.form.get('price', 0))
        seller = request.form.get('seller')
        image = request.form.get('image')
        cursor.execute("UPDATE products SET name=?, quantity=?, price=?, seller=?, image=? WHERE id=?",
                       (name, quantity, price, seller, image, id))
        conn.commit()
        conn.close()
        flash('تم تحديث المنتج بنجاح', 'success')
        return redirect(url_for('index'))
    
    cursor.execute("SELECT * FROM products WHERE id=?", (id,))
    product = cursor.fetchone()
    conn.close()
    if not product:
        flash('المنتج غير موجود', 'danger')
        return redirect(url_for('index'))
    return render_template_string(EDIT_TEMPLATE, product=product)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_product(id):
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('تم حذف المنتج بنجاح', 'success')
    return redirect(url_for('index'))

@app.route('/add_to_cart/<int:id>', methods=['POST'])
def add_to_cart(id):
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id=?", (id,))
    product = cursor.fetchone()
    conn.close()
    
    if not product:
        flash('المنتج غير موجود', 'danger')
        return redirect(url_for('index'))
    
    if product[2] <= 0:
        flash('المنتج نفذ من المخزن!', 'danger')
        return redirect(url_for('index'))
    
    if 'cart' not in session:
        session['cart'] = []
    
    cart = session['cart']
    found = False
    for item in cart:
        if item['id'] == id:
            if item['quantity'] < product[2]:
                item['quantity'] += 1
                flash('تم زيادة كمية المنتج في السلة', 'success')
            else:
                flash('الكمية المطلوبة تتجاوز المخزن المتاح!', 'warning')
            found = True
            break
            
    if not found:
        cart.append({
            'id': product[0],
            'name': product[1],
            'price': product[3],
            'quantity': 1
        })
        flash('تم إضافة المنتج إلى السلة', 'success')
        
    session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/cart')
def cart_view():
    cart = session.get('cart', [])
    total_sum = sum(item['price'] * item['quantity'] for item in cart)
    return render_template_string(CART_TEMPLATE, cart_items=cart, total_sum=total_sum)

@app.route('/remove_from_cart/<int:id>', methods=['POST'])
def remove_from_cart(id):
    cart = session.get('cart', [])
    session['cart'] = [item for item in cart if item['id'] != id]
    flash('تم إزالة المنتج من السلة', 'info')
    return redirect(url_for('cart_view'))

@app.route('/checkout', methods=['POST'])
def checkout():
    user_email = session.get('user_email', 'mmmmm_mmmmm319@yahoo.com')
    cart = session.get('cart', [])
    
    if not cart:
        flash('سلة المشتريات فارغة!', 'warning')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    
    for item in cart:
        p_id = item['id']
        buy_qty = item['quantity']
        
        cursor.execute("SELECT quantity, name, price FROM products WHERE id=?", (p_id,))
        p_data = cursor.fetchone()
        
        if p_data:
            available_qty, p_name, p_price = p_data
            if available_qty >= buy_qty:
                new_qty = available_qty - buy_qty
                cursor.execute("UPDATE products SET quantity=? WHERE id=?", (new_qty, p_id))
                
                created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT INTO orders (user_email, product_name, quantity, total_price, created_at) VALUES (?, ?, ?, ?, ?)",
                               (user_email, p_name, buy_qty, p_price * buy_qty, created_at))
            else:
                flash(f'عذراً، الكمية غير متوفرة حالياً للمنتج: {p_name}', 'danger')
                conn.close()
                return redirect(url_for('cart_view'))
                
    conn.commit()
    conn.close()
    
    session['cart'] = []
    flash('تم إتمام الطلب بنجاح! وتم خصم المخزن وتسجيله في سجل الطلبات.', 'success')
    return redirect(url_for('orders_view'))

@app.route('/orders')
def orders_view():
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    conn.close()
    return render_template_string(ORDERS_TEMPLATE, orders=orders)

@app.route('/export_csv')
def export_csv():
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, quantity, price, seller FROM products")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Product Name', 'Quantity', 'Price', 'Seller'])
    for row in rows:
        writer.writerow(row)
        
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers["Content-Disposition"] = "attachment; filename=products_export.csv"
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
