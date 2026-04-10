import re
from config import get_db

# ==================== DEBUNKED INGREDIENTS ====================
DEBUNKED_INGREDIENTS = {
    'thickener': {'explanation': 'Generally safe plant-based thickener', 'risk_level': 'Low', 'caution_group': ''},
    'acidity regulator': {'explanation': 'Controls pH, usually safe', 'risk_level': 'Low', 'caution_group': ''},
    'humectant': {'explanation': 'Retains moisture, generally safe', 'risk_level': 'Low', 'caution_group': ''},
    'flavour enhancer': {'explanation': 'Enhances taste', 'risk_level': 'Low', 'caution_group': ''},
    'emulsifier': {'explanation': 'Helps mix oil and water', 'risk_level': 'Low', 'caution_group': ''},
    'stabilizer': {'explanation': 'Maintains texture', 'risk_level': 'Low', 'caution_group': ''},
    'preservative': {'explanation': 'Prevents spoilage', 'risk_level': 'Low', 'caution_group': ''},
    'antioxidant': {'explanation': 'Prevents oxidation', 'risk_level': 'Low', 'caution_group': ''},
    'raising agent': {'explanation': 'Helps food rise', 'risk_level': 'Low', 'caution_group': ''}
}

# ==================== PARSER ====================
import re


def parse_ingredients(text):
    if not text:
        return []

    text = text.lower()
    ingredients = []
    seen = set()

    # protect brackets
    bracket_contents = []

    def replace_bracket(match):
        bracket_contents.append(match.group(0))
        return f"__BRACKET_{len(bracket_contents)-1}__"

    text = re.sub(r'\([^)]*\)', replace_bracket, text)

    # split safely
    parts = re.split(r',|\band\b|&|(?<!\d)\.(?!\d)', text)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # restore brackets
        for i, b in enumerate(bracket_contents):
            part = part.replace(f"__BRACKET_{i}__", b)

        # 🔥 remove percentages
        part = re.sub(r'\b\d+(\.\d+)?\s*%', '', part).strip()

        # ❌ remove junk tokens
        if re.fullmatch(r'\d+[a-z]?\)?', part):  # 500, 412
            continue

        if len(part) <= 1:  # i
            continue

        # ❌ remove broken bracket parts
        if part.count('(') != part.count(')'):
            continue

        if part.endswith('(') or (part.endswith(')') and '(' not in part):
            continue

        # colon case
        if ':' in part:
            parent, rest = part.split(':', 1)
            parent = parent.strip()
            rest = rest.strip()

            if parent and parent not in seen:
                ingredients.append({
                    "name": parent,
                    "sub": [rest]
                })
                seen.add(parent)
            continue

        # bracket case
        bracket_match = re.search(r'(.*?)\((.*?)\)', part)

        if bracket_match:
            parent = bracket_match.group(1).strip()
            inside = bracket_match.group(2)

            subs = re.split(r',|\band\b|&', inside)
            subs = [
                re.sub(r'\b\d+(\.\d+)?\s*%', '', s).strip()
                for s in subs if s.strip()
            ]

            if parent and parent not in seen:
                ingredients.append({
                    "name": parent,
                    "sub": subs
                })
                seen.add(parent)

            continue

        # normal case
        clean = part.strip()

        if clean and clean not in seen:
            ingredients.append({
                "name": clean,
                "sub": []
            })
            seen.add(clean)

    return ingredients
# ==================== INS EXTRACTION ====================
def extract_ins_numbers(text, cursor):
    if not text:
        return []

    matches = re.findall(r'(?:INS|E)[-.\s]*(\d{2,4}[a-z]?)', text, re.IGNORECASE)

    results = []
    seen = set()

    for code in matches:
        code_upper = code.upper()
        if code_upper in seen:
            continue
        seen.add(code_upper)

        cursor.execute("""
            SELECT * FROM ingredients 
            WHERE LOWER(ingredient_name) LIKE %s 
            LIMIT 1
        """, (f'%ins {code_upper.lower()}%',))

        row = cursor.fetchone()

        if row:
            results.append({
                'code': f'INS {code_upper}',
                'name': row.get('ingredient_name'),
                'category': row.get('category'),
                'risk_level': row.get('risk_level'),
                'explanation': row.get('explanation'),
                'caution': row.get('caution_group'),
                'allergen': row.get('allergen_type')
            })
        else:
            results.append({
                'code': f'INS {code_upper}',
                'name': f'Additive {code_upper}',
                'risk_level': 'Unknown'
            })

    return results

# ==================== DEBUNK HANDLER ====================
def get_debunked_info(ingredient):
    if isinstance(ingredient, dict):
        ingredient = ingredient.get("name", "")
    ingredient_lower = (ingredient or "").lower()

    for key, info in DEBUNKED_INGREDIENTS.items():
        if key in ingredient_lower:
            return info
    return None

# ==================== MAIN ANALYZER ====================
def build_ingredient_analysis(ingredient_list, cursor):
    seen_ingredients = set()

    all_ingredients = []
    high_risk = []
    moderate_risk = []
    allergens = set()
    health_warnings = set()

    for ing in ingredient_list:

        # Handle dict or string
        if isinstance(ing, dict):
            name = ing.get("name", "")
            subs = ing.get("sub", [])
        else:
            name = ing
            subs = []

        name_lower = (name or "").lower()

        # Debunk check
        debunked = get_debunked_info(name)
        if debunked:
            all_ingredients.append({
                'name': name,
                'category': 'Food Additive',
                'risk_level': 'Low',
                'flagged': False
            })
            continue

        # ✅ FIXED DB MATCHING
        cursor.execute("""
            SELECT * FROM ingredients
            WHERE LOWER(ingredient_name) LIKE %s
            LIMIT 1
        """, (f"%{name_lower}%",))

        row = cursor.fetchone()

        category = row.get('category', 'General Ingredient') if row else 'General Ingredient'
        risk_level = row.get('risk_level') if row else None
        flagged = False

        if row:
            caution = str(row.get('caution_group') or '').strip()
            allergen = str(row.get('allergen_type') or '').strip()

            if allergen.lower() in {'null', 'nan', 'none', ''}:
                allergen = None

            is_general = caution.lower() in {'general consumers', 'general', 'none', ''}

            if not is_general and caution:
                flagged = True

                key = row['ingredient_name'].lower()
                if key not in seen_ingredients:
                    seen_ingredients.add(key)

                    entry = {
                        'ingredient': row['ingredient_name'],
                        'original_text': name,
                        'category': category,
                        'risk_level': row['risk_level'],
                        'explanation': row.get('explanation'),
                        'caution_for': caution,
                        'allergen': allergen
                    }

                    if row['risk_level'] == 'High':
                        high_risk.append(entry)
                    elif row['risk_level'] == 'Moderate':
                        moderate_risk.append(entry)

                    if allergen:
                        allergens.add(allergen)

                    health_warnings.add(f"{row['ingredient_name']} → Avoid for: {caution}")

        all_ingredients.append({
            'name': name,
            'category': category,
            'risk_level': risk_level,
            'flagged': flagged
        })

        # Sub-ingredients handling
        for sub in subs:
            sub_lower = (sub or "").lower()

            cursor.execute("""
                SELECT * FROM ingredients
                WHERE LOWER(ingredient_name) LIKE %s
                LIMIT 1
            """, (f"%{sub_lower}%",))

            sub_row = cursor.fetchone()

            if sub_row and sub_row.get('risk_level') == 'High':
                high_risk.append({
                    'ingredient': sub_row['ingredient_name'],
                    'original_text': sub,
                    'category': sub_row.get('category'),
                    'risk_level': sub_row.get('risk_level'),
                    'explanation': sub_row.get('explanation'),
                    'caution_for': sub_row.get('caution_group'),
                    'allergen': sub_row.get('allergen_type')
                })

            all_ingredients.append({
                'name': sub,
                'category': sub_row.get('category') if sub_row else 'Sub Ingredient',
                'risk_level': sub_row.get('risk_level') if sub_row else None,
                'flagged': bool(sub_row)
            })

    overall = 'High' if high_risk else ('Moderate' if moderate_risk else 'Low')

    return {
        'all_ingredients': all_ingredients,
        'high_risk_ingredients': high_risk,
        'moderate_risk_ingredients': moderate_risk,
        'allergens': list(allergens),
        'health_warnings': list(health_warnings),
        'overall_risk': overall
    }