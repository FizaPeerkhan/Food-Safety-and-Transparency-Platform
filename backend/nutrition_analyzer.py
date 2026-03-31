import re

NUTRIENT_THRESHOLDS = {
    'calories': {'unit': 'kcal', 'high': 400, 'moderate': 200, 'worse': True,
                 'advice_high': 'High calorie density — watch portion size.'},
    'total_fat': {'unit': 'g', 'high': 20, 'moderate': 10, 'worse': True,
                  'advice_high': 'High fat content.'},
    'saturated_fat': {'unit': 'g', 'high': 5, 'moderate': 2, 'worse': True,
                      'advice_high': 'High saturated fat — raises cholesterol.'},
    'trans_fat': {'unit': 'g', 'high': 0.5, 'moderate': 0, 'worse': True,
                  'advice_high': 'Trans fats detected — harmful for health.'},
    'sodium': {'unit': 'mg', 'high': 600, 'moderate': 300, 'worse': True,
               'advice_high': 'Very high sodium — hypertension patients should limit.'},
    'sugar': {'unit': 'g', 'high': 22.5, 'moderate': 11, 'worse': True,
              'advice_high': 'High sugar content — diabetics should limit.'},
    'added_sugar': {'unit': 'g', 'high': 10, 'moderate': 5, 'worse': True,
                    'advice_high': 'High added sugar content.'},
    'fiber': {'unit': 'g', 'good': 6, 'moderate': 3, 'worse': False,
              'advice_low': 'Low fiber — pair with vegetables.'},
    'protein': {'unit': 'g', 'good': 10, 'moderate': 5, 'worse': False,
                'advice_low': 'Low protein content.'},
}

def parse_nutrition_text(text):
    """Parse nutrition text and extract numeric values"""
    if not text:
        return {}
    
    t = text.lower()
    result = {}
    
    patterns = {
        'calories': [r'(?:energy|calories?)[:\s]*(\d+(?:\.\d+)?)\s*(?:kcal|cal)?', r'(\d+(?:\.\d+)?)\s*kcal'],
        'total_fat': [r'(?:total\s+)?fat[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'saturated_fat': [r'saturated[:\s]*(\d+(?:\.\d+)?)\s*g', r'sat\.?\s*fat[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'trans_fat': [r'trans[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'sodium': [r'sodium[:\s]*(\d+(?:\.\d+)?)\s*(mg|g)', r'salt[:\s]*(\d+(?:\.\d+)?)\s*(mg|g)'],
        'sugar': [r'(?:total\s+)?sugar[s]?[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'added_sugar': [r'added\s+sugar[s]?[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'fiber': [r'(?:dietary\s+)?fiber[:\s]*(\d+(?:\.\d+)?)\s*g'],
        'protein': [r'protein[s]?[:\s]*(\d+(?:\.\d+)?)\s*g'],
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
            "value": val, "unit": unit, "status": status,
            "message": msg, "percentage": min(val * 2, 100), "bar_color": bar
        })
 
    score = max(0, min(100, score))
    rating = 'Excellent' if score >= 80 else 'Good' if score >= 60 else 'Fair' if score >= 40 else 'Poor'
    rating_color = {'Excellent': '#38a169', 'Good': '#68d391', 'Fair': '#ed8936', 'Poor': '#e53e3e'}[rating]
 
    parts = []
    if issues: parts.append(f"This product is high in {' and '.join(issues)}")
    if cautions: parts.append(f"moderate in {' and '.join(cautions)}")
 
    advice_groups = []
    if data.get('sodium', 0) > 600 or data.get('saturated_fat', 0) > 5:
        advice_groups.append('hypertension or heart conditions')
    if data.get('sugar', 0) > 22.5:
        advice_groups.append('diabetes')
    if data.get('calories', 0) > 400:
        advice_groups.append('weight management')
 
    verdict = '. '.join(parts) + '.' if parts else 'Nutritional profile looks balanced.'
    if advice_groups:
        verdict += f" People managing {', '.join(advice_groups)} should limit consumption."
 
    return {
        'health_score': score, 'rating': rating, 'rating_color': rating_color,
        'nutrients': nutrients, 'verdict': verdict,
    }