import os
import pymysql
from pymysql import Error
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration from .env
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'food_safety'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'port': int(os.environ.get('DB_PORT', 330)),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Upload configuration
UPLOAD_FOLDER = 'uploads'
EVIDENCE_FOLDER = 'evidence'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'pdf'}

# Tesseract OCR path (update for your OS)
TESSERACT_PATH = os.environ.get('TESSERACT_PATH', r'C:\Program Files\Tesseract-OCR\tesseract.exe')

def get_db():
    """Get database connection using PyMySQL"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print("✅ Database connected successfully")
        return connection
    except Error as e:
        print(f"❌ Database connection error: {e}")
        return None

# INS Map for fallback when database doesn't have the INS number
INS_MAP = {
    '440': 'Pectin',
    '223': 'Sodium Metabisulfite',
    '260': 'Acetic Acid',
    '270': 'Lactic Acid',
    '282': 'Calcium Propionate',
    '290': 'Carbon Dioxide',
    '296': 'Malic Acid',
    '300': 'Ascorbic Acid',
    '319': 'TBHQ',
    '320': 'BHA',
    '321': 'BHT',
    '322': 'Lecithin',
    '325': 'Sodium Lactate',
    '330': 'Citric Acid',
    '331': 'Sodium Citrate',
    '334': 'Tartaric Acid',
    '338': 'Phosphoric Acid',
    '340': 'Potassium Phosphate',
    '341': 'Calcium Phosphate',
    '401': 'Sodium Alginate',
    '406': 'Agar Agar',
    '407': 'Carrageenan',
    '412': 'Guar Gum',
    '414': 'Gum Arabic',
    '415': 'Xanthan Gum',
    '416': 'Karaya Gum',
    '420': 'Sorbitol',
    '421': 'Mannitol',
    '422': 'Glycerol',
    '431': 'Polyoxyethylene Stearate',
    '432': 'Polysorbate 20',
    '433': 'Polysorbate 80',
    '435': 'Polysorbate 60',
    '436': 'Polysorbate 65',
    '450': 'Diphosphates',
    '451': 'Triphosphates',
    '452': 'Polyphosphates',
    '460': 'Cellulose',
    '461': 'Methyl Cellulose',
    '466': 'CMC',
    '471': 'Mono- and Diglycerides',
    '472': 'Esters of Mono/Diglycerides',
    '473': 'Sucrose Esters',
    '475': 'Polyglycerol Esters',
    '476': 'PGPR',
    '477': 'Propylene Glycol Esters',
    '481': 'Sodium Stearoyl Lactylate',
    '482': 'Calcium Stearoyl Lactylate',
    '491': 'Sorbitan Monostearate',
    '492': 'Sorbitan Tristearate',
    '500': 'Sodium Carbonate',
    '501': 'Potassium Carbonate',
    '503': 'Ammonium Carbonate',
    '504': 'Magnesium Carbonate',
    '508': 'Potassium Chloride',
    '509': 'Calcium Chloride',
    '511': 'Magnesium Chloride',
}