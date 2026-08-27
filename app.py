import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import requests

app = Flask(__name__)
app.secret_key = 'smart_store_secret_key'

def init_db():
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

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    conn.close()
    
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    
    return render_template('index.html', products=products, cart_count=cart_count)

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
    return render_template('register.html')

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
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/add-product', methods=['POST'])
def add_product():
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

@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
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
    cart = session.get('cart', {})
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    cart_items = []
    total_price = 0
    
    for product_id, quantity in cart.items():
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if product:
            item_total = product[3] * quantity
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
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

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
