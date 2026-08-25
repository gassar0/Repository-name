import csv
import io
import sqlite3
from flask import Flask, jsonify, make_response, render_template, request

app = Flask(__name__)


def init_db():
  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()

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

  cursor.execute("PRAGMA table_info(products)")
  columns = [info[1] for info in cursor.fetchall()]

  if "vendor_name" not in columns:
    cursor.execute(
        "ALTER TABLE products ADD COLUMN vendor_name TEXT DEFAULT 'الإدارة'"
    )

  if "approved" not in columns:
    cursor.execute("ALTER TABLE products ADD COLUMN approved INTEGER DEFAULT 1")

  conn.commit()
  conn.close()


init_db()


@app.route("/")
def index():
  return render_template("store.html")


@app.route("/admin/login", methods=["POST"])
def admin_login():
  data = request.json
  email = data.get("email")
  password = data.get("password")

  if email == "mmmmm_mmmmm319@yahoo.com":
    return jsonify({"status": "success", "message": "تم تسجيل الدخول بنجاح"})
  return jsonify({"status": "error", "message": "بيانات غير صحيحة"}), 401


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
        "name": row[0],
        "quantity": row[1],
        "price": row[2],
        "vendor": row[3],
    })
  return jsonify(products)


@app.route("/api/admin/products", methods=["GET"])
def get_admin_products():
  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, name, quantity, price, vendor_name, approved FROM products"
  )
  rows = cursor.fetchall()
  conn.close()

  products = []
  for row in rows:
    products.append({
        "id": row[0],
        "name": row[1],
        "quantity": row[2],
        "price": row[3],
        "vendor": row[4],
        "approved": row[5],
    })
  return jsonify(products)


@app.route("/admin/approve-product", methods=["POST"])
def approve_product():
  data = request.json
  prod_id = data.get("id")
  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  cursor.execute("UPDATE products SET approved = 1 WHERE id = ?", (prod_id,))
  conn.commit()
  conn.close()
  return jsonify({"status": "success", "message": "تم اعتماد المنتج بنجاح"})


@app.route("/admin/delete-product", methods=["POST"])
def delete_product():
  data = request.json
  prod_id = data.get("id")
  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
  conn.commit()
  conn.close()
  return jsonify({"status": "success", "message": "تم حذف المنتج بنجاح"})


@app.route("/admin/export-excel", methods=["GET"])
def export_excel():
  conn = sqlite3.connect("store.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, name, quantity, price, vendor_name, approved FROM products"
  )
  rows = cursor.fetchall()
  conn.close()

  output = io.StringIO()
  output.write("\ufeff")
  writer = csv.writer(output)
  writer.writerow(["م", "اسم المنتج", "الكمية", "السعر", "البائع", "الحالة"])

  for row in rows:
    status = "معتمد" if row[5] == 1 else "قيد الانتظار"
    writer.writerow([row[0], row[1], row[2], row[3], row[4], status])

  response = make_response(output.getvalue())
  response.headers["Content-Disposition"] = (
      "attachment; filename=store_report.csv"
  )
  response.headers["Content-type"] = "text/csv; charset=utf-8-sig"

  return response


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
  
  
