import os
import json
import re
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, session, send_from_directory
import bcrypt
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import get_db, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, TESSERACT_PATH
from ingredient_analyzer import parse_ingredients, build_ingredient_analysis, extract_ins_numbers
from claim_verifier import verify_claims
from ocr_handler import process_ocr_image, process_ocr_nutrition

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# CORS configuration with credentials
CORS(app, 
     origins=["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:5000"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Configuration
UPLOAD_FOLDER = 'uploads'
EVIDENCE_FOLDER = 'evidence'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EVIDENCE_FOLDER'] = EVIDENCE_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EVIDENCE_FOLDER, exist_ok=True)

# ==================== AUTHENTICATION DECORATORS ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    health_conditions = data.get('health_conditions', [])
    
    if not all([username, email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    health_conditions_str = json.dumps(health_conditions)
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, health_conditions)
            VALUES (%s, %s, %s, 'user', %s)
        """, (username, email, hashed.decode('utf-8'), health_conditions_str))
        db.commit()
        user_id = cursor.lastrowid
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! Please login.',
            'user_id': user_id
        })
    except Exception as e:
        if 'username' in str(e):
            return jsonify({'error': 'Username already exists'}), 400
        elif 'email' in str(e):
            return jsonify({'error': 'Email already registered'}), 400
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            db = get_db()
            cursor = db.cursor()
            cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
            db.commit()
            cursor.close()
            db.close()
            
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['email'] = user['email']
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role']
                }
            })
        else:
            return jsonify({'error': 'Invalid email or password'}), 401
            
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/me', methods=['GET'])
def get_current_user():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'username': session.get('username'),
                'email': session.get('email'),
                'role': session.get('role')
            }
        })
    return jsonify({'authenticated': False})

# ==================== ADMIN ROUTES ====================

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, username, email, role, created_at, last_login FROM users ORDER BY id DESC")
        users = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify({'users': users, 'count': len(users)})
    except Exception as e:
        return jsonify({'error': str(e), 'users': []}), 500

@app.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def update_user_role(user_id):
    data = request.get_json()
    new_role = data.get('role')
    
    if new_role not in ['admin', 'user']:
        return jsonify({'error': 'Invalid role'}), 400
    
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot change your own role'}), 400
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': f'User role updated to {new_role}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete yourself'}), 400
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'User deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM flagged_products")
        total_reports = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM flagged_products WHERE status != 'Resolved'")
        pending_reports = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM flagged_products WHERE status = 'Resolved'")
        resolved_reports = cursor.fetchone()[0]
        
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True,
            'totalUsers': total_users,
            'totalReports': total_reports,
            'pendingReports': pending_reports,
            'resolvedReports': resolved_reports
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== PRODUCT ROUTES ====================

@app.route('/search', methods=['GET'])
def search_product():
    product_name = request.args.get('name', '')
    if not product_name:
        return jsonify({'error': 'Product name is required'}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT * FROM products 
        WHERE LOWER(product_name) LIKE LOWER(%s) OR LOWER(brand) LIKE LOWER(%s)
        LIMIT 5
    """, (f"%{product_name}%", f"%{product_name}%"))
    
    products = cursor.fetchall()

    if not products:
        cursor.close()
        db.close()
        return jsonify({'error': 'Product not found'}), 404

    product = products[0]
    ingredients_text = product.get('ingredients_text', '')
    
    # 1. Parse and analyze standard ingredients
    ingredient_list = parse_ingredients(ingredients_text)
    analysis = build_ingredient_analysis(ingredient_list, cursor)

    # 2. FIX: Extract INS numbers USING the cursor before it closes
    ins_data = extract_ins_numbers(ingredients_text, cursor)

    # 3. Now it is safe to close the database
    cursor.close()
    db.close()

    return jsonify({
        "product": {
            "product_name": product['product_name'],
            "brand": product['brand'],
            "ingredients_text": ingredients_text
        },
        **analysis,
        "ins_numbers": ins_data  # Pass the fetched data here
    })
@app.route('/analyze-ingredients', methods=['POST'])
def analyze_ingredients():
    data = request.get_json()
    ingredients_text = data.get('ingredients_text', '')

    if not ingredients_text:
        return jsonify({'error': 'Ingredients text is required'}), 400

    ingredient_list = parse_ingredients(ingredients_text)
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    analysis = build_ingredient_analysis(ingredient_list, cursor)
    cursor.close()
    db.close()

    return jsonify({
        "product": {"product_name": "Manual Analysis", "brand": "—", "ingredients_text": ingredients_text},
        **analysis,
        "ins_numbers": extract_ins_numbers(ingredients_text)
    })

@app.route('/add-product', methods=['POST'])
def add_product():
    data = request.get_json()
    product_name = data.get('product_name', '')
    brand = data.get('brand', '')
    ingredients_text = data.get('ingredients_text', '')
    
    if not all([product_name, brand, ingredients_text]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO products (product_name, brand, ingredients_text)
        VALUES (%s, %s, %s)
    """, (product_name, brand, ingredients_text))
    db.commit()
    
    ingredient_list = parse_ingredients(ingredients_text)
    analysis_cursor = db.cursor(dictionary=True, buffered=True)
    analysis = build_ingredient_analysis(ingredient_list, analysis_cursor)
    analysis_cursor.close()
    cursor.close()
    db.close()
    
    return jsonify({
        'success': True,
        'message': f'✅ Product "{product_name}" added successfully',
        'analysis': analysis
    })
# ==================== CLAIM & OCR ROUTES ====================

@app.route('/verify-claims', methods=['POST'])
def verify_claims_route():
    data = request.get_json()
    result = verify_claims(data.get('claims', []), data.get('ingredients_text', ''))
    return jsonify(result)

@app.route('/ocr', methods=['POST'])
def ocr_extract():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    extracted_text, error = process_ocr_image(request.files['image'])
    if error:
        return jsonify({'error': f'OCR failed: {error}'}), 500
    
    return jsonify({'extracted_text': extracted_text, 'raw_text': extracted_text, 'success': True})

@app.route('/api/ocr/nutrition', methods=['POST'])
def ocr_nutrition():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    extracted_text, error = process_ocr_nutrition(file)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'text': extracted_text,
        'success': True
    })

@app.route('/api/ocr/generic', methods=['POST'])
def ocr_generic():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    extracted_text, error = process_ocr_image(file)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'text': extracted_text,
        'success': True
    })
# Replace your ALTERNATIVES_DB in app.py with this more targeted list:

ALTERNATIVES_DB = [
    {
        "name": "Millet Noodles",
        "brand": "Slurrp Farm",
        "reason": "High fiber, no preservatives, whole grain alternative to refined wheat noodles",
        "tags": ["high fiber", "no preservatives", "whole grain"],
        "health_score": 82,
        "suitable_for": ["diabetes", "hypertension", "heartdisease"],
        "replaces_category": ["noodles", "instant noodles", "pasta", "maggi"]
    },
    {
        "name": "Brown Rice Noodles",
        "brand": "Nature's Basket",
        "reason": "Gluten-free, lower glycemic index than refined wheat noodles",
        "tags": ["gluten free", "low GI", "no additives"],
        "health_score": 78,
        "suitable_for": ["diabetes", "celiac"],
        "replaces_category": ["noodles", "instant noodles", "maggi"]
    },
    {
        "name": "Jowar Noodles",
        "brand": "Soulfull",
        "reason": "Made from sorghum, no MSG, no artificial preservatives, high fiber",
        "tags": ["no MSG", "high fiber", "no preservatives"],
        "health_score": 80,
        "suitable_for": ["diabetes", "hypertension"],
        "replaces_category": ["noodles", "instant noodles", "maggi"]
    },
    {
        "name": "Ragi Vermicelli",
        "brand": "Bambino",
        "reason": "Finger millet base, high calcium and iron, no MSG or artificial additives",
        "tags": ["no MSG", "high calcium", "no additives"],
        "health_score": 84,
        "suitable_for": ["pregnant", "diabetes", "hypertension"],
        "replaces_category": ["noodles", "instant noodles", "vermicelli", "maggi"]
    },
    {
        "name": "Oats Biscuits",
        "brand": "Britannia NutriChoice",
        "reason": "High fiber, lower sugar than regular biscuits",
        "tags": ["high fiber", "low sugar", "whole grain"],
        "health_score": 74,
        "suitable_for": ["diabetes", "heartdisease"],
        "replaces_category": ["biscuits", "cookies", "dark fantasy", "parle", "bakery"]
    },
    {
        "name": "Multigrain Cookies",
        "brand": "Unibic",
        "reason": "Whole grain, no maida, less sugar than cream biscuits",
        "tags": ["whole grain", "no maida", "low sugar"],
        "health_score": 76,
        "suitable_for": ["diabetes", "heartdisease"],
        "replaces_category": ["biscuits", "cookies", "dark fantasy", "bakery"]
    },
    {
        "name": "Ragi Cookies",
        "brand": "Sprout",
        "reason": "Finger millet based, high calcium, no refined flour",
        "tags": ["high calcium", "no maida", "whole grain"],
        "health_score": 78,
        "suitable_for": ["diabetes", "pregnant"],
        "replaces_category": ["biscuits", "cookies", "dark fantasy", "bakery"]
    },
    {
        "name": "Multigrain Bread",
        "brand": "Harvest Gold",
        "reason": "Complex carbs, added vitamins, no artificial colours",
        "tags": ["multigrain", "no artificial colour", "vitamins"],
        "health_score": 76,
        "suitable_for": ["heartdisease", "hypertension"],
        "replaces_category": ["bread", "bakery", "sandwich"]
    },
    {
        "name": "Cold Pressed Mustard Oil",
        "brand": "Dhara",
        "reason": "Natural fat source, no hydrogenation, rich in omega-3",
        "tags": ["natural", "no hydrogenation", "omega-3"],
        "health_score": 85,
        "suitable_for": ["heartdisease", "hypertension"],
        "replaces_category": ["oil", "cooking oil", "vegetable oil"]
    },
    {
        "name": "Rock Salt",
        "brand": "Tata",
        "reason": "Lower sodium than table salt, contains natural minerals",
        "tags": ["low sodium", "natural minerals"],
        "health_score": 80,
        "suitable_for": ["hypertension"],
        "replaces_category": ["salt", "condiments"]
    },
    {
        "name": "Stevia Sweetener",
        "brand": "Zindagi",
        "reason": "Zero calories, plant-based, does not spike blood sugar",
        "tags": ["zero calorie", "plant-based", "no sugar spike"],
        "health_score": 88,
        "suitable_for": ["diabetes", "pcos"],
        "replaces_category": ["sugar", "sweetener"]
    },
    {
        "name": "Unsalted Mixed Nuts",
        "brand": "Happilo",
        "reason": "Healthy fats, high protein, no added salt or preservatives",
        "tags": ["healthy fats", "high protein", "no preservatives"],
        "health_score": 90,
        "suitable_for": ["heartdisease", "diabetes", "pcos"],
        "replaces_category": ["snacks", "chips", "namkeen", "kurkure", "bingo"]
    },
    {
        "name": "Greek Yogurt",
        "brand": "Epigamia",
        "reason": "High protein, probiotic, no added sugar in plain variant",
        "tags": ["high protein", "probiotic", "no added sugar"],
        "health_score": 86,
        "suitable_for": ["pcos", "thyroid", "pregnant"],
        "replaces_category": ["dairy", "yogurt", "dahi", "curd"]
    },
    {
        "name": "Quinoa",
        "brand": "True Elements",
        "reason": "Complete protein, gluten-free, high fiber, low GI",
        "tags": ["complete protein", "gluten free", "low GI"],
        "health_score": 92,
        "suitable_for": ["celiac", "diabetes", "pcos", "pregnant"],
        "replaces_category": ["rice", "grains", "cereal"]
    },
    {
        "name": "Baked Makhana",
        "brand": "Go Makhana",
        "reason": "Low sodium, no artificial flavours, high magnesium",
        "tags": ["low sodium", "no artificial flavour", "baked"],
        "health_score": 83,
        "suitable_for": ["hypertension", "heartdisease", "pregnant"],
        "replaces_category": ["snacks", "chips", "namkeen", "kurkure", "bingo"]
    },
    {
        "name": "Homemade Tomato Sauce",
        "brand": "DIY",
        "reason": "No preservatives, no added colour, control over sodium and sugar",
        "tags": ["no preservatives", "no added colour", "low sodium"],
        "health_score": 95,
        "suitable_for": ["hypertension", "diabetes", "heartdisease"],
        "replaces_category": ["sauce", "ketchup", "condiments"]
    }
]


@app.route('/get-alternatives', methods=['POST'])
def get_alternatives():
    data = request.get_json() or {}
    overall_risk = data.get('overall_risk', 'Low')
    health_conditions = data.get('health_conditions', [])
    product_name = data.get('product_name', '').lower()
    brand = data.get('brand', '').lower()
    flagged_names = [f.lower() for f in data.get('flagged_ingredient_names', [])]
    flagged_issues = [f.lower() for f in data.get('flagged_issues', [])]

    # Only show alternatives for High or Moderate risk products
    if overall_risk == 'Low':
        return jsonify({'alternatives': [], 'show': False})

    # Improved category detection
    product_lower = f"{product_name} {brand}"
    
    # Direct brand matching
    brand_mapping = {
        'maggi': ['noodles', 'instant noodles'],
        'kurkure': ['snacks', 'chips', 'namkeen'],
        'lays': ['chips', 'snacks'],
        'bingo': ['chips', 'snacks'],
        'parle': ['biscuits', 'cookies'],
        'britannia': ['biscuits', 'cookies', 'bread'],
        'dark fantasy': ['biscuits', 'cookies', 'dark fantasy'],
        'amul': ['milk', 'dairy', 'butter', 'cheese'],
        'mother dairy': ['milk', 'dairy', 'yogurt'],
        'nestle': ['noodles', 'chocolate', 'dairy'],
    }
    
    product_category_hints = []
    
    # Check brand mapping
    for brand_key, categories in brand_mapping.items():
        if brand_key in product_lower:
            product_category_hints.extend(categories)
    
    # Check for category keywords in product name
    category_keywords = {
        'noodles': ['noodle', 'maggi', 'yippee', 'top ramen', 'ching', 'vermicelli', 'pasta'],
        'biscuits': ['biscuit', 'cookie', 'parle', 'marie', 'krack', 'dark fantasy', 'oreo', 'hide & seek', 'good day'],
        'chips': ['chip', 'lays', 'kurkure', 'too yumm', 'bingo', 'namkeen', 'snack'],
        'sauce': ['sauce', 'ketchup', 'kissan', 'maggi sauce'],
        'oil': ['oil', 'ghee', 'vanaspati', 'cooking oil'],
        'milk': ['milk', 'dairy', 'dahi', 'yogurt', 'amul', 'toned milk'],
        'bread': ['bread', 'rusk', 'toast', 'sandwich'],
        'sugar': ['sugar', 'jaggery', 'syrup', 'sweetener'],
        'salt': ['salt', 'namak', 'sendha namak'],
        'butter': ['butter', 'margarine', 'butter spread'],
        'cheese': ['cheese', 'processed cheese', 'cheddar'],
    }
    
    for cat, keywords in category_keywords.items():
        for kw in keywords:
            if kw in product_lower:
                product_category_hints.append(cat)
    
    # Remove duplicates
    product_category_hints = list(set(product_category_hints))
    
    # If no category detected, try to infer from product type
    if not product_category_hints:
        # Default fallbacks based on common product types
        if 'biscuit' in product_lower or 'cookie' in product_lower:
            product_category_hints = ['biscuits', 'cookies']
        elif 'noodle' in product_lower or 'maggi' in product_lower:
            product_category_hints = ['noodles', 'instant noodles']
        elif 'chip' in product_lower or 'snack' in product_lower:
            product_category_hints = ['snacks', 'chips']
    
    scored = []
    for alt in ALTERNATIVES_DB:
        score = 0
        replaces = [r.lower() for r in alt.get('replaces_category', [])]
        
        # PRIMARY SIGNAL: direct brand match or category match
        category_match = any(hint in replaces for hint in product_category_hints)
        
        # Specific brand matching for better alternatives
        if 'dark fantasy' in product_lower and 'dark fantasy' in replaces:
            score += 20  # Strong boost for Dark Fantasy alternatives
        elif 'maggi' in product_lower and 'maggi' in replaces:
            score += 20
        elif 'kurkure' in product_lower and 'kurkure' in replaces:
            score += 20
        elif category_match:
            score += 15
        
        # If no category match at all, skip entirely
        if not category_match and product_category_hints:
            continue
        
        # Health condition match
        for condition in health_conditions:
            if condition in alt.get('suitable_for', []):
                score += 5
        
        # Tag addresses a flagged issue
        for issue in flagged_issues:
            for tag in alt.get('tags', []):
                if any(word in tag.lower() for word in issue.split()):
                    score += 2
        
        # Base health score (0-100 scale, divide by 10)
        score += alt['health_score'] / 10
        
        # Penalize if health_score is low
        if alt['health_score'] < 70:
            score -= 5
        
        scored.append({**alt, '_score': score})
    
    # Sort by score and take top 3
    scored.sort(key=lambda x: x['_score'], reverse=True)
    top = []
    for a in scored[:3]:
        top.append({
            'name': a['name'],
            'brand': a['brand'],
            'reason': a['reason'],
            'tags': a['tags'],
            'health_score': a['health_score']
        })
    
    return jsonify({'alternatives': top, 'show': bool(top)})
# ==================== REPORT ROUTES ====================

@app.route('/submit-report', methods=['POST'])
def submit_report():
    try:
        product_name = request.form.get('product_name', '')
        brand = request.form.get('brand', '')
        category = request.form.get('category', '')
        batch_number = request.form.get('batch_number', '')
        barcode = request.form.get('barcode', '')
        purchase_location = request.form.get('purchase_location', '')
        issue_type = request.form.get('issue_type', '')
        severity = request.form.get('severity', 'medium')
        description = request.form.get('description', '')
        reporter_name = request.form.get('reporter_name', '')
        reporter_email = request.form.get('reporter_email', '')
        reporter_city = request.form.get('reporter_city', '')
        
        evidence_path = ''
        if 'evidence' in request.files:
            file = request.files['evidence']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                filepath = os.path.join(EVIDENCE_FOLDER, filename)
                file.save(filepath)
                evidence_path = filepath
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO flagged_products (
                product_name, brand, category, batch_number, barcode, 
                purchase_location, issue_type, severity, description, 
                reporter_name, reporter_email, reporter_city, evidence_path, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Under Review')
        """, (product_name, brand, category, batch_number, barcode,
              purchase_location, issue_type, severity, description,
              reporter_name, reporter_email, reporter_city, evidence_path))
        
        db.commit()
        report_id = cursor.lastrowid
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True,
            'message': 'Report submitted successfully',
            'report_id': report_id,
            'evidence_path': evidence_path
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/flagged-products', methods=['GET'])
def get_flagged_products():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM flagged_products ORDER BY id DESC")
        products = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify({'products': products, 'count': len(products)})
    except Exception as e:
        return jsonify({'error': str(e), 'products': []}), 500

@app.route('/evidence/<path:filename>')
def serve_evidence(filename):
    try:
        return send_from_directory('evidence', filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/flagged-products/<int:report_id>/resolve', methods=['PUT'])
def resolve_report(report_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE flagged_products SET status = 'Resolved' WHERE id = %s", (report_id,))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({'success': True})

@app.route('/api/flagged-products/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM flagged_products WHERE id = %s", (report_id,))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({'success': True})

# ==================== OTHER ROUTES ====================

@app.route('/products', methods=['GET'])
def list_products():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT product_name, brand FROM products ORDER BY product_name LIMIT 100")
    products = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({'products': products, 'count': len(products)})

@app.route('/ingredients', methods=['GET'])
def get_all_ingredients():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ingredients")
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(results)

@app.route('/disease-aware', methods=['GET'])
def disease_aware():
    condition = request.args.get('condition', '')
    if not condition:
        return jsonify({'error': 'Health condition is required'}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ingredients WHERE LOWER(caution_group) LIKE LOWER(%s)", (f"%{condition}%",))
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({'condition': condition, 'ingredients_to_avoid': results})

@app.route('/health-score', methods=['POST'])
def health_score():
    data = request.get_json()
    ingredients_text = data.get('ingredients_text', '')
    
    if not ingredients_text:
        return jsonify({'error': 'Ingredients text required'}), 400
    
    ingredient_list = parse_ingredients(ingredients_text)
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    high_risk_count = moderate_risk_count = 0
    for ing in ingredient_list:
        cursor.execute("SELECT risk_level FROM ingredients WHERE LOWER(ingredient_name) LIKE LOWER(%s)", (f"%{ing}%",))
        result = cursor.fetchone()
        if result:
            if result['risk_level'] == 'High':
                high_risk_count += 1
            elif result['risk_level'] == 'Moderate':
                moderate_risk_count += 1
    
    cursor.close()
    db.close()
    
    score = max(0, min(100, 100 - (high_risk_count * 15) - (moderate_risk_count * 8)))
    
    if score >= 80:
        rating = "🌟 Excellent - Very healthy choice"
    elif score >= 60:
        rating = "👍 Good - Moderately healthy"
    elif score >= 40:
        rating = "⚠️ Fair - Consume in moderation"
    else:
        rating = "🚫 Poor - Limited consumption recommended"
    
    return jsonify({'health_score': score, 'rating': rating, 'high_risk_count': high_risk_count, 'moderate_risk_count': moderate_risk_count})

# ==================== HOME ROUTE ====================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'name': 'Food Safety Checker API',
        'version': '2.0',
        'status': 'running',
        'endpoints': {
            'search': 'GET /search?name=<product>',
            'analyze': 'POST /analyze-ingredients',
            'verify': 'POST /verify-claims',
            'ocr': 'POST /ocr',
            'ocr-nutrition': 'POST /ocr-nutrition',
            'add': 'POST /add-product',
            'products': 'GET /products',
            'ingredients': 'GET /ingredients',
            'disease-aware': 'GET /disease-aware?condition=<condition>',
            'health-score': 'POST /health-score',
            'submit-report': 'POST /submit-report',
            'flagged-products': 'GET /flagged-products'
        }
    })

# ==================== INITIALIZE DATABASE ====================

def init_db():
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('admin', 'user') DEFAULT 'user',
                health_conditions TEXT,
                last_login TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw('admin123'.encode('utf-8'), salt)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'admin')
            """, ('Administrator', 'admin@foodsafety.com', hashed.decode('utf-8')))
            print("✅ Default admin created: admin@foodsafety.com / admin123")
        
        db.commit()
        cursor.close()
        db.close()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database init error: {e}")

# Initialize database
init_db()

# ==================== RUN APP ====================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🍎 FOOD SAFETY CHECKER API")
    print("="*60)
    
    if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
        print("✅ Tesseract found")
    else:
        print("⚠️ Tesseract not found")
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ingredients")
        ingredients_count = cursor.fetchone()[0]
        cursor.close()
        db.close()
        print(f"\n📊 Database: {products_count} products, {ingredients_count} ingredients")
    except Exception as e:
        print(f"\n⚠️ Database error: {e}")
    
    print("\n📍 Default Admin Credentials:")
    print("   Email: admin@foodsafety.com")
    print("   Password: admin123")
    print("\n🚀 Server running on http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)