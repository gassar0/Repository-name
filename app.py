from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required

app = Flask(__name__)
CORS(app)

# إعدادات قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# إعدادات الحماية والـ JWT
app.config['JWT_SECRET_KEY'] = 'super-secret-key-change-this'
jwt = JWTManager(app)

# جدول المنتجات في قاعدة البيانات
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "price": self.price
        }

with app.app_context():
    db.create_all()

# مسار الصفحة الرئيسية لعرض المتجر تلقائياً
@app.route('/')
def home():
    return send_from_directory('.', 'store.html')

# مسار تسجيل دخول المدير
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # بيانات المدير المطابقة لصفحة المتجر
    if username == 'mmmmm_mmmmm319@yahoo.com' and password == 'Zx1231992':
        access_token = create_access_token(identity=username)
        return jsonify(token=access_token), 200
    return jsonify({"msg": "خطأ في الإيميل أو كلمة المرور"}), 401

# مسار عرض المنتجات (متاح للجميع بدون تسجيل دخول)
@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    products = Product.query.all()
    return jsonify({"products": [p.to_dict() for p in products]}), 200

# مسار إضافة منتج جديد (محمي بصلاحيات المدير فقط)
@app.route('/api/inventory', methods=['POST'])
@jwt_required()
def add_product():
    data = request.get_json()
    name = data.get('name')
    quantity = data.get('quantity')
    price = data.get('price')

    if not name or quantity is None or price is None:
        return jsonify({"msg": "الرجاء إدخال جميع البيانات"}), 400

    new_product = Product(name=name, quantity=quantity, price=price)
    db.session.add(new_product)
    db.session.commit()
    return jsonify({"msg": "تم إضافة المنتج بنجاح", "product": new_product.to_dict()}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
