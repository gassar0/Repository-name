import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

app = Flask(__name__)
CORS(app)  # تفعيل الـ CORS لحل مشكلة الاتصال من المتصفح نهائياً

# إعدادات الأمان والتشفير (JWT)
app.config["JWT_SECRET_KEY"] = "super-secret-key-change-this"
jwt = JWTManager(app)


# دالة الاتصال بقاعدة البيانات
def get_db_connection():
  conn = sqlite3.connect("database.db")
  conn.row_factory = sqlite3.Row
  return conn


# إنشـاء الجداول والمستخدم الافتراضي تلقائياً
def init_db():
  conn = get_db_connection()
  # جدول المستخدمين
  conn.execute(
      "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,"
      " username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)"
  )
  # جدول المخزن والمنتجات
  conn.execute(
      "CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY"
      " AUTOINCREMENT, name TEXT NOT NULL, quantity INTEGER NOT NULL, price"
      " REAL NOT NULL)"
  )

  # إضافة حسابك الافتراضي تلقائياً عشان يشتغل من أول مرة
  user = conn.execute(
      "SELECT * FROM users WHERE username = ?", ("mmmmm_mmmmm319@yahoo.com",)
  ).fetchone()
  if not user:
    conn.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        ("mmmmm_mmmmm319@yahoo.com", "Zx1231992"),
    )

  conn.commit()
  conn.close()


# تشغيل تهيئة القاعدة أول ما السيرفر يقوم
init_db()


# 1. مسار تسجيل الدخول وإعطاء التوكن
@app.route("/api/auth/login", methods=["POST"])
def login():
  data = request.get_json()
  if not data or not data.get("username") or not data.get("password"):
    return (
        jsonify({"status": "error", "message": "اسم المستخدم وكلمة المرور مطلوبان"}),
        400,
    )

  username = data["username"]
  password = data["password"]

  conn = get_db_connection()
  user = conn.execute(
      "SELECT * FROM users WHERE username = ? AND password = ?",
      (username, password),
  ).fetchone()
  conn.close()

  if user:
    token = create_access_token(identity=username)
    return jsonify({"status": "success", "token": token}), 200
  else:
    return (
        jsonify({"status": "error", "message": "بيانات الدخول غير صحيحة"}),
        401,
    )


# 2. مسار جلب وعرض المنتجات (GET) أو إضافة منتج جديد (POST)
@app.route("/api/inventory", methods=["GET", "POST"])
@jwt_required()
def inventory():
  conn = get_db_connection()

  if request.method == "GET":
    products = conn.execute("SELECT * FROM inventory").fetchall()
    conn.close()
    return (
        jsonify({
            "status": "success",
            "products": [dict(p) for p in products],
        }),
        200,
    )

  if request.method == "POST":
    data = request.get_json()
    if (
        not data
        or "name" not in data
        or "quantity" not in data
        or "price" not in data
    ):
      conn.close()
      return (
          jsonify({"status": "error", "message": "بيانات المنتج غير مكتملة"}),
          400,
      )

    name = data["name"]
    quantity = data["quantity"]
    price = data["price"]

    conn.execute(
        "INSERT INTO inventory (name, quantity, price) VALUES (?, ?, ?)",
        (name, quantity, price),
    )
    conn.commit()
    conn.close()
    return (
        jsonify({"status": "success", "message": "تم إضافة المنتج بنجاح"}),
        201,
    )


# 3. مسار حذف منتج (DELETE)
@app.route("/api/inventory/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_product(id):
  conn = get_db_connection()
  product = conn.execute("SELECT * FROM inventory WHERE id = ?", (id,)).fetchone()
  if not product:
    conn.close()
    return jsonify({"status": "error", "message": "المنتج غير موجود"}), 404

  conn.execute("DELETE FROM inventory WHERE id = ?", (id,))
  conn.commit()
  conn.close()
  return jsonify({"status": "success", "message": "تم حذف المنتج بنجاح"}), 200


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
    
