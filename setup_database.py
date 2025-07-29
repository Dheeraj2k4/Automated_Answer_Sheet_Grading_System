import mysql.connector
from mysql.connector import Error

def setup_database():
    try:
        # First connect without database
        connection = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='system'
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS teacher_part")
            print("Database created or already exists")
            
            # Switch to the database
            cursor.execute("USE teacher_part")
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Admins (
                    admin_id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(50) NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Students (
                    student_id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(50) NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Teachers (
                    teacher_id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(50) NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Tests (
                    test_id INT AUTO_INCREMENT PRIMARY KEY,
                    test_name VARCHAR(100) NOT NULL,
                    teacher_id INT,
                    FOREIGN KEY (teacher_id) REFERENCES Teachers(teacher_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Questions (
                    question_id INT AUTO_INCREMENT PRIMARY KEY,
                    question_text TEXT NOT NULL,
                    test_id INT,
                    FOREIGN KEY (test_id) REFERENCES Tests(test_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ExpectedAnswers (
                    answer_id INT AUTO_INCREMENT PRIMARY KEY,
                    answer_text TEXT NOT NULL,
                    question_id INT,
                    FOREIGN KEY (question_id) REFERENCES Questions(question_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS StudentAnswers (
                    answer_id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT,
                    test_id INT,
                    question_id INT,
                    answer_text TEXT,
                    score FLOAT,
                    FOREIGN KEY (student_id) REFERENCES Students(student_id),
                    FOREIGN KEY (test_id) REFERENCES Tests(test_id),
                    FOREIGN KEY (question_id) REFERENCES Questions(question_id)
                )
            """)
            
            # Insert default admin if not exists
            cursor.execute("SELECT * FROM Admins WHERE username = 'admin'")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO Admins (username, password) VALUES ('admin', 'admin123')")
                print("Default admin user created")
            
            connection.commit()
            print("All tables created successfully")
            
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
            
    except Error as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    setup_database() 