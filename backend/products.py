import requests
import mysql.connector
import time

# -----------------------------
# Database Connection
# -----------------------------
db = mysql.connector.connect(
    host="localhost",
    port=330,
    user="root",
    password="r00t",
    database="food_safety"
)

cursor = db.cursor()

# -----------------------------
# Create Products Table (Safe)
# -----------------------------
cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_name VARCHAR(255),
        brand VARCHAR(255),
        ingredients_text TEXT,
        country VARCHAR(100),
        UNIQUE(product_name, brand)
    )
""")

db.commit()

# -----------------------------
# Search Terms (Indian Focused)
# -----------------------------
search_terms = [
    "biscuit india",
    "namkeen india",
    "maggi india",
    "chips india",
    "chocolate india",
    "noodles india",
    "juice india",
    "bournvita india",
    "parle india",
    "britannia india",
    "haldiram india",
    "kurkure india",
    "frooti india",
    "amul india",
    "nestle india"
]

inserted = 0
skipped = 0

print("\nStarting product seeding...\n")

for term in search_terms:
    print(f"Searching: {term}")

    try:
        url = "https://world.openfoodfacts.org/api/v2/search"
        params = {
            "search_terms": term,
            "page_size": 20,
            "fields": "product_name,brands,ingredients_text,countries"
        }

        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        products = data.get("products", [])

        print(f"  Found {len(products)} products")

        for p in products:
            name = (p.get("product_name") or "").strip().lower()
            brand = (p.get("brands") or "").strip().lower()
            ingredients = (p.get("ingredients_text") or "").strip().lower()
            country = (p.get("countries") or "").strip().lower()

            # Skip incomplete data
            if not name or not ingredients:
                skipped += 1
                continue

            if len(ingredients) < 10:
                skipped += 1
                continue

            # Insert safely (ignore duplicates)
            cursor.execute("""
                INSERT IGNORE INTO products
                (product_name, brand, ingredients_text, country)
                VALUES (%s, %s, %s, %s)
            """, (name, brand, ingredients, country))

            if cursor.rowcount > 0:
                inserted += 1
                print(f"  Added: {name} — {brand}")
            else:
                skipped += 1

        db.commit()
        time.sleep(2)  # polite delay

    except requests.exceptions.Timeout:
        print(f"  Timeout on '{term}' — skipping")
        continue

    except requests.exceptions.RequestException as e:
        print(f"  API error on '{term}': {e}")
        continue

    except Exception as e:
        print(f"  Unexpected error on '{term}': {e}")
        continue

cursor.close()
db.close()

print("\n" + "=" * 50)
print(f"Done! Inserted: {inserted}")
print(f"Skipped (duplicates/missing): {skipped}")
print("=" * 50)
print("\nYou can now test:")
print("http://127.0.0.1:5000/search?name=maggi")