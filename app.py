import sqlite3
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def init_db():
  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  # إنشاء جدول المنتجات مع دعم اسم التاجر وحالة الموافقة
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            vendor_name TEXT DEFAULT 'الإدارة',
            approved INTEGER DEFAULT 1
        )
    """)
  conn.commit()
  conn.close()


init_db()


@app.route("/")
def index():
  return render_template("store.html")


# تسجيل دخول المدير (بالبيانات المعتمدة)
@app.route("/admin/login", methods=["POST"])
def admin_login():
  data = request.json
  email = data.get("email")
  password = data.get("password")

  if email == "mmmmm_mmmmm319@yahoo.com":
    return jsonify({"status": "success", "message": "تم تسجيل الدخول بنجاح"})
  return jsonify({"status": "error", "message": "بيانات غير صحيحة"}), 401


# إضافة منتج بواسطة المدير (يظهر فوراً في المتجر)
@app.route("/add-product", methods=["POST"])
def add_product():
  data = request.json
  name = data.get("name")
  quantity = data.get("quantity")
  price = data.get("price")

  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO products (name, quantity, price, vendor_name, approved)"
      " VALUES (?, ?, ?, 'الإدارة', 1)",
      (name, quantity, price),
  )
  conn.commit()
  conn.close()
  return jsonify({"status": "success", "message": "تم إضافة المنتج بنجاح للمتجر"})


# إضافة منتج من تاجر خارجي (ينتظر الموافقة approved = 0)
@app.route("/vendor/add-product", methods=["POST"])
def vendor_add_product():
  data = request.json
  name = data.get("name")
  quantity = data.get("quantity")
  price = data.get("price")
  vendor_name = data.get("vendor_name", "تاجر خارجي")

  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO products (name, quantity, price, vendor_name, approved)"
      " VALUES (?, ?, ?, ?, 0)",
      (name, quantity, price, vendor_name),
  )
  conn.commit()
  conn.close()
  return jsonify({
      "status": "success",
      "message": (
          "تم إرسال المنتج بنجاح، في انتظار مراجعة الإدارة ليظهر في المتجر."
      ),
  })


# جلب المنتجات المعتمدة فقط للعامة في المتجر
@app.route("/api/products", methods=["GET"])
def get_public_products():
  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT name, quantity, price, vendor_name FROM products WHERE approved ="
      " 1"
  )
  rows = cursor.fetchall()
  conn.close()

  products = []
  for row in rows:
    products.append({
        "name": row,
        "quantity": row,
        "price": row,
        "vendor": row,
    })
  return jsonify(products)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
    
