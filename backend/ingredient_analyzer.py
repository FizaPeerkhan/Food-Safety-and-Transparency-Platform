import re
from config import get_db

# ==================== DEBUNKED INGREDIENTS (FALLBACK ONLY) ====================
# These are ONLY for generic category words that won't be found in DB
# e.g., "thickeners (508 & 412)" - the word "thickener" isn't a DB row
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
    }
}

# ==================== PARSER ====================
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

        # remove percentages
        part = re.sub(r'\b\d+(\.\d+)?\s*%', '', part).strip()

        # remove junk tokens
        if re.fullmatch(r'\d+[a-z]?\)?', part):
            continue

        if len(part) <= 1:
            continue

        # remove broken bracket parts
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
    """Return debunked info for common additive categories (FALLBACK ONLY)"""
    if isinstance(ingredient, dict):
        ingredient = ingredient.get("name", "")
    
    if not ingredient:
        return None
        
    ingredient_lower = ingredient.lower()
    
    for key, info in DEBUNKED_INGREDIENTS.items():
        if key in ingredient_lower:
            return {
                'explanation': info.get('explanation', 'Generally safe ingredient'),
                'risk_level': 'Info',
                'caution_group': ''
            }
    return None

# ==================== HELPER FUNCTIONS ====================
GENERAL_GROUPS = {
    'general consumers', 'general consumer', 'general',
    'generally safe', 'none', ''
}

def _query_ingredient(name_lower, cursor):
    """Query database for ingredient by name"""
    cursor.execute("""
        SELECT * FROM ingredients
        WHERE LOWER(ingredient_name) LIKE %s
        LIMIT 1
    """, (f'%{name_lower[:25]}%',))
    return cursor.fetchone()

def _has_db_match(name_lower, cursor):
    """Check if ingredient exists in database"""
    cursor.execute("""
        SELECT 1 FROM ingredients
        WHERE LOWER(ingredient_name) LIKE %s
        LIMIT 1
    """, (f'%{name_lower[:25]}%',))
    return cursor.fetchone() is not None

def _process_subs(subs, cursor, seen_ingredients, all_ingredients, 
                  high_risk, moderate_risk, allergens, health_warnings):
    """Process sub-ingredients (e.g., 508, 412 from thickeners (508 & 412))"""
    for sub in subs:
        sub_lower = (sub or '').lower().strip()

        # Skip bare INS codes — extract_ins_numbers handles those
        if re.match(r'^(ins\s*)?\d{2,4}[a-z]?$', sub_lower):
            continue
        if not sub_lower or len(sub_lower) <= 1 or sub_lower in seen_ingredients:
            continue

        seen_ingredients.add(sub_lower)
        row = _query_ingredient(sub_lower, cursor)

        if not row:
            all_ingredients.append({
                'name': sub,
                'category': 'Sub-ingredient',
                'risk_level': None,
                'explanation': '',
                'flagged': False,
                'is_debunked': False
            })
            continue

        caution = str(row.get('caution_group') or '').strip()
        allergen = str(row.get('allergen_type') or '').strip()
        risk_level = row.get('risk_level', 'Low')
        is_general = caution.lower() in GENERAL_GROUPS

        if allergen.lower() in {'null', 'nan', 'none', ''}:
            allergen = None

        flagged = False
        if risk_level in ('High', 'Moderate'):
            should_flag = (
                not is_general or
                'general population' in caution.lower() or
                'long-term risk' in caution.lower()
            )
            if should_flag:
                flagged = True
                key = row['ingredient_name'].lower()
                if key not in seen_ingredients:
                    seen_ingredients.add(key)
                    entry = {
                        'ingredient': row['ingredient_name'],
                        'original_text': sub,
                        'category': row.get('category', ''),
                        'risk_level': risk_level,
                        'explanation': row.get('explanation', ''),
                        'caution_for': caution if not is_general else 'General population',
                        'allergen': allergen,
                        'is_debunked': False
                    }
                    if risk_level == 'High':
                        high_risk.append(entry)
                    else:
                        moderate_risk.append(entry)
                if allergen:
                    allergens.add(allergen)
                if caution and not is_general:
                    health_warnings.add(
                        f"{row['ingredient_name']} → Caution for: {caution}"
                    )

        all_ingredients.append({
            'name': sub,
            'category': row.get('category', 'Sub-ingredient'),
            'risk_level': risk_level,
            'explanation': row.get('explanation', ''),
            'flagged': flagged,
            'is_debunked': False
        })

# ==================== MAIN ANALYZER ====================
def build_ingredient_analysis(ingredient_list, cursor):
    seen_ingredients = set()
    all_ingredients = []
    high_risk = []
    moderate_risk = []
    allergens = set()
    health_warnings = set()

    for ing in ingredient_list:
        if isinstance(ing, dict):
            name = ing.get('name', '')
            subs = ing.get('sub', [])
        else:
            name = str(ing)
            subs = []

        name_lower = (name or '').lower().strip()
        if not name_lower or name_lower in seen_ingredients:
            continue

        # ── DEBUNK CHECK FIRST (FALLBACK ONLY) ─────────────────────────
        # Only use DEBUNKED_INGREDIENTS for category words that
        # would never appear verbatim in the DB
        # e.g., "thickeners (508 & 412)" — the word "thickener" isn't a DB row
        debunked = get_debunked_info(name)
        if debunked and not _has_db_match(name_lower, cursor):
            seen_ingredients.add(name_lower)
            all_ingredients.append({
                'name': name,
                'category': 'Food Additive',
                'risk_level': 'Info',
                'explanation': debunked.get('explanation', ''),
                'flagged': False,
                'is_debunked': True
            })
            # Still process sub-items (e.g., 508, 412)
            _process_subs(subs, cursor, seen_ingredients,
                          all_ingredients, high_risk, moderate_risk,
                          allergens, health_warnings)
            continue

        # ── DB LOOKUP ──────────────────────────────────────────────────
        row = _query_ingredient(name_lower, cursor)

        if not row:
            # Not in DB at all — show as neutral
            seen_ingredients.add(name_lower)
            all_ingredients.append({
                'name': name,
                'category': 'General Ingredient',
                'risk_level': None,
                'explanation': '',
                'flagged': False,
                'is_debunked': False
            })
            _process_subs(subs, cursor, seen_ingredients,
                          all_ingredients, high_risk, moderate_risk,
                          allergens, health_warnings)
            continue

        # ── ROW EXISTS — use DB values directly ────────────────────────
        caution = str(row.get('caution_group') or '').strip()
        allergen = str(row.get('allergen_type') or '').strip()
        risk_level = row.get('risk_level', 'Low')
        category = row.get('category', 'General Ingredient')
        explanation = row.get('explanation', '')

        if allergen.lower() in {'null', 'nan', 'none', ''}:
            allergen = None

        is_general = caution.lower() in GENERAL_GROUPS

        seen_ingredients.add(name_lower)

        # ── KEY LOGIC CHANGE ───────────────────────────────────────────
        # Show ALL ingredients in the tag cloud with their DB category.
        # Only FLAG (add to risk lists) if:
        #   - risk is High or Moderate AND
        #   - caution group is specific (not general)
        #
        # Low risk + general = show in tag cloud only, no warning
        # Low risk + specific caution = show info (e.g., hypertension patients)
        # Moderate/High + general = still flag (e.g., "General population")
        # Moderate/High + specific = flag with caution group

        flagged = False

        if risk_level in ('High', 'Moderate'):
            # Flag if caution is specific OR if it affects general population
            should_flag = (
                not is_general or
                'general population' in caution.lower() or
                'long-term risk' in caution.lower()
            )
            if should_flag:
                flagged = True
                key = row['ingredient_name'].lower()
                if key not in seen_ingredients:
                    seen_ingredients.add(key)
                    entry = {
                        'ingredient': row['ingredient_name'],
                        'original_text': name,
                        'category': category,
                        'risk_level': risk_level,
                        'explanation': explanation,
                        'caution_for': caution if not is_general else 'General population',
                        'allergen': allergen,
                        'is_debunked': False
                    }
                    if risk_level == 'High':
                        high_risk.append(entry)
                    elif risk_level == 'Moderate':
                        moderate_risk.append(entry)

                if allergen:
                    allergens.add(allergen)

                if caution and not is_general:
                    health_warnings.add(
                        f"{row['ingredient_name']} → Caution for: {caution}"
                    )
                elif 'general population' in caution.lower():
                    health_warnings.add(
                        f"{row['ingredient_name']} → Long-term risk for general population"
                    )

        elif risk_level == 'Low' and not is_general:
            # Low risk but specific caution (e.g., INS 508 → Hypertension patients)
            # Show as info, not a warning
            flagged = False  # don't add to risk lists

        all_ingredients.append({
            'name': name,
            'category': category,      # always from DB
            'risk_level': risk_level,  # always from DB
            'explanation': explanation, # always from DB
            'flagged': flagged,
            'is_debunked': False
        })

        _process_subs(subs, cursor, seen_ingredients,
                      all_ingredients, high_risk, moderate_risk,
                      allergens, health_warnings)

    overall = 'High' if high_risk else ('Moderate' if moderate_risk else 'Low')
    
    return {
        'all_ingredients': all_ingredients,
        'high_risk_ingredients': high_risk,
        'moderate_risk_ingredients': moderate_risk,
        'allergens': list(allergens),
        'health_warnings': list(health_warnings),
        'overall_risk': overall
    }