import re
from config import get_db, INS_MAP

# Debunked ingredients (educational info for common additives)
DEBUNKED_INGREDIENTS = {
    'thickener': {
        'explanation': 'Thickeners increase viscosity. Most are plant-based (guar gum, xanthan gum) and generally safe.',
        'risk_level': 'Low', 'caution_group': ''
    },
    'acidity regulator': {
        'explanation': 'Acidity regulators control pH. Citric acid occurs naturally in citrus fruits. Generally safe.',
        'risk_level': 'Low', 'caution_group': ''
    },
    'humectant': {
        'explanation': 'Humectants retain moisture in foods. They occur naturally and are considered safe.',
        'risk_level': 'Low', 'caution_group': ''
    },
    'flavour enhancer': {
        'explanation': 'Flavour enhancers amplify existing flavors. Most are naturally derived and safe.',
        'risk_level': 'Low', 'caution_group': ''
    },
    'emulsifier': {
        'explanation': 'Emulsifiers help mix oil and water. Lecithin is naturally found in eggs and soy.',
        'risk_level': 'Low', 'caution_group': ''
    },
    'stabilizer': {
        'explanation': 'Stabilizers maintain food texture. Most are plant-based and generally safe.',
        'risk_level': 'Low', 'caution_group': ''
    },
    'preservative': {
        'explanation': 'Preservatives prevent spoilage. Many are safe in approved amounts.',
        'risk_level': 'Low', 'caution_group': ''
    },
    'antioxidant': {
        'explanation': 'Antioxidants prevent oxidation. Natural ones like vitamin C are beneficial.',
        'risk_level': 'Low', 'caution_group': ''
    },
    'raising agent': {
        'explanation': 'Raising agents (baking soda, baking powder) help baked goods rise.',
        'risk_level': 'Low', 'caution_group': ''
    }
}
def parse_ingredients(text):
    if not text:
        return []

    text = str(text)

    # Step 1: Remove nested parenthetical sub-lists like (Palm Oil, Sunflower Oil)
    # but KEEP the main ingredient name before the bracket
    # e.g. "Edible Vegetable Oil (Palm Oil, Sunflower Oil)" → "Edible Vegetable Oil"
    text = re.sub(r'\([^)]*\)', '', text)

    # Step 2: Remove square bracket annotations like [INS 330, INS 412]
    text = re.sub(r'\[[^\]]*\]', '', text)

    # Step 3: Remove curly bracket annotations like {Sugar, Cocoa}
    text = re.sub(r'\{[^}]*\}', '', text)

    # Step 4: Split on comma, semicolon, " and " (with word boundary)
    parts = re.split(r'[,;]\s*|\s+and\s+', text, flags=re.IGNORECASE)

    seen, result = set(), []
    for p in parts:
        clean = p.strip().lower()

        # Remove leftover percentage annotations like "67%" or "(67%)"
        clean = re.sub(r'\(?\d+[\.\d]*\s*%?\)?', '', clean).strip()

        # Remove trailing/leading special characters
        clean = re.sub(r'^[\s\-\*•]+|[\s\-\*•]+$', '', clean)

        # Skip if too short, numeric only, or already seen
        if clean and len(clean) > 2 and not clean.isdigit() and clean not in seen:
            seen.add(clean)
            result.append(clean)

    return result
def extract_ins_numbers(text):
    """Extract INS/E numbers from ingredients text"""
    if not text:
        return []
    seen, result = set(), []
    for code in re.findall(r'(?:INS|E)\s*(\d{2,4}[a-z]?)', text, re.IGNORECASE):
        c = code.lower()
        if c not in seen:
            seen.add(c)
            name = INS_MAP.get(c)
            result.append({'code': f'INS {code.upper()}', 'name': name or 'Unknown additive'})
    return result

def get_debunked_info(ingredient):
    """Return debunked info for common additive categories"""
    ingredient_lower = ingredient.lower()
    for key, info in DEBUNKED_INGREDIENTS.items():
        if key in ingredient_lower:
            return info
    return None

def build_ingredient_analysis(ingredient_list, cursor):
    """Single source of truth for ingredient risk analysis."""
    seen_ingredients = set()
    all_ingredients, high_risk, moderate_risk = [], [], []
    allergens, health_warnings = set(), set()
 
    for ing in ingredient_list:
        # Check for debunked additives first
        debunked = get_debunked_info(ing)
        if debunked:
            all_ingredients.append({
                'name': ing,
                'category': 'Food Additive',
                'risk_level': 'Low',
                'flagged': False
            })
            continue
        
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
                        'ingredient': row['ingredient_name'],
                        'original_text': ing,
                        'category': category,
                        'risk_level': row['risk_level'],
                        'explanation': row.get('explanation', ''),
                        'caution_for': caution,
                        'allergen': allergen,
                    }
                    if row['risk_level'] == 'High':
                        high_risk.append(entry)
                    elif row['risk_level'] == 'Moderate':
                        moderate_risk.append(entry)
 
                    if allergen:
                        allergens.add(allergen)
                    
                    # FIXED: This should be for ALL flagged ingredients (both High and Moderate)
                    # Just like your original code
                    health_warnings.add(f"{row['ingredient_name']} → Avoid for: {caution}")
 
        all_ingredients.append({
            'name': ing,
            'category': category,
            'risk_level': risk_level,
            'flagged': flagged,
        })
 
    overall = 'High' if high_risk else ('Moderate' if moderate_risk else 'Low')
    return {
        'all_ingredients': all_ingredients,
        'high_risk_ingredients': high_risk,
        'moderate_risk_ingredients': moderate_risk,
        'allergens': list(allergens),
        'health_warnings': list(health_warnings),
        'overall_risk': overall,
    }