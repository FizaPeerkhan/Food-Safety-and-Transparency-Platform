from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS
import re
import os
import cv2
import numpy as np
import subprocess
import tempfile

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Tesseract path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# -------------------------------
# Database Connection (Port 330)
# -------------------------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        port=330,
        user="root",
        password="r00t",
        database="food_safety"
    )

# -------------------------------
# Helper: Parse Ingredients
# -------------------------------
def parse_ingredients(text):
    """Parse ingredients text into list"""
    if not text:
        return []
    ingredients = re.split(r'[,;]\s*|and\s+', str(text).lower())
    return [i.strip() for i in ingredients if i.strip()]

# -------------------------------
# Helper: Extract INS Numbers
# -------------------------------
def extract_ins_numbers(ingredients_text):
    """Extract INS/E numbers from ingredients text"""
    if not ingredients_text:
        return []
    
    ins_mapping = {
        '621': 'Monosodium Glutamate (MSG)',
        '635': 'Disodium Ribonucleotides',
        '627': 'Disodium Guanylate',
        '631': 'Disodium Inosinate',
        '211': 'Sodium Benzoate',
        '202': 'Potassium Sorbate',
        '330': 'Citric Acid',
        '322': 'Lecithin',
        '407': 'Carrageenan',
        '412': 'Guar Gum',
        '415': 'Xanthan Gum',
        '500': 'Sodium Carbonate',
        '451': 'Triphosphate',
        '450': 'Diphosphate',
        '452': 'Polyphosphate',
        '950': 'Acesulfame K',
        '951': 'Aspartame',
        '952': 'Cyclamate',
        '954': 'Saccharin',
        '955': 'Sucralose',
        '150a': 'Caramel Color',
        '150c': 'Caramel Color III',
        '150d': 'Caramel Color IV',
        '160c': 'Paprika Extract',
        '102': 'Tartrazine',
        '110': 'Sunset Yellow',
        '122': 'Azorubine',
        '124': 'Ponceau 4R',
        '129': 'Allura Red',
        '133': 'Brilliant Blue',
        '171': 'Titanium Dioxide',
        '319': 'TBHQ',
        '260': 'Acetic Acid',
        '270': 'Lactic Acid',
        '296': 'Malic Acid',
        '334': 'Tartaric Acid',
        '338': 'Phosphoric Acid',
        '440': 'Pectin',
        '466': 'Carboxymethyl Cellulose',
        '471': 'Mono- and Diglycerides',
        '472': 'Esters of Mono- and Diglycerides',
        '475': 'Polyglycerol Esters',
        '476': 'Polyglycerol Polyricinoleate',
        '477': 'Propylene Glycol Esters',
        '481': 'Sodium Stearoyl Lactylate',
        '482': 'Calcium Stearoyl Lactylate',
        '491': 'Sorbitan Monostearate',
        '492': 'Sorbitan Tristearate',
        '503': 'Ammonium Carbonate',
        '504': 'Magnesium Carbonate',
        '508': 'Potassium Chloride',
        '509': 'Calcium Chloride',
        '551': 'Silicon Dioxide'
    }
    
    ins_pattern = r'(?:INS|E)?\s*(\d{3,4}[a-z]?)'
    matches = re.findall(ins_pattern, ingredients_text, re.IGNORECASE)
    result = []
    for match in matches:
        if match in ins_mapping:
            result.append(f"INS {match} ({ins_mapping[match]})")
        else:
            result.append(f"INS {match}")
    return list(set(result))

# -------------------------------
# Helper: Calculate Overall Risk
# -------------------------------
def calculate_overall_risk(risks):
    if not risks:
        return "Low"
    levels = []
    for r in risks:
        level = r.get('risk') or r.get('risk_level', '')
        levels.append(level)
    if 'High' in levels:
        return 'High'
    elif 'Moderate' in levels:
        return 'Moderate'
    else:
        return 'Low'

# -------------------------------
# Route 1: Search Product
# -------------------------------
@app.route('/search', methods=['GET'])
def search_product():
    product_name = request.args.get('name', '')
    if not product_name:
        return jsonify({'error': 'Product name is required'}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Search using actual column names: product_name and brand
    cursor.execute("""
        SELECT * FROM products 
        WHERE LOWER(product_name) LIKE LOWER(%s) 
           OR LOWER(brand) LIKE LOWER(%s)
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

    high_risk = []
    moderate_risk = []
    allergens = []
    health_warnings = []
    all_flagged = []

    for ing in ingredient_list:
        risk_cursor = db.cursor(dictionary=True)
        risk_cursor.execute("""
            SELECT * FROM ingredients 
            WHERE LOWER(ingredient_name) LIKE LOWER(%s)
            LIMIT 1
        """, (f"%{ing}%",))
        result = risk_cursor.fetchone()
        
        if result:
            caution_group = result.get('caution_group', '')
            if caution_group and caution_group.lower() not in ['general consumers', 'general consumer', 'general']:
                flagged_item = {
                    "ingredient": ing,
                    "risk": result['risk_level'],
                    "reason": result.get('explanation', 'May cause issues'),
                    "caution_for": caution_group
                }
                all_flagged.append(flagged_item)
                
                if result['risk_level'] == 'High':
                    high_risk.append(flagged_item)
                elif result['risk_level'] == 'Moderate':
                    moderate_risk.append(flagged_item)
                
                if result.get('allergen_type'):
                    allergens.append(result['allergen_type'])
                
                if caution_group:
                    health_warnings.append(f"{ing}: {result.get('explanation', '')}")
        risk_cursor.close()

    cursor.close()
    db.close()

    overall_risk = calculate_overall_risk(all_flagged)

    return jsonify({
        "product": {
            "product_name": product['product_name'],
            "brand": product['brand'],
            "ingredients_text": ingredients_text
        },
        "overall_risk": overall_risk,
        "high_risk_ingredients": high_risk,
        "moderate_risk_ingredients": moderate_risk,
        "all_flagged_ingredients": all_flagged,
        "allergens": list(set(allergens)),
        "health_warnings": list(set(health_warnings)),
        "ins_numbers": extract_ins_numbers(ingredients_text)
    })

# -------------------------------
# Route 2: Analyze Ingredients
# -------------------------------
@app.route('/analyze-ingredients', methods=['POST'])
def analyze_ingredients():
    data = request.get_json()
    ingredients_text = data.get('ingredients_text', '')

    if not ingredients_text:
        return jsonify({'error': 'Ingredients text is required'}), 400

    ingredient_list = parse_ingredients(ingredients_text)
    ingredient_risks = []
    allergens = []
    health_warnings = []

    db = get_db()
    cursor = db.cursor(dictionary=True)

    for ing in ingredient_list:
        cursor.execute("""
            SELECT * FROM ingredients 
            WHERE LOWER(ingredient_name) LIKE LOWER(%s)
            LIMIT 1
        """, (f"%{ing}%",))
        result = cursor.fetchone()
        
        if result:
            caution_group = result.get('caution_group', '')
            if caution_group and caution_group.lower() not in ['general consumers', 'general consumer', 'general']:
                ingredient_risks.append({
                    'ingredient_name': result['ingredient_name'],
                    'risk_level': result['risk_level'],
                    'explanation': result.get('explanation', ''),
                    'caution_group': caution_group
                })
                
                if result.get('allergen_type'):
                    allergens.append(result['allergen_type'])
                if caution_group:
                    health_warnings.append(f"{result['ingredient_name']}: {result.get('explanation', '')}")

    cursor.close()
    db.close()

    high_count = sum(1 for r in ingredient_risks if r['risk_level'] == 'High')
    moderate_count = sum(1 for r in ingredient_risks if r['risk_level'] == 'Moderate')

    if high_count > 0:
        overall_risk = 'High'
        risk_badge = f'🔴 High Risk - {high_count} concerning ingredient(s) found'
    elif moderate_count > 0:
        overall_risk = 'Moderate'
        risk_badge = f'🟡 Moderate Risk - {moderate_count} ingredient(s) may affect sensitive individuals'
    else:
        overall_risk = 'Low'
        risk_badge = '🟢 Low Risk - Generally safe for most consumers'

    return jsonify({
        'overall_risk': overall_risk,
        'risk_badge': risk_badge,
        'ingredient_risks': ingredient_risks,
        'allergens': list(set(allergens)),
        'health_warnings': list(set(health_warnings)),
        'ins_numbers': extract_ins_numbers(ingredients_text)
    })

# -------------------------------
# Route 3: OCR Extraction
# -------------------------------
@app.route('/ocr', methods=['POST'])
def ocr_extract():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    image_data = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify({'error': 'Could not read image'}), 400

    # Preprocess
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        temp_path = tmp.name
    cv2.imwrite(temp_path, gray)

    # Call Tesseract directly
    output_path = temp_path.replace('.png', '')

    try:
        subprocess.run(
            [TESSERACT_PATH, temp_path, output_path],
            check=True,
            capture_output=True
        )
        with open(output_path + '.txt', 'r', encoding='utf-8') as f:
            extracted_text = f.read()
    except Exception as e:
        return jsonify({'error': f'OCR failed: {str(e)}'}), 500
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass
        try:
            os.unlink(output_path + '.txt')
        except:
            pass

    cleaned = extracted_text.replace('\n', ', ').strip()
    cleaned = ', '.join([x.strip() for x in cleaned.split(',') if x.strip()])

    return jsonify({
        'extracted_text': cleaned,
        'raw_text': extracted_text,
        'success': True
    })

# -------------------------------
# Route 4: Verify Marketing Claims
# -------------------------------
CLAIM_RULES = {
    "no added sugar": {
        "banned_ingredients": ["sugar", "high fructose corn syrup", "invert sugar",
                               "glucose syrup", "dextrose", "fructose", "sucrose",
                               "maltodextrin", "corn syrup", "liquid glucose", "jaggery", "honey"],
        "message": "⚠️ Claims 'No Added Sugar' but contains sugar-based ingredients."
    },
    "no preservatives": {
        "banned_ingredients": ["sodium benzoate", "potassium sorbate", "sodium nitrate",
                               "sulphur dioxide", "bha", "bht", "tbhq", "calcium propionate",
                               "sodium metabisulphite", "ins 211", "ins 202", "benzoate", "sorbate"],
        "message": "⚠️ Claims 'No Preservatives' but contains preservative ingredients."
    },
    "low fat": {
        "banned_ingredients": ["palm oil", "hydrogenated vegetable oil", "vanaspati",
                               "coconut oil", "butter", "cream", "whole milk", "ghee"],
        "message": "⚠️ Claims 'Low Fat' but contains high-fat ingredients."
    },
    "no artificial colours": {
        "banned_ingredients": ["tartrazine", "sunset yellow", "brilliant blue",
                               "allura red", "carmoisine", "erythrosine", "ins 102", "ins 110", "ins 129"],
        "message": "⚠️ Claims 'No Artificial Colours' but contains artificial colour additives."
    },
    "no msg": {
        "banned_ingredients": ["msg", "monosodium glutamate", "flavor enhancer", "e621", "ins 621"],
        "message": "⚠️ Claims 'No MSG' but contains MSG or similar flavor enhancers."
    },
    "gluten free": {
        "banned_ingredients": ["wheat flour", "wheat", "barley", "rye", "malt extract", "maida", "atta"],
        "message": "⚠️ Claims 'Gluten Free' but contains gluten-containing ingredients."
    },
    "sugar free": {
        "banned_ingredients": ["sugar", "high fructose corn syrup", "glucose syrup",
                               "dextrose", "sucrose", "fructose", "invert sugar", "jaggery"],
        "message": "⚠️ Claims 'Sugar Free' but contains sugar or sugar-derived ingredients."
    },
    "natural": {
        "banned_ingredients": ["aspartame", "saccharin", "acesulfame", "sucralose", 
                               "tartrazine", "sodium benzoate", "bha", "bht", "artificial flavor"],
        "message": "⚠️ Claims 'Natural' but contains artificial additives."
    },
    "dairy free": {
        "banned_ingredients": ["milk", "cream", "butter", "ghee", "whey", "casein", "lactose", "milk solids"],
        "message": "⚠️ Claims 'Dairy Free' but contains dairy ingredients."
    },
    "vegan": {
        "banned_ingredients": ["milk", "cream", "butter", "ghee", "whey", "casein", "egg", "honey", "gelatin"],
        "message": "⚠️ Claims 'Vegan' but contains animal-derived ingredients."
    }
}

@app.route('/verify-claims', methods=['POST'])
def verify_claims():
    data = request.get_json()
    claims = data.get('claims', [])
    ingredients_text = data.get('ingredients_text', '')

    if not claims or not ingredients_text:
        return jsonify({'error': 'Both claims and ingredients_text are required'}), 400

    ingredients_lower = ingredients_text.lower()
    results = []

    for claim in claims:
        claim_clean = claim.strip().lower()
        matched_rule = None

        for key in CLAIM_RULES:
            if key in claim_clean or claim_clean in key:
                matched_rule = CLAIM_RULES[key]
                break

        if not matched_rule:
            results.append({
                "claim": claim,
                "status": "Unverified",
                "message": "ℹ️ We don't have a rule to verify this claim yet.",
                "violating_ingredients": []
            })
            continue

        found_violations = []
        for banned in matched_rule["banned_ingredients"]:
            if banned.lower() in ingredients_lower:
                found_violations.append(banned)

        if found_violations:
            results.append({
                "claim": claim,
                "status": "Misleading",
                "message": matched_rule["message"],
                "violating_ingredients": list(set(found_violations))
            })
        else:
            results.append({
                "claim": claim,
                "status": "Verified",
                "message": f"✅ '{claim}' - No contradicting ingredients found.",
                "violating_ingredients": []
            })

    statuses = [r["status"] for r in results]
    if "Misleading" in statuses:
        misleading_count = sum(1 for r in results if r["status"] == "Misleading")
        verdict = f"⚠️ {misleading_count} claim(s) appear misleading"
    elif "Unverified" in statuses:
        verdict = "ℹ️ Some claims could not be verified"
    else:
        verdict = "✅ All claims appear consistent with ingredients"

    return jsonify({
        "claims_checked": len(results),
        "verdict": verdict,
        "results": results
    })

# -------------------------------
# Route 5: Add New Product
# -------------------------------
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
    
    # Using correct column names: product_name, brand, ingredients_text
    cursor.execute("""
        INSERT INTO products (product_name, brand, ingredients_text)
        VALUES (%s, %s, %s)
    """, (product_name, brand, ingredients_text))
    
    db.commit()
    cursor.close()
    db.close()
    
    return jsonify({
        'success': True,
        'message': f'✅ Product "{product_name}" added successfully'
    })

# -------------------------------
# Route 6: List All Products
# -------------------------------
@app.route('/products', methods=['GET'])
def list_products():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT product_name, brand FROM products ORDER BY product_name LIMIT 100")
    products = cursor.fetchall()
    cursor.close()
    db.close()
    
    return jsonify({
        'products': products,
        'count': len(products)
    })

# -------------------------------
# Route 7: Disease-Aware Filter
# -------------------------------
@app.route('/disease-aware', methods=['GET'])
def disease_aware():
    condition = request.args.get('condition', '')
    if not condition:
        return jsonify({'error': 'Health condition is required'}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM ingredients WHERE LOWER(caution_group) LIKE LOWER(%s)",
        (f"%{condition}%",)
    )
    results = cursor.fetchall()
    cursor.close()
    db.close()

    return jsonify({
        'condition': condition,
        'ingredients_to_avoid': results
    })

# -------------------------------
# Route 8: Get All Ingredients
# -------------------------------
@app.route('/ingredients', methods=['GET'])
def get_all_ingredients():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ingredients")
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(results)

# -------------------------------
# Route 9: Health Score Calculator
# -------------------------------
@app.route('/health-score', methods=['POST'])
def health_score():
    data = request.get_json()
    ingredients_text = data.get('ingredients_text', '')
    
    if not ingredients_text:
        return jsonify({'error': 'Ingredients text required'}), 400
    
    ingredient_list = parse_ingredients(ingredients_text)
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    high_risk_count = 0
    moderate_risk_count = 0
    
    for ing in ingredient_list:
        cursor.execute(
            "SELECT risk_level FROM ingredients WHERE LOWER(ingredient_name) LIKE LOWER(%s)",
            (f"%{ing}%",)
        )
        result = cursor.fetchone()
        if result:
            if result['risk_level'] == 'High':
                high_risk_count += 1
            elif result['risk_level'] == 'Moderate':
                moderate_risk_count += 1
    
    cursor.close()
    db.close()
    
    score = 100
    score -= high_risk_count * 15
    score -= moderate_risk_count * 8
    score = max(0, min(100, score))
    
    if score >= 80:
        rating = "🌟 Excellent - Very healthy choice"
    elif score >= 60:
        rating = "👍 Good - Moderately healthy"
    elif score >= 40:
        rating = "⚠️ Fair - Consume in moderation"
    else:
        rating = "🚫 Poor - Limited consumption recommended"
    
    return jsonify({
        'health_score': score,
        'rating': rating,
        'high_risk_count': high_risk_count,
        'moderate_risk_count': moderate_risk_count
    })

# -------------------------------
# Route 10: Home
# -------------------------------
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'name': 'Food Safety Checker API',
        'version': '2.0',
        'status': 'running',
        'database': {
            'products_table': 'products (product_name, brand, ingredients_text)',
            'ingredients_table': 'ingredients'
        },
        'endpoints': {
            'search': 'GET /search?name=<product>',
            'analyze': 'POST /analyze-ingredients',
            'verify': 'POST /verify-claims',
            'ocr': 'POST /ocr (upload image)',
            'add': 'POST /add-product',
            'products': 'GET /products',
            'ingredients': 'GET /ingredients',
            'disease-aware': 'GET /disease-aware?condition=<condition>',
            'health-score': 'POST /health-score'
        }
    })

# -------------------------------
# Run App
# -------------------------------
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🍎 FOOD SAFETY CHECKER API (Final Version)")
    print("="*60)
    
    # Check Tesseract
    if os.path.exists(TESSERACT_PATH):
        print(f"✅ Tesseract found at: {TESSERACT_PATH}")
    else:
        print(f"⚠️ Tesseract not found at: {TESSERACT_PATH}")
        print("   OCR feature may not work. Update TESSERACT_PATH if needed.")
    
    # Test database connection
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
        print(f"\n⚠️ Database connection error: {e}")
        print("   Make sure MySQL is running on port 330")
    
    print("\n📍 Test URLs:")
    print("   http://127.0.0.1:5000/")
    print("   http://127.0.0.1:5000/search?name=butter")
    print("   http://127.0.0.1:5000/search?name=amul")
    print("   http://127.0.0.1:5000/products")
    print("   http://127.0.0.1:5000/ingredients")
    print("\n🚀 Server running on http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)