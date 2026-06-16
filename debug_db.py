import mysql.connector
try:
    conn = mysql.connector.connect(host='localhost', user='root', password='root@123')
    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES LIKE 'smartbuy_db'")
    dbs = cursor.fetchall()
    print("Databases:", dbs)
    if dbs:
        cursor.execute("USE smartbuy_db")
        cursor.execute("SHOW TABLES")
        print("Tables:", cursor.fetchall())
        
        cursor.execute("SELECT * FROM users")
        print("Users:", cursor.fetchall())
    else:
        print("Database smartbuy_db does not exist!")
except Exception as e:
    print("Error:", e)
