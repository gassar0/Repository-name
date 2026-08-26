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
    return "Welcome to Smart Store - Flask & Moyasar Integration"

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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
