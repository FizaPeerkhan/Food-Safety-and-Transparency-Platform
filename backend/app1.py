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
    if not text:
        return []
    parts = re.split(r'[,;]\s*', str(text))
    seen, result = set(), []
    for p in parts:
        clean = p.strip().lower()
        # strip percentages like "wheat flour (67%)" → "wheat flour"
        clean = re.sub(r'\s*\(\d+[\.\d]*\s*%?\)', '', clean).strip()
        if clean and len(clean) > 1 and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result

def build_ingredient_analysis(ingredient_list, cursor):
    """Single source of truth for ingredient risk analysis."""
    seen_ingredients = set()
    all_ingredients, high_risk, moderate_risk = [], [], []
    allergens, health_warnings = set(), set()
 
    for ing in ingredient_list:
        # PATCH 3: reverse LIKE — DB ingredient name is substring of the input text
        cursor.execute("""
            SELECT * FROM ingredients
            WHERE LOWER(%s) LIKE CONCAT('%%', LOWER(ingredient_name), '%%')
            LIMIT 1
        """, (ing,))
        row = cursor.fetchone()
 
        category = row.get('category', 'General Ingredient') if row else 'General Ingredient'
        risk_level = row.get('risk_level') if row else None
        flagged = False
 
        if row:
            caution = str(row.get('caution_group') or '').strip()
            allergen = str(row.get('allergen_type') or '').strip()
            if allergen.lower() in {'null', 'nan', 'none', ''}:
                allergen = None
 
            is_general = caution.lower() in {
                'general consumers', 'general consumer', 'general', 'generally safe', 'none', ''
            }
 
            if not is_general and caution:
                flagged = True
                ing_key = row['ingredient_name'].lower()
                if ing_key not in seen_ingredients:
                    seen_ingredients.add(ing_key)
                    entry = {
                        'ingredient':    row['ingredient_name'],
                        'original_text': ing,
                        'category':      category,
                        'risk_level':    row['risk_level'],
                        'explanation':   row.get('explanation', ''),
                        'caution_for':   caution,
                        'allergen':      allergen,
                    }
                    if row['risk_level'] == 'High':
                        high_risk.append(entry)
                    elif row['risk_level'] == 'Moderate':
                        moderate_risk.append(entry)
 
                    if allergen:
                        allergens.add(allergen)
                    health_warnings.add(f"{row['ingredient_name']} → Avoid for: {caution}")
 
        all_ingredients.append({
            'name':       ing,
            'category':   category,
            'risk_level': risk_level,
            'flagged':    flagged,
        })
 
    overall = 'High' if high_risk else ('Moderate' if moderate_risk else 'Low')
    return {
        'all_ingredients':           all_ingredients,
        'high_risk_ingredients':     high_risk,
        'moderate_risk_ingredients': moderate_risk,
        'allergens':                 list(allergens),
        'health_warnings':           list(health_warnings),
        'overall_risk':              overall,
    }
 
# -------------------------------
# Helper: Extract INS Numbers
# -------------------------------
INS_MAP = {
    '102':'Tartrazine','110':'Sunset Yellow','122':'Carmoisine',
    '129':'Allura Red','133':'Brilliant Blue','150a':'Caramel Color',
    '150c':'Caramel Color','150d':'Caramel Color','160c':'Paprika Extract',
    '171':'Titanium Dioxide','202':'Potassium Sorbate','211':'Sodium Benzoate',
    '220':'Sulphur Dioxide','250':'Sodium Nitrate','260':'Acetic Acid',
    '282':'Calcium Propionate','300':'Ascorbic Acid','319':'TBHQ',
    '320':'BHA','321':'BHT','322':'Lecithin','330':'Citric Acid',
    '407':'Carrageenan','412':'Guar Gum','415':'Xanthan Gum',
    '440':'Pectin','450':'Diphosphates','451':'Triphosphates',
    '460':'Cellulose','466':'CMC','471':'Mono & Diglycerides',
    '476':'PGPR','500':'Sodium Bicarbonate','503':'Ammonium Bicarbonate',
    '508':'Potassium Chloride','551':'Silicon Dioxide',
    '621':'Monosodium Glutamate','627':'Disodium Guanylate',
    '631':'Disodium Inosinate','635':'Disodium Ribonucleotides',
    '950':'Acesulfame K','951':'Aspartame','954':'Saccharin','955':'Sucralose',
}
 
def extract_ins_numbers(text):
    if not text:
        return []
    seen, result = set(), []
    for code in re.findall(r'(?:INS|E)\s*(\d{2,4}[a-z]?)', text, re.IGNORECASE):
        c = code.lower()
        if c not in seen:
            seen.add(c)
            name = INS_MAP.get(c)
            result.append({'code': f'INS {code.upper()}', 'name': name or 'Unknown additive'})
    return result  # empty list = caller hides the section

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
# Route 1: Search Product (FIXED - removed broken loop)
# -------------------------------
@app.route('/search', methods=['GET'])
def search_product():
    product_name = request.args.get('name', '')
    if not product_name:
        return jsonify({'error': 'Product name is required'}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

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

    # FIXED: Use build_ingredient_analysis instead of broken loop
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

# -------------------------------
# Route 2: Analyze Ingredients (FIXED - added missing route)
# -------------------------------
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
        "product": {
            "product_name": "Manual Analysis",
            "brand": "—",
            "ingredients_text": ingredients_text
        },
        **analysis,
        "ins_numbers": extract_ins_numbers(ingredients_text)
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
# Route 4: OCR Nutrition
# -------------------------------
@app.route('/ocr-nutrition', methods=['POST'])
def ocr_nutrition():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    image_data = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
    
    if image is None:
        return jsonify({'error': 'Could not read image'}), 400
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        temp_path = tmp.name
    cv2.imwrite(temp_path, gray)
    
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
    
    return jsonify({
        'success': True,
        'extracted_text': extracted_text
    })

# -------------------------------
# Route 5: Verify Marketing Claims
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
# Route 6: Add New Product (FIXED - returns analysis)
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
    
    # FIXED: Return analysis for the added product
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

# -------------------------------
# Route 7: List All Products
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
# Route 8: Disease-Aware Filter
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
# Route 9: Get All Ingredients
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
# Route 10: Health Score Calculator
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
# Route 11: Nutrition Analysis (FIXED - uses proper thresholds)
# -------------------------------
NUTRIENT_THRESHOLDS = {
    'calories':      {'unit':'kcal', 'high':400,  'moderate':200, 'worse':True,  'advice_high':'High calorie density — watch portion size.'},
    'total_fat':     {'unit':'g',    'high':20,   'moderate':10,  'worse':True,  'advice_high':'High fat content.'},
    'saturated_fat': {'unit':'g',    'high':5,    'moderate':2,   'worse':True,  'advice_high':'High saturated fat — raises cholesterol, risk for heart patients.'},
    'trans_fat':     {'unit':'g',    'high':0.5,  'moderate':0,   'worse':True,  'advice_high':'Trans fats detected — harmful for cardiovascular health.'},
    'sodium':        {'unit':'mg',   'high':600,  'moderate':300, 'worse':True,  'advice_high':'Very high sodium — people with hypertension should limit this.'},
    'sugar':         {'unit':'g',    'high':22.5, 'moderate':11,  'worse':True,  'advice_high':'High sugar content — diabetics and children should limit.'},
    'added_sugar':   {'unit':'g',    'high':10,   'moderate':5,   'worse':True,  'advice_high':'High added sugar content.'},
    'fiber':         {'unit':'g',    'good':6,    'moderate':3,   'worse':False, 'advice_low':'Low fiber — pair with vegetables and whole grains.'},
    'protein':       {'unit':'g',    'good':10,   'moderate':5,   'worse':False, 'advice_low':'Low protein content.'},
}

def parse_nutrition_text(text):
    t = text.lower()
    result = {}
    patterns = {
        'calories':      [r'(?:energy|calories?)[:\s]*(\d+(?:\.\d+)?)\s*(?:kcal|cal)?', r'(\d+(?:\.\d+)?)\s*kcal'],
        'total_fat':     [r'(?:total\s+)?fat[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'saturated_fat': [r'saturated[:\s]*(\d+(?:\.\d+)?)\s*g', r'sat\.?\s*fat[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'trans_fat':     [r'trans[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'sodium':        [r'sodium[:\s]*(\d+(?:\.\d+)?)\s*(mg|g)', r'salt[:\s]*(\d+(?:\.\d+)?)\s*(mg|g)'],
        'sugar':         [r'(?:total\s+)?sugar[s]?[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'added_sugar':   [r'added\s+sugar[s]?[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'fiber':         [r'(?:dietary\s+)?fi[b]?[e]?r[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'protein':       [r'protein[s]?[:\s]*(\d+(?:\.\d+)?)\s*g'],
    }
    for key, pats in patterns.items():
        for pat in pats:
            m = re.search(pat, t)
            if m:
                val = float(m.group(1))
                if key == 'sodium':
                    groups = m.groups()
                    unit = str(groups[1]).strip() if len(groups) > 1 and groups[1] else 'mg'
                    val = round(val * 1000, 2) if unit == 'g' else round(val, 2)
                result[key] = round(val, 2)
                break
    return result

def analyze_nutrients(data):
    """Returns per-nutrient status + overall score + verdict."""
    nutrients = []
    score = 100
    issues, cautions = [], []
 
    for key, cfg in NUTRIENT_THRESHOLDS.items():
        val = data.get(key)
        if val is None:
            continue
        unit = cfg['unit']
 
        if cfg['worse']:
            if val > cfg['high']:
                status, msg, bar = 'high', f"{val}{unit} — {cfg['advice_high']}", '#e53e3e'
                score -= 20 if key in ('sodium','saturated_fat','sugar','trans_fat') else 10
                issues.append(key.replace('_',' '))
            elif val > cfg['moderate']:
                status, msg, bar = 'moderate', f"{val}{unit} — moderate level", '#dd6b20'
                score -= 8 if key in ('sodium','saturated_fat','sugar') else 4
                cautions.append(key.replace('_',' '))
            else:
                status, msg, bar = 'low', f"{val}{unit} — within healthy range", '#38a169'
        else:
            if val >= cfg['good']:
                status, msg, bar = 'good', f"{val}{unit} — good level", '#38a169'
                score += 8
            elif val >= cfg['moderate']:
                status, msg, bar = 'moderate', f"{val}{unit} — moderate level", '#dd6b20'
            else:
                status, msg, bar = 'low', f"{val}{unit} — {cfg['advice_low']}", '#e53e3e'
                score -= 5
 
        nutrients.append({
            "label": key.replace('_', ' ').capitalize(),
            "value": val,
            "unit": unit,
            "status": status,
            "message": msg,
            "percentage": min(val * 2, 100),
            "bar_color": bar
        })
 
    score = max(0, min(100, score))
    rating = ('Excellent' if score >= 80 else 'Good' if score >= 60 else 'Fair' if score >= 40 else 'Poor')
    rating_color = {'Excellent':'#38a169','Good':'#68d391','Fair':'#ed8936','Poor':'#e53e3e'}[rating]
 
    # Build verdict
    parts = []
    if issues:    parts.append(f"This product is high in {' and '.join(issues)}")
    if cautions:  parts.append(f"moderate in {' and '.join(cautions)}")
 
    advice_groups = []
    if data.get('sodium',0) > 600 or data.get('saturated_fat',0) > 5:
        advice_groups.append('hypertension or heart conditions')
    if data.get('sugar',0) > 22.5:
        advice_groups.append('diabetes')
    if data.get('calories',0) > 400:
        advice_groups.append('weight management')
 
    verdict = '. '.join(parts) + '.' if parts else 'Nutritional profile looks balanced.'
    if advice_groups:
        verdict += f" People managing {', '.join(advice_groups)} should limit consumption."
 
    return {
        'health_score':  score,
        'rating':        rating,
        'rating_color':  rating_color,
        'nutrients':     nutrients,
        'verdict':       verdict,
    }

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

# -------------------------------
# Route 12: Home
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
            'ocr-nutrition': 'POST /ocr-nutrition (upload image)',
            'add': 'POST /add-product',
            'products': 'GET /products',
            'ingredients': 'GET /ingredients',
            'disease-aware': 'GET /disease-aware?condition=<condition>',
            'health-score': 'POST /health-score',
            'nutrition-analysis': 'POST /nutrition-analysis'
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
    print("   http://127.0.0.1:5000/nutrition-analysis (POST)")
    print("\n🚀 Server running on http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)