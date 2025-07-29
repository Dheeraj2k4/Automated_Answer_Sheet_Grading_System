import mysql.connector
from mysql.connector import Error

def test_connection():
    try:
        # Create connection
        connection = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='system',
            database='teacher_part'
        )
        
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Connected to MySQL Server version {db_info}")
            
            # Create cursor
            cursor = connection.cursor()
            
            # Execute query
            cursor.execute("select database();")
            record = cursor.fetchone()
            print(f"Connected to database: {record[0]}")
            
            # Show tables
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            print("\nTables in database:")
            for table in tables:
                print(table[0])
            
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
            
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")

if __name__ == "__main__":
    test_connection() 