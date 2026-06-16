import mysql.connector

try:
    print("Connecting to MySQL database...")
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root@123',
        database='smartbuy_db'
    )
    cursor = conn.cursor()
    
    print("Checking if 'customer_name' column already exists in 'orders' table...")
    cursor.execute("SHOW COLUMNS FROM orders LIKE 'customer_name'")
    result = cursor.fetchone()
    
    if not result:
        print("Column 'customer_name' not found. Adding column...")
        cursor.execute("ALTER TABLE orders ADD COLUMN customer_name VARCHAR(100) AFTER user_id")
        conn.commit()
        print("Column 'customer_name' added successfully!")
    else:
        print("Column 'customer_name' already exists!")
        
    cursor.close()
    conn.close()
    print("Database upgrade complete.")
    
except Exception as e:
    print("Error during database upgrade:", e)
