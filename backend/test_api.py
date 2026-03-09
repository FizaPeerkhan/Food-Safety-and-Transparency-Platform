import mysql.connector

try:
    db = mysql.connector.connect(
        host="localhost",
        port=330,
        user="root",
        password="r00t",  # put your exact MySQL password here
        database="food_safety"
    )
    print("Database connected successfully!")
    db.close()
except Exception as e:
    print("Error:", e)