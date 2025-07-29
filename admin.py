from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
import sys
import string
import pandas as pd
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings
from collections import defaultdict
import os
from werkzeug.utils import secure_filename
import shutil
from datetime import datetime
import json
import PyPDF2
import google.cloud.vision as vision
from scan.pdf_text_extractor import process_pdf_pypdf2
from scan.enhanced_evaluator import EnhancedEvaluator

warnings.filterwarnings("ignore")
nltk.download("stopwords")

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Set the template folder
app.template_folder = 'templates'

# MySQL Configuration
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'system',
    'database': 'teacher_part',
    'port': 3306
}

def get_db_connection():
    """Get a new database connection"""
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def test_db_connection():
    """Test MySQL connection"""
    try:
        print("\nAttempting to connect to MySQL...")
        print(f"Host: {MYSQL_CONFIG['host']}")
        print(f"User: {MYSQL_CONFIG['user']}")
        print(f"Database: {MYSQL_CONFIG['database']}")
        print(f"Port: {MYSQL_CONFIG['port']}")
        
        connection = get_db_connection()
        if connection is None:
            print("Failed to connect to MySQL")
            return False
            
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if result:
                print("MySQL connection successful!")
                return True
            else:
                print("MySQL connection failed: Query returned no results")
                return False
                
    except Exception as e:
        print(f"MySQL connection error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

def init_db():
    """Initialize the database and create tables if they don't exist"""
    try:
        # First connect without database
        connection = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password']
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
            return True
            
    except Error as e:
        print(f"Error initializing database: {e}")
        return False

# Initialize database when app starts
if not test_db_connection():
    print("Failed to connect to MySQL. Please check your MySQL server is running.")
elif not init_db():
    print("Failed to initialize database. Please check your MySQL configuration.")

# Set English stopwords
EN_STOPWORDS = set(stopwords.words("english"))

def preprocess_text(text):
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Remove stopwords
    words = text.split()
    words = [word for word in words if word not in EN_STOPWORDS]
    return ' '.join(words)

def enhanced_sentence_match(expected_answer, student_answer):
    """Calculate similarity between expected and student answers using TF-IDF and cosine similarity"""
    # Preprocess both answers
    expected_processed = preprocess_text(expected_answer)
    student_processed = preprocess_text(student_answer)
    
    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer()
    
    try:
        # Create TF-IDF matrix
        tfidf_matrix = vectorizer.fit_transform([expected_processed, student_processed])
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        # Convert similarity to a score out of 10
        score = similarity * 10
        
        return score
    except Exception as e:
        print(f"Error in similarity calculation: {str(e)}")
        return 0.0

# Admin login route
@app.route('/')
def index():
    return render_template('Homepage.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            print("\nTesting database connection before login...")
            if not test_db_connection():
                error_msg = "Database connection error. Please check if MySQL server is running."
                print(error_msg)
                flash(error_msg, 'error')
                return render_template('adminlogin.html', error=error_msg)

            print("Database connection successful, attempting login...")
            connection = get_db_connection()
            if connection is None:
                error_msg = "Failed to connect to database"
                flash(error_msg, 'error')
                return render_template('adminlogin.html', error=error_msg)

            cursor = connection.cursor()
            cursor.execute("SELECT * FROM Admins WHERE username = %s AND password = %s", (username, password))
            admin = cursor.fetchone()
            cursor.close()
            connection.close()

            if admin:
                session['admin_logged_in'] = True
                session['admin_id'] = admin[0]
                flash('Login successful!', 'success')
                return redirect(url_for('admin_home'))
            else:
                flash('Invalid username or password', 'error')
                return render_template('adminlogin.html', error='Invalid username or password')
                
        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            print(error_msg)
            flash(error_msg, 'error')
            return render_template('adminlogin.html', error=error_msg)

    return render_template('adminlogin.html')

# Admin home route
@app.route('/admin/home')
def admin_home():
    if 'admin_logged_in' in session:
        return render_template('adminhome.html')
    else:
        flash('Please login first', 'error')
        return redirect(url_for('admin_login'))

# Admin students route
@app.route('/admin/students')
def admin_students():
    if 'admin_logged_in' in session:
        cur = mysql.connector.connector.cursor()
        cur.execute("SELECT * FROM Students")
        students = cur.fetchall()
        cur.close()
        return render_template('admin_students.html', students=students)
    else:
        return redirect(url_for('admin_login'))

# Add student route
@app.route('/admin/add_student', methods=['POST'])
def add_student():
    if 'admin_logged_in' in session:
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connector.connector.cursor()
        cur.execute("INSERT INTO Students (username, password) VALUES (%s, %s)", (username, password))
        mysql.connector.connector.commit()
        cur.close()
        return redirect(url_for('admin_students'))
    else:
        return redirect(url_for('admin_login'))

# Update student route
@app.route('/admin/update_student/<int:student_id>', methods=['POST'])
def update_student(student_id):
    if 'admin_logged_in' in session:
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connector.connector.cursor()
        cur.execute("UPDATE Students SET username = %s, password = %s WHERE student_id = %s", (username, password, student_id))
        mysql.connector.connector.commit()
        cur.close()
        return redirect(url_for('admin_students'))
    else:
        return redirect(url_for('admin_login'))

# Delete student route
@app.route('/admin/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    if 'admin_logged_in' in session:
        cur = mysql.connector.connector.cursor()
        cur.execute("DELETE FROM Students WHERE student_id = %s", (student_id,))
        mysql.connector.connector.commit()
        cur.close()
        return redirect(url_for('admin_students'))
    else:
        return redirect(url_for('admin_login'))

# View student scores route
# View student scores route
# View student scores route
@app.route('/admin/view_student_scores/<int:student_id>')
def view_student_scores(student_id):
    if 'admin_logged_in' in session:
        cur = mysql.connector.connector.cursor()
        query = """
            SELECT DISTINCT sa.answer_id, sa.test_id, t.test_name, q.question_text, 
                ea.answer_text AS expected_answer, 
                sa.answer_text AS student_answer, sa.score
                FROM studentanswers sa
                JOIN tests t ON sa.test_id = t.test_id
                JOIN questions q ON sa.question_id = q.question_id
                JOIN expectedanswers ea ON q.question_id = ea.question_id
                WHERE sa.student_id = %s
                ORDER BY sa.test_id, q.question_id;
        """
        cur.execute(query, (student_id,))
        scores = cur.fetchall()
        cur.close()
        # Convert the tuple of tuples to a list of dictionaries
        scores = [{'answer_id': score[0], 'test_id': score[1], 'test_name': score[2], 
                   'question_text': score[3], 'expected_answer': score[4], 
                   'student_answer': score[5], 'score': score[6]} for score in scores]
        return render_template('student_scores.html', scores=scores)
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/delete_student_score/<int:answer_id>', methods=['POST'])
def delete_student_score(answer_id):
    if 'admin_logged_in' in session:
        cur = mysql.connector.connector.cursor()
        # Delete the score with the given answer_id
        query = "DELETE FROM studentanswers WHERE answer_id = %s"
        cur.execute(query, (answer_id,))
        mysql.connector.connector.commit()
        cur.close()
        return redirect(url_for('admin_students'))  # Redirect to admin students page
    else:
        return redirect(url_for('admin_login'))

###############################################################
#############################Admin Teacher ####################

# Admin teachers route
@app.route('/admin/teachers')
def admin_teachers():
    if 'admin_logged_in' in session:
        cur = mysql.connector.connector.cursor()
        cur.execute("SELECT * FROM Teachers")
        teachers = cur.fetchall()
        cur.close()
        return render_template('admin_teachers.html', teachers=teachers)
    else:
        return redirect(url_for('admin_login'))

# Admin add teacher route
@app.route('/admin/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    if 'admin_logged_in' in session:
        if request.method == 'POST':
            username = request.form['username']  # Changed from 'name' to 'username'
            password = request.form['password']  # Changed from 'email' to 'password'
            cur = mysql.connector.connector.cursor()
            cur.execute("INSERT INTO Teachers (username, password) VALUES (%s, %s)", (username, password))
            mysql.connector.connector.commit()
            cur.close()
            return redirect(url_for('admin_teachers'))
        else:
            return render_template('add_teacher.html')
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/update_teacher/<int:teacher_id>', methods=['GET', 'POST'])
def update_teacher(teacher_id):
    if 'admin_logged_in' in session:
        if request.method == 'POST':
            try:
                username = request.form['username']
                password = request.form['password']
                cur = mysql.connector.connector.cursor()
                cur.execute("UPDATE Teachers SET username = %s, password = %s WHERE teacher_id = %s", (username, password, teacher_id))
                mysql.connector.connector.commit()
                cur.close()
                return redirect(url_for('admin_teachers'))
            except Exception as e:
                print("Error updating teacher:", e)
                # Handle error appropriately, such as displaying an error message to the user
        else:
            cur = mysql.connector.connector.cursor()
            cur.execute("SELECT * FROM Teachers WHERE teacher_id = %s", (teacher_id,))
            teacher = cur.fetchone()
            cur.close()
            if teacher:
                return render_template('update_teacher.html', teacher=teacher, teacher_id=teacher_id)
            else:
                # Handle case where teacher with given ID is not found
                return "Teacher not found"
    else:
        return redirect(url_for('admin_login'))

# Admin delete teacher route
@app.route('/admin/delete_teacher/<int:teacher_id>', methods=['POST'])
def delete_teacher(teacher_id):
    if 'admin_logged_in' in session:
        try:
            cur = mysql.connector.connector.cursor()

            # Delete related records from teacherstudentrelationship table
            cur.execute("DELETE FROM teacherstudentrelationship WHERE teacher_id = %s", (teacher_id,))
            
            # Now, delete the teacher from the teachers table
            cur.execute("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,))
            
            mysql.connector.connector.commit()
            cur.close()
            return redirect(url_for('admin_teachers'))
        except Exception as e:
            # Handle any exceptions
            flash("An error occurred while deleting the teacher.")
            print(e)  # Print the exception for debugging purposes
            return redirect(url_for('admin_teachers'))
    else:
        return redirect(url_for('admin_login'))


# Admin view teacher tests route
@app.route('/admin/view_teacher_tests/<int:teacher_id>')
def view_teacher_tests(teacher_id):
    if 'admin_logged_in' in session:
        cur = mysql.connector.connector.cursor()
        cur.execute("SELECT * FROM Tests WHERE teacher_id = %s", (teacher_id,))
        tests = cur.fetchall()
        cur.close()
        return render_template('view_teacher_tests.html', tests=tests, teacher_id=teacher_id)
    else:
        return redirect(url_for('admin_login'))

# Admin view test questions route
@app.route('/admin/view_test_questions/<int:test_id>')
def view_test_questions(test_id):
    if 'admin_logged_in' in session:
        cur = mysql.connector.connector.cursor()
        cur.execute("SELECT * FROM Questions WHERE test_id = %s", (test_id,))
        questions = cur.fetchall()

        # Fetching expected answers for each question
        question_answers = {}
        for question in questions:
            cur.execute("SELECT * FROM ExpectedAnswers WHERE question_id = %s", (question[0],))
            answers = cur.fetchall()
            question_answers[question[0]] = answers

        cur.close()
        # Pass test_id as teacher_id to the template
        return render_template('view_test_questions.html', teacher_id=test_id, questions=questions, question_answers=question_answers)
    else:
        return redirect(url_for('admin_login'))

# Admin view question expected answers route
@app.route('/admin/view_question_answers/<int:question_id>')
def view_question_answers(question_id):
    if 'admin_logged_in' in session:
        cur = mysql.connector.connector.cursor()
        cur.execute("SELECT * FROM ExpectedAnswers WHERE question_id = %s", (question_id,))
        answers = cur.fetchall()
        cur.close()
        return render_template('view_question_answers.html', answers=answers)
    else:
        return redirect(url_for('admin_login'))


################################################
    


# Admin logout route
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))




################################################################################
###################################Teacher LOGIN######################
# Teacher login route
@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            print("\nTesting database connection before login...")
            if not test_db_connection():
                error_msg = "Database connection error. Please check if MySQL server is running."
                print(error_msg)
                flash(error_msg, 'error')
                return render_template('teacher_login.html', error=error_msg)

            print("Database connection successful, attempting login...")
            connection = get_db_connection()
            if connection is None:
                error_msg = "Failed to connect to database"
                flash(error_msg, 'error')
                return render_template('teacher_login.html', error=error_msg)

            cursor = connection.cursor()
            cursor.execute("SELECT * FROM Teachers WHERE username = %s AND password = %s", (username, password))
            teacher = cursor.fetchone()
            cursor.close()
            connection.close()

            if teacher:
                session['teacher_logged_in'] = True
                session['teacher_id'] = teacher[0]
                flash('Login successful!', 'success')
                return redirect(url_for('teacher_home'))
            else:
                flash('Invalid username or password', 'error')
                return render_template('teacher_login.html', error='Invalid username or password')
                
        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            print(error_msg)
            flash(error_msg, 'error')
            return render_template('teacher_login.html', error=error_msg)

    return render_template('teacher_login.html')

# Teacher home route
@app.route('/teacher_home', methods=['GET', 'POST'])
def teacher_home():
    if 'teacher_logged_in' in session:
        if request.method == 'POST':
            # Check if form was submitted for adding, updating, or deleting test name
            if 'add_test_name' in request.form:
                test_name = request.form['test_name']
                # Add test name to the database
                connection = get_db_connection()
                if connection:
                    cursor = connection.cursor()
                    cursor.execute("INSERT INTO Tests (test_name, teacher_id) VALUES (%s, %s)", (test_name, session['teacher_id']))
                    connection.commit()
                    cursor.close()
                    connection.close()
            elif 'update_test_name' in request.form:
                test_id = request.form['test_id']
                updated_test_name = request.form['updated_test_name']
                # Update test name in the database
                connection = get_db_connection()
                if connection:
                    cursor = connection.cursor()
                    cursor.execute("UPDATE Tests SET test_name = %s WHERE test_id = %s", (updated_test_name, test_id))
                    connection.commit()
                    cursor.close()
                    connection.close()
            elif 'delete_test_name' in request.form:
                test_id = request.form['test_id']
                
                try:
                    connection = get_db_connection()
                    if connection:
                        cursor = connection.cursor()
                        # Delete related student answers first
                        cursor.execute("DELETE FROM studentanswers WHERE test_id = %s", (test_id,))
                        connection.commit()

                        # Delete related expected answers
                        cursor.execute("DELETE FROM expectedanswers WHERE question_id IN (SELECT question_id FROM questions WHERE test_id = %s)", (test_id,))
                        connection.commit()

                        # Delete related questions
                        cursor.execute("DELETE FROM questions WHERE test_id = %s", (test_id,))
                        connection.commit()

                        # Now delete the test from the Tests table
                        cursor.execute("DELETE FROM tests WHERE test_id = %s", (test_id,))
                        connection.commit()
                        
                        cursor.close()
                        connection.close()

                except Exception as e:
                    print("Error:", e)

        # Fetch all tests for the current teacher
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM Tests WHERE teacher_id = %s", (session['teacher_id'],))
            tests = cursor.fetchall()
            cursor.close()
            connection.close()
            return render_template('teacher_home.html', tests=tests)
        else:
            flash('Database connection error', 'error')
            return redirect(url_for('teacher_login'))
    else:
        return redirect(url_for('teacher_login'))

# Teacher logout route
@app.route('/teacher_logout')
def teacher_logout():
    session.pop('teacher_logged_in', None)
    session.pop('teacher_id', None)
    return redirect(url_for('teacher_login'))
######################teacherLOGOUT####################################
################################################################################
###############teacher FUNCTIONS ############################
@app.route('/teacher/view_test_questions/<int:test_id>', methods=['GET', 'POST'])
def view_teacher_test_questions(test_id):
    if 'teacher_logged_in' in session:
        if request.method == 'POST':
            if 'add_question' in request.form:
                question_text = request.form['question_text']
                expected_answers = request.form.getlist('expected_answer')
                connection = get_db_connection()
                if connection:
                    cursor = connection.cursor()
                    cursor.execute("INSERT INTO Questions (question_text, test_id) VALUES (%s, %s)", (question_text, test_id))
                    question_id = cursor.lastrowid
                    for answer in expected_answers:
                        cursor.execute("INSERT INTO ExpectedAnswers (answer_text, question_id) VALUES (%s, %s)", (answer, question_id))
                    connection.commit()
                    cursor.close()
                    connection.close()
            elif 'delete_question' in request.form:
                question_id = request.form['question_id']
                connection = get_db_connection()
                if connection:
                    cursor = connection.cursor()
                    cursor.execute("DELETE FROM ExpectedAnswers WHERE question_id = %s", (question_id,))
                    cursor.execute("DELETE FROM Questions WHERE question_id = %s", (question_id,))
                    connection.commit()
                    cursor.close()
                    connection.close()

        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM Questions WHERE test_id = %s", (test_id,))
            questions = cursor.fetchall()

            question_answers = {}
            for question in questions:
                cursor.execute("SELECT * FROM ExpectedAnswers WHERE question_id = %s", (question[0],))
                answers = cursor.fetchall()
                question_answers[question[0]] = answers

            cursor.close()
            connection.close()
            return render_template('view_teacher_test_questions.html', teacher_id=test_id, questions=questions, question_answers=question_answers)
        else:
            flash('Database connection error', 'error')
            return redirect(url_for('teacher_login'))
    else:
        return redirect(url_for('teacher_login'))

###### Teacher ( student marks section page) ################
@app.route('/teacher_view_score')
def teacher_view_score():
    # Check if the user is logged in as a teacher
    if 'teacher_logged_in' in session:
        teacher_id = session['teacher_id']

        # Fetch student answers and expected answers for the logged-in teacher's tests
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            query = """
                SELECT s.student_id, s.username AS student_username, t.test_name, q.question_text, ea.answer_text AS expected_answer, sa.answer_text AS student_answer, sa.score
                FROM StudentAnswers sa
                JOIN Students s ON sa.student_id = s.student_id
                JOIN Tests t ON sa.test_id = t.test_id
                JOIN Questions q ON sa.question_id = q.question_id
                JOIN ExpectedAnswers ea ON q.question_id = ea.question_id
                WHERE t.teacher_id = %s
            """
            cursor.execute(query, (teacher_id,))
            results = cursor.fetchall()

            # Group the results by student_id and test_name
            student_scores = defaultdict(lambda: {'student_username': None, 'tests': defaultdict(list)})
            for result in results:
                student_id, student_username, test_name, question_text, expected_answer, student_answer, score = result
                student_scores[student_id]['student_username'] = student_username
                student_scores[student_id]['tests'][test_name].append({
                    'question_text': question_text,
                    'expected_answer': expected_answer,
                    'student_answer': student_answer,
                    'score': score
                })

            cursor.close()
            connection.close()
            return render_template('teacher_view_score.html', student_scores=student_scores)
        else:
            flash('Database connection error', 'error')
            return redirect(url_for('teacher_login'))
    else:
        return redirect(url_for('teacher_login'))


##############################################################
                                                              
######################## Student LOGIN ####################### 
    
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            print("\nTesting database connection before login...")
            if not test_db_connection():
                error_msg = "Database connection error. Please check if MySQL server is running."
                print(error_msg)
                flash(error_msg, 'error')
                return render_template('student_login.html', error=error_msg)

            print("Database connection successful, attempting login...")
            connection = get_db_connection()
            if connection is None:
                error_msg = "Failed to connect to database"
                flash(error_msg, 'error')
                return render_template('student_login.html', error=error_msg)

            cursor = connection.cursor()
            cursor.execute("SELECT * FROM Students WHERE username = %s AND password = %s", (username, password))
            student = cursor.fetchone()
            cursor.close()
            connection.close()

            if student:
                session['student_logged_in'] = True
                session['student_id'] = student[0]
                flash('Login successful!', 'success')
                return redirect(url_for('student_home'))
            else:
                flash('Invalid username or password', 'error')
                return render_template('student_login.html', error='Invalid username or password')
                
        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            print(error_msg)
            flash(error_msg, 'error')
            return render_template('student_login.html', error=error_msg)

    return render_template('student_login.html')
@app.route('/student_home')
def student_home():
    if 'student_logged_in' in session:
        student_id = session['student_id']
        cur = mysql.connector.connector.cursor()
        cur.execute("SELECT username FROM Students WHERE id = %s", (student_id,))
        student = cur.fetchone()
        cur.close()
        return render_template('student_home.html', student_name=student[0] if student else 'Student')
    else:
        return redirect(url_for('student_login'))

@app.route('/student_logout')
def student_logout():
    session.pop('student_logged_in', None)
    session.pop('student_id', None)
    return redirect(url_for('student_login'))



# Route for showing available tests and taking a test
@app.route('/student_take_test', methods=['GET', 'POST'])
def student_take_test():
    if 'student_logged_in' in session:
        if request.method == 'POST':
            # Handle form submission (store student answers)
            test_id = request.form.get('test_id')  # Assuming you have a hidden input field for the test_id
            student_id = session['student_id']  # Assuming you have stored student_id in the session
            
            # Check if the student has already taken the test
            if check_test_taken(student_id):
                return redirect(url_for('student_view_score'))
            
            # Loop through form data to retrieve answers for each question
            for question_id, answer in request.form.items():
                # Assuming input field names are in the format 'question_{question_id}'
                if question_id.startswith('question_'):
                    question_id = int(question_id.split('_')[1])
                    
                    # Store student answer in the StudentAnswers table
                    cur = mysql.connector.connector.cursor()
                    cur.execute("INSERT INTO StudentAnswers (student_id, test_id, question_id, answer_text) VALUES (%s, %s, %s, %s)",
                                (student_id, test_id, question_id, answer))
                    mysql.connector.connector.commit()
                    cur.close()
            
            # Redirect the student after storing answers
            return redirect(url_for('student_view_score'))
        else:
            # Fetch tests that the student has not taken yet
            cur = mysql.connector.connector.cursor()
            cur.execute("""SELECT t.test_id, t.test_name 
                           FROM Tests t 
                           LEFT JOIN StudentAnswers sa ON t.test_id = sa.test_id AND sa.student_id = %s
                           WHERE sa.test_id IS NULL""", (session['student_id'],))
            tests = cur.fetchall()
            cur.close()
            
            # Convert the list of tuples to a list of dictionaries
            tests = [{'test_id': test[0], 'test_name': test[1]} for test in tests]
            
            return render_template('student_take_test.html', tests=tests)
    else:
        return redirect(url_for('student_login'))

@app.route('/student_take_test/<int:test_id>', methods=['GET', 'POST'])
def student_take_test_questions(test_id):
    if 'student_logged_in' in session:
        if request.method == 'POST':
            # Retrieve student ID from the session
            student_id = session['student_id']
            
            # Retrieve test ID from the route parameter
            test_id = test_id
            
            # Loop through form data to retrieve answers for each question
            for question_id, answer in request.form.items():
                # Assuming input field names are in the format 'question_{question_id}'
                if question_id.startswith('question_'):
                    question_id = int(question_id.split('_')[1])

                    # Store student answer in the StudentAnswers table
                    cur = mysql.connector.connector.cursor()
                    cur.execute("INSERT INTO StudentAnswers (student_id, test_id, question_id, answer_text) VALUES (%s, %s, %s, %s)",
                                (student_id, test_id, question_id, answer))
                    mysql.connector.connector.commit()
                    cur.close()

            # Redirect the student after storing answers
            return redirect(url_for('student_home'))

        else:
            # Fetch test details and questions for the specified test from the database
            cur = mysql.connector.connector.cursor()
            cur.execute("SELECT * FROM Tests WHERE test_id = %s", (test_id,))
            test = cur.fetchone()
            cur.execute("SELECT * FROM Questions WHERE test_id = %s", (test_id,))
            questions = cur.fetchall()
            cur.close()

            return render_template('student_take_test_questions.html', test=test, questions=questions, test_id=test_id)
    else:
        return redirect(url_for('student_login'))

@app.route('/student_view_score')
def student_view_score():
    # Check if the user is logged in as a student
    if 'student_logged_in' in session:
        student_id = session['student_id']

        # Fetch student answers, test names, questions, and expected answers for the logged-in student's tests
        cur = mysql.connector.connector.cursor()
        query = """
            SELECT t.test_id, t.test_name, q.question_text, ea.answer_text AS expected_answer, sa.answer_text AS student_answer
            FROM StudentAnswers sa
            JOIN Tests t ON sa.test_id = t.test_id
            JOIN Questions q ON sa.question_id = q.question_id
            JOIN ExpectedAnswers ea ON q.question_id = ea.question_id
            WHERE sa.student_id = %s
        """
        cur.execute(query, (student_id,))
        results = cur.fetchall()

        # Prepare the data to be displayed
        student_scores = {}
        for result in results:
            test_id, test_name, question_text, expected_answer, student_answer = result
            # Calculate score
            score = evaluate(expected_answer, student_answer)
            cur.execute("UPDATE studentanswers SET score = %s WHERE student_id = %s AND test_id = %s AND question_id IN (SELECT question_id FROM questions WHERE question_text = %s)", (score, student_id, test_id, question_text))
            mysql.connector.connector.commit()
            # Check if test_id already exists in student_scores
            if test_id not in student_scores:
                student_scores[test_id] = {
                    'test_id': test_id,
                    'test_name': test_name,
                    'total_score': 0,
                    'max_score': 0,
                    'scores': []
                }
            student_scores[test_id]['scores'].append({
                'question': question_text,
                'expected_answer': expected_answer,
                'student_answer': student_answer,
                'score': score
            })
            score = evaluate(expected_answer, student_answer)
            # Increment total score

            student_scores[test_id]['total_score'] += score
            # Increment max score
            student_scores[test_id]['max_score'] += 10

        # Format total score as "X / Y" for each test
        for test_data in student_scores.values():
            test_data['total_score'] = f"{test_data['total_score']} / {test_data['max_score']}"

        return render_template('student_view_score.html', student_scores=student_scores.values())
    else:
        return redirect(url_for('student_login'))


###############################################
#####################algorithm#################


###########################################

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory and subfolders exist
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'answer_sheets'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'answer_keys'), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/evaluate', methods=['GET', 'POST'])
def evaluate():
    if request.method == 'POST':
        if 'answer_sheet' in request.files:
            file = request.files['answer_sheet']
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'answer_sheets', filename))
                flash('Answer sheet uploaded successfully!')
                return redirect(url_for('upload_answer_key'))
        elif 'answer_key' in request.files:
            file = request.files['answer_key']
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'answer_keys', filename))
                flash('Answer key uploaded successfully!')
                return redirect(url_for('generate_results'))
        elif 'generate' in request.form:
            # Extract text from the uploaded PDF using Google Vision API
            # Process the extracted text using Mistral7B
            # Generate results
            flash('Results generated successfully!')
            return redirect(url_for('evaluate'))
    return render_template('evaluate.html')

# File upload configurations
STUDENT_FILES_FOLDER = 'student_files'
MASTER_FILES_FOLDER = 'master_files'
REFERENCE_FILES_FOLDER = 'reference_files'
RESULTS_FOLDER = 'results'

app.config['STUDENT_FILES_FOLDER'] = STUDENT_FILES_FOLDER
app.config['MASTER_FILES_FOLDER'] = MASTER_FILES_FOLDER
app.config['REFERENCE_FILES_FOLDER'] = REFERENCE_FILES_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

# Create necessary directories if they don't exist
for folder in [STUDENT_FILES_FOLDER, MASTER_FILES_FOLDER, REFERENCE_FILES_FOLDER, RESULTS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/upload_student_files', methods=['POST'])
def upload_student_files():
    if 'student_files' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    files = request.files.getlist('student_files')
    for file in files:
        if file.filename == '':
            continue
        if file and allowed_file(file.filename, {'pdf', 'jpg', 'jpeg', 'png'}):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'answer_sheets', filename))
    return jsonify({'success': True, 'message': 'Student files uploaded successfully!'}), 200

@app.route('/upload_answer_key', methods=['GET', 'POST'])
def upload_answer_key():
    if request.method == 'POST':
        if 'master_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file part'}), 400
        file = request.files['master_file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No selected file'}), 400
        if file and allowed_file(file.filename, {'pdf', 'docx'}):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'answer_keys', filename))
            return jsonify({'success': True, 'message': 'Answer key uploaded successfully!'}), 200
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400
    return render_template('evaluate.html')

@app.route('/upload_master_copy', methods=['POST'])
def upload_master_copy():
    if 'master_file' not in request.files:
        flash('No master file was uploaded')
        return redirect(url_for('evaluate'))
    
    file = request.files['master_file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('evaluate'))
        
    if file and allowed_file(file.filename, {'txt', 'pdf'}):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['MASTER_FILES_FOLDER'], filename))
        flash('Master copy uploaded successfully!')
    else:
        flash('Invalid file type. Please upload TXT or PDF files only.')
        
    return redirect(url_for('evaluate'))

@app.route('/upload_reference', methods=['POST'])
def upload_reference():
    if 'reference_files' not in request.files:
        flash('No reference files were uploaded')
        return redirect(url_for('evaluate'))
    
    files = request.files.getlist('reference_files')
    
    for file in files:
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename, {'txt', 'pdf'}):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['REFERENCE_FILES_FOLDER'], filename))
                
    flash('Reference materials uploaded successfully!')
    return redirect(url_for('evaluate'))

@app.route('/generate_results', methods=['POST'])
def generate_results():
    try:
        # Check if required files exist
        answer_sheets_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'answer_sheets')
        answer_keys_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'answer_keys')
        
        if not os.path.exists(answer_sheets_dir) or not os.listdir(answer_sheets_dir):
            return jsonify({'success': False, 'message': 'No answer sheets found. Please upload student files first.'}), 400
            
        if not os.path.exists(answer_keys_dir) or not os.listdir(answer_keys_dir):
            return jsonify({'success': False, 'message': 'No answer key found. Please upload answer key first.'}), 400
        
        # Get the answer key
        answer_key_file = os.listdir(answer_keys_dir)[0]
        answer_key_path = os.path.join(answer_keys_dir, answer_key_file)
        
        # Create results directory if it doesn't exist
        results_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        # Initialize the evaluator
        evaluator = EnhancedEvaluator()
        
        results = []
        # Process each student's answer sheet
        for student_file in os.listdir(answer_sheets_dir):
            student_file_path = os.path.join(answer_sheets_dir, student_file)
            
            # Create output file path for this student
            output_file = os.path.join(results_dir, f"{os.path.splitext(student_file)[0]}_results.json")
            
            # Process the answer sheet
            evaluator.process_answer_sheet(student_file_path, answer_key_path, output_file)
            
            # Read the results
            with open(output_file, 'r', encoding='utf-8') as f:
                student_results = json.load(f)
            
            # Calculate total score
            total_score = sum(float(result['score']) for result in student_results)
            max_score = len(student_results) * 10  # Assuming each question is out of 10
            
            results.append({
                'student_file': student_file,
                'total_score': f"{total_score}/{max_score}",
                'detailed_results': student_results
            })
        
        return jsonify({
            'success': True,
            'message': 'Results generated successfully!',
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating results: {str(e)}'
        }), 500

@app.route('/upload_answer_sheet', methods=['GET', 'POST'])
def upload_answer_sheet():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('Answer sheet uploaded successfully!')
            return redirect(url_for('upload_answer_key'))
    return render_template('upload_answer_sheet.html')

def extract_text_from_pdf(file_path):
    try:
        # Initialize the client
        client = vision.ImageAnnotatorClient()
        
        # Read the file
        with open(file_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        
        # Perform text detection
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if texts:
            return texts[0].description
        return ""
        
    except Exception as e:
        print(f"Error extracting text: {str(e)}")
        return ""

if __name__ == '__main__':
    app.run(debug=True)
