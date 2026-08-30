import os
import csv
import sqlite3
from io import StringIO
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# إعدادات بوت تيليجرام
TELEGRAM_BOT_TOKEN = '8969435828:AAEsccn8O8KuiqaVLQSERnxY2rstA8SF8JQ'
TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID_HERE'  # ضع الchat_id الخاص بك هنا

def send_telegram_notification(message):
    if TELEGRAM_CHAT_ID != 'YOUR_CHAT_ID_HERE':
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Telegram error: {e}")

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # جدول المنتجات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            image TEXT
        )
    ''')
    # جدول الطلبات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            total REAL NOT NULL,
            items TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/cart')
def cart():
    cart_items = session.get('cart', {})
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    detailed_cart = []
    total_price = 0
    for product_id, quantity in cart_items.items():
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if product:
            item_total = product[2] * quantity
            total_price += item_total
            detailed_cart.append({
                'id': product[0],
                'name': product[1],
                'price': product[2],
                'image': product[4],
                'quantity': quantity,
                'total': item_total
            })
    conn.close()
    return render_template('cart.html', cart=detailed_cart, total_price=total_price)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = {}
    cart = session['cart']
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        cart[product_id_str] += 1
    else:
        cart[product_id_str] = 1
    session.modified = True
    flash('تم إضافة المنتج إلى السلة بنجاح!', 'success')
    return redirect(url_for('index'))

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        del cart[product_id_str]
        session.modified = True
        flash('تم حذف المنتج من السلة.', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        customer_name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        cart_items = session.get('cart', {})
        if not cart_items:
            flash('سلة المشتريات فارغة!', 'warning')
            return redirect(url_for('cart'))
            
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        total_price = 0
        items_summary = []
        for product_id, quantity in cart_items.items():
            cursor.execute('SELECT name, price FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            if product:
                item_total = product[1] * quantity
                total_price += item_total
                items_summary.append(f"- {product[0]} (الكمية: {quantity}) - السعر: {item_total}")
                
        items_text = "\n".join(items_summary)
        
        cursor.execute('''
            INSERT INTO orders (customer_name, phone, address, total, items)
            VALUES (?, ?, ?, ?, ?)
        ''', (customer_name, phone, address, total_price, items_text))
        conn.commit()
        conn.close()
        
        # إرسال إشعار تيليجرام
        msg = f"🚨 *طلب جديد تم استلامه!*\n\n👤 العميل: {customer_name}\n📞 الهاتف: {phone}\n📍 العنوان: {address}\n💰 الإجمالي: {total_price}\n\n📦 المنتجات:\n{items_text}"
        send_telegram_notification(msg)
        
        # تفريغ السلة
        session.pop('cart', None)
        flash('تم إتمام الطلب بنجاح وتم إرسال الإشعار!', 'success')
        return redirect(url_for('index'))
        
    return render_template('checkout.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        image = request.form.get('image', 'default.jpg')
        
        cursor.execute('''
            INSERT INTO products (name, price, description, image)
            VALUES (?, ?, ?, ?)
        ''', (name, price, description, image))
        conn.commit()
        flash('تم إضافة المنتج بنجاح!', 'success')
        return redirect(url_for('admin'))
        
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
    orders = cursor.fetchall()
    conn.close()
    return render_template('admin.html', products=products, orders=orders)

@app.route('/export_csv')
def export_csv():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, customer_name, phone, address, total, items, created_at FROM orders')
    orders = cursor.fetchall()
    conn.close()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order ID', 'Customer Name', 'Phone', 'Address', 'Total', 'Items', 'Created At'])
    for order in orders:
        writer.writerow(order)
        
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=orders_report.csv'
    return response

if __name__ == '__main__':
    app.run(debug=True)
