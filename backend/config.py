import mysql.connector
import os

# ==================== CONFIGURATION ====================
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# Tesseract path - UPDATE THIS TO YOUR ACTUAL PATH
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 330,
    'user': 'root',
    'password': 'r00t',
    'database': 'food_safety'
}

# ==================== DATABASE CONNECTION ====================
def get_db():
    """Get database connection"""
    return mysql.connector.connect(**DB_CONFIG)

# ==================== INS NUMBER MAPPING ====================
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