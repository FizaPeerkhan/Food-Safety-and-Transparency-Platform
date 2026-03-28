import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    port=330,
    user="root",
    password="r00t",
    database="food_safety"
)

cursor = conn.cursor()

# Check products table columns
print("Products table columns:")
cursor.execute("SHOW COLUMNS FROM Ingredients")
for col in cursor.fetchall():
    print(f"  {col[0]}")

print("\n" + "="*50)

# Check a sample product
print("\nSample product:")
cursor.execute("SELECT * FROM products LIMIT 1")
row = cursor.fetchone()
if row:
    cursor.execute("SHOW COLUMNS FROM products")
    columns = [col[0] for col in cursor.fetchall()]
    for i, col in enumerate(columns):
        print(f"  {col}: {row[i]}")
else:
    print("No products found")

cursor.close()
conn.close()