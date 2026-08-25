from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required

app = Flask(__name__)
CORS(app)

# إعدادات قاعدة البيانات والسيرفر
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['JWT_SECRET_KEY'] = 'super-secret-key-change-it'  # مفتاح الأمان للتوكن
db = SQLAlchemy(app)
jwt = JWTManager(app)

# جدول المنتجات في قاعدة البيانات
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

# إنشاء جدول البيانات لو مش موجود
with app.app_context():
    db.create_all()

# مسار تسجيل الدخول (ليك أنت وحدك)
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # الإيميل والباسورد الثابتين بتوعك
    if username == 'mmmmm_mmmmm319@yahoo.com' and password == 'Zx1231992':
        access_token = create_access_token(identity=username)
        return jsonify(token=access_token), 200
    
    return jsonify({'message': 'بيانات الدخول غير صحيحة'}), 401

# 1. جلب وعرض المنتجات (متاح للجميع - للعامة في المتجر من غير تسجيل دخول)
@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    try:
        products = Product.query.all()
        products_list = []
        for p in products:
            products_list.append({
                'id': p.id,
                'name': p.name,
                'quantity': p.quantity,
                'price': p.price
            })
        return jsonify({'products': products_list}), 200
    except Exception as e:
        return jsonify({'message': 'حدث خطأ', 'error': str(e)}), 500

# 2. إضافة منتج جديد (محمي - ليك أنت وحدك بصلاحية المدير)
@app.route('/api/inventory', methods=['POST'])
@jwt_required()
def add_product():
    data = request.get_json()
    name = data.get('name')
    quantity = data.get('quantity')
    price = data.get('price')
    
    if not name or quantity is None or price is None:
        return jsonify({'message': 'جميع الحقول مطلوبة'}), 400
        
    new_product = Product(name=name, quantity=quantity, price=price)
    db.session.add(new_product)
    db.session.commit()
    
    return jsonify({'message': 'تم إضافة المنتج بنجاح'}), 201

# 3. حذف منتج (محمي - ليك أنت وحدك)
@app.route('/api/inventory/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_product(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({'message': 'المنتج غير موجود'}), 404
        
    db.session.delete(product)
    db.session.commit()
    
    return jsonify({'message': 'تم حذف المنتج بنجاح'}), 200

if __name__ == '__main__':
    app.run(debug=True)
    
