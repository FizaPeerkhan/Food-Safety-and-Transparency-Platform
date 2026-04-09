import re
from config import get_db, INS_MAP

# Debunked ingredients (educational info for common additives)
DEBUNKED_INGREDIENTS = {
    'thickener': {
        'explanation': 'Thickeners increase viscosity. Most are plant-based (guar gum, xanthan gum) and generally safe.',
        'risk_level': 'Info', 
        'caution_group': ''
    },
    'acidity regulator': {
        'explanation': 'Acidity regulators control pH. Citric acid occurs naturally in citrus fruits. Generally safe.',
        'risk_level': 'Info', 
        'caution_group': ''
    },
    'humectant': {
        'explanation': 'Humectants retain moisture in foods. They occur naturally and are considered safe.',
        'risk_level': 'Info', 
        'caution_group': ''
    },
    'flavour enhancer': {
        'explanation': 'Flavour enhancers amplify existing flavors. Most are naturally derived and safe.',
        'risk_level': 'Info', 
        'caution_group': ''
    },
    'emulsifier': {
        'explanation': 'Emulsifiers help mix oil and water. Lecithin is naturally found in eggs and soy.',
        'risk_level': 'Info', 
        'caution_group': ''
    },
    'stabilizer': {
        'explanation': 'Stabilizers maintain food texture. Most are plant-based and generally safe.',
        'risk_level': 'Info', 
        'caution_group': ''
    },
    'preservative': {
        'explanation': 'Preservatives prevent spoilage. Many are safe in approved amounts.',
        'risk_level': 'Info', 
        'caution_group': ''
    },
    'antioxidant': {
        'explanation': 'Antioxidants prevent oxidation. Natural ones like vitamin C are beneficial.',
        'risk_level': 'Info', 
        'caution_group': ''
    },
    'raising agent': {
        'explanation': 'Raising agents (baking soda, baking powder) help baked goods rise.',
        'risk_level': 'Info', 
        'caution_group': ''
    },
    'colour': {
        'explanation': 'Colours add or restore color to foods. Natural colours are safe; some artificial colours may cause sensitivity.',
        'risk_level': 'Info',
        'caution_group': ''
    },
    'color': {
        'explanation': 'Colours add or restore color to foods. Natural colours are safe; some artificial colours may cause sensitivity.',
        'risk_level': 'Info',
        'caution_group': ''
    }
}

import re

def parse_ingredients(text):
    """
    Parse ingredients from CSV format with proper handling of:
    - " and " as separator
    - " & " as separator
    - Dots '.' as separators (but not decimal points)
    - Brackets (), {}, [] 
    - INS/E-numbers preservation
    - Percentage removal
    """
    if not text:
        return []

    text = str(text)
    
    # Step 1: Mark bracket regions to preserve them during replacement
    bracket_regions = []
    depth = 0
    bracket_start = -1
    
    for i, char in enumerate(text):
        if char in '([{':
            if depth == 0:
                bracket_start = i
            depth += 1
        elif char in ')]}':
            depth -= 1
            if depth == 0 and bracket_start != -1:
                bracket_regions.append((bracket_start, i))
                bracket_start = -1
    
    # Create a list of characters for manipulation
    chars = list(text)
    
    # Mark which positions are inside brackets
    inside_bracket = [False] * len(text)
    for start, end in bracket_regions:
        for j in range(start, end + 1):
            if j < len(inside_bracket):
                inside_bracket[j] = True
    
    # Step 2: Replace separators outside brackets
    i = 0
    while i < len(chars):
        if not inside_bracket[i]:
            # Check for " and " (with spaces)
            if i + 5 <= len(chars) and ''.join(chars[i:i+5]).lower() == ' and ':
                chars[i] = ','
                for j in range(i+1, i+5):
                    chars[j] = ''
                i += 5
                continue
            
            # Check for " & " (with spaces)
            elif i + 3 <= len(chars) and ''.join(chars[i:i+3]).lower() == ' & ':
                chars[i] = ','
                for j in range(i+1, i+3):
                    chars[j] = ''
                i += 3
                continue
            
            # Check for dot '.' as separator (not decimal point)
            # A dot is a separator if:
            # 1. It's not part of a number (e.g., 2.5)
            # 2. It has spaces around or is followed by space
            elif chars[i] == '.':
                # Check if it's a decimal point (number.number)
                is_decimal = False
                if i > 0 and i + 1 < len(chars):
                    left_is_digit = chars[i-1].isdigit()
                    right_is_digit = chars[i+1].isdigit()
                    if left_is_digit and right_is_digit:
                        is_decimal = True
                
                if not is_decimal:
                    # Check if dot has space before/after or is at sentence end
                    if (i > 0 and chars[i-1] == ' ') or (i + 1 < len(chars) and chars[i+1] == ' '):
                        chars[i] = ','
        i += 1
    
    modified_text = ''.join(chars)
    
    # Step 3: Split by commas, respecting brackets
    parts = []
    current = []
    depth = 0
    
    for char in modified_text:
        if char in '([{':
            depth += 1
            current.append(char)
        elif char in ')]}':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            if current:
                part = ''.join(current).strip()
                if part:
                    parts.append(part)
                current = []
        else:
            current.append(char)
    
    if current:
        part = ''.join(current).strip()
        if part:
            parts.append(part)
    
    # Step 4: Process each part
    seen = set()
    result = []
    
    for part in parts:
        if not part:
            continue
        
        # Remove trailing "and" (without spaces)
        part = re.sub(r'\s+and\s*$', '', part)
        part = re.sub(r'&$', '', part)
        
        # Check if this part contains INS/E numbers
        has_ins = bool(re.search(r'(?:INS|E)\s*\d+', part, re.IGNORECASE))
        
        if has_ins:
            # Keep INS numbers, remove only standalone percentages
            # Example: "Thickeners (508 & 412)" → keep as is
            # But remove "23.6%" if standalone
            clean = re.sub(r'\s*\(\s*\d+(?:\.\d+)?\s*%\s*\)', '', part)
            clean = re.sub(r'\s*\{\s*\d+(?:\.\d+)?\s*%\s*\}', '', clean)
            clean = re.sub(r'\s*\[\s*\d+(?:\.\d+)?\s*%\s*\]', '', clean)
            clean = re.sub(r'\s*\d+(?:\.\d+)?\s*%', '', clean)
        else:
            # Remove all bracket content for non-INS ingredients
            # Example: "Wheat Flour (67%)" → "Wheat Flour"
            clean = re.sub(r'[\(\[{][^\]\)}{]*[\]\)}]', '', part)
            clean = re.sub(r'\s*\d+(?:\.\d+)?\s*%', '', clean)
        
        # Clean up extra spaces
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        # Remove leading/trailing punctuation
        clean = clean.strip(' ,;:.-_')
        
        # Remove trailing "and" and "&" again
        clean = re.sub(r'\s+and\s*$', '', clean)
        clean = re.sub(r'\s*&\s*$', '', clean)
        
        # Skip empty or too short
        if not clean or len(clean) < 2:
            continue
        
        # Skip if it's just a number
        if re.match(r'^\d+(?:\.\d+)?$', clean):
            continue
        
        # Skip if it's just a percentage
        if re.match(r'^\d+(?:\.\d+)?\s*%$', clean):
            continue
        
        # Deduplicate (case-insensitive)
        key = clean.lower()
        if key not in seen:
            seen.add(key)
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

def extract_ins_with_parent(ingredient_text):
    """
    Extract INS numbers and associate them with their parent ingredient.
    Returns: (clean_ingredient_name, ins_list)
    """
    if not ingredient_text:
        return ingredient_text, []
    
    # Find INS numbers in the text
    ins_pattern = r'(?:INS|E)\s*(\d{2,4}[a-z]?)'
    ins_matches = re.findall(ins_pattern, ingredient_text, re.IGNORECASE)
    
    # Remove INS brackets for clean name
    clean = re.sub(r'\s*[\(\[{][^\]\)}{]*[\]\)}]', '', ingredient_text)
    clean = re.sub(r'\s*\d+(?:\.\d+)?\s*%', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    return clean, ins_matches

def get_debunked_info(ingredient):
    """Return debunked info for common additive categories"""
    ingredient_lower = ingredient.lower()
    for key, info in DEBUNKED_INGREDIENTS.items():
        if key in ingredient_lower:
            return info
    return None

def build_ingredient_analysis(ingredient_list, cursor):
    """
    Single source of truth for ingredient risk analysis.
    Preserves INS numbers and handles debunked ingredients.
    """
    seen_ingredients = set()
    all_ingredients = []
    high_risk = []
    moderate_risk = []
    info_ingredients = []  # For debunked/info ingredients
    allergens = set()
    health_warnings = set()
    
    for ing in ingredient_list:
        # First, extract INS numbers from this ingredient
        clean_ingredient, ins_codes = extract_ins_with_parent(ing)
        
        # Check for debunked additives first
        debunked = get_debunked_info(clean_ingredient)
        if debunked:
            # This is an educational/info ingredient
            info_ingredients.append({
                'name': ing,
                'clean_name': clean_ingredient,
                'category': 'Food Additive',
                'risk_level': 'Info',
                'explanation': debunked['explanation'],
                'flagged': False,
                'is_debunked': True,
                'ins_codes': ins_codes
            })
            all_ingredients.append({
                'name': ing,
                'category': 'Food Additive',
                'risk_level': 'Info',
                'explanation': debunked['explanation'],
                'flagged': False,
                'is_debunked': True
            })
            continue
        
        # Search in database using the clean ingredient name
        search_term = clean_ingredient[:30]  # Limit search length
        cursor.execute("""
            SELECT * FROM ingredients
            WHERE LOWER(%s) LIKE CONCAT('%%', LOWER(ingredient_name), '%%')
               OR LOWER(ingredient_name) LIKE CONCAT('%%', LOWER(%s), '%%')
            LIMIT 1
        """, (search_term, search_term))
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
                        'clean_name': clean_ingredient,
                        'category': category,
                        'risk_level': row['risk_level'],
                        'explanation': row.get('explanation', ''),
                        'caution_for': caution,
                        'allergen': allergen,
                        'ins_codes': ins_codes
                    }
                    if row['risk_level'] == 'High':
                        high_risk.append(entry)
                        health_warnings.add(f"{row['ingredient_name']} → Avoid for: {caution}")
                    elif row['risk_level'] == 'Moderate':
                        moderate_risk.append(entry)
                        health_warnings.add(f"{row['ingredient_name']} → Caution for: {caution}")
                    
                    if allergen:
                        allergens.add(allergen)
        else:
            # Ingredient not found in database - add as unknown but keep INS if present
            risk_level = 'Unknown'
        
        all_ingredients.append({
            'name': ing,
            'clean_name': clean_ingredient,
            'category': category,
            'risk_level': risk_level,
            'ins_codes': ins_codes,
            'flagged': flagged,
            'is_debunked': False
        })
    
    overall = 'High' if high_risk else ('Moderate' if moderate_risk else 'Low')
    
    return {
        'all_ingredients': all_ingredients,
        'high_risk_ingredients': high_risk,
        'moderate_risk_ingredients': moderate_risk,
        'info_ingredients': info_ingredients,
        'allergens': list(allergens),
        'health_warnings': list(health_warnings),
        'overall_risk': overall,
    }