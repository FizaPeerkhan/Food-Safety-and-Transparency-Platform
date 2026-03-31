from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from config import get_db, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, TESSERACT_PATH
from ingredient_analyzer import parse_ingredients, build_ingredient_analysis, extract_ins_numbers
from nutrition_analyzer import parse_nutrition_text, analyze_nutrients
from claim_verifier import verify_claims
from ocr_handler import process_ocr_image, process_ocr_nutrition

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==================== ROUTES ====================

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
    ingredient_list = parse_ingredients(ingredients_text)
    analysis = build_ingredient_analysis(ingredient_list, cursor)

    cursor.close()
    db.close()

    return jsonify({
        "product": {
            "product_name": product['product_name'],
            "brand": product['brand'],
            "ingredients_text": ingredients_text
        },
        **analysis,
        "ins_numbers": extract_ins_numbers(ingredients_text)
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

@app.route('/verify-claims', methods=['POST'])
def verify_claims_route():
    data = request.get_json()
    result = verify_claims(data.get('claims', []), data.get('ingredients_text', ''))
    return jsonify(result)

@app.route('/nutrition-analysis', methods=['POST'])
def nutrition_analysis():
    data = request.get_json() or {}
    text = data.get('nutrition_text', '').strip()
    serving_size = data.get('serving_size', '100g')

    if not text:
        return jsonify({'error': 'Nutrition text is required'}), 400

    nutrition_info = parse_nutrition_text(text)
    if not nutrition_info:
        return jsonify({'error': 'Could not parse nutrition values'}), 400

    result = analyze_nutrients(nutrition_info)
    result['serving_size'] = serving_size
    result['nutrition_info'] = nutrition_info

    return jsonify(result)

@app.route('/ocr', methods=['POST'])
def ocr_extract():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    extracted_text, error = process_ocr_image(request.files['image'])
    if error:
        return jsonify({'error': f'OCR failed: {error}'}), 500
    
    return jsonify({'extracted_text': extracted_text, 'raw_text': extracted_text, 'success': True})

@app.route('/ocr-nutrition', methods=['POST'])
def ocr_nutrition():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    extracted_text, error = process_ocr_image(request.files['image'])
    if error:
        return jsonify({'error': f'OCR failed: {error}'}), 500
    
    return jsonify({'success': True, 'extracted_text': extracted_text})

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
            'nutrition-analysis': 'POST /nutrition-analysis'
        }
    })

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
    
    print("\n🚀 Server running on http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)