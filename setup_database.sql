-- Create the database
CREATE DATABASE IF NOT EXISTS teacher_part;
USE teacher_part;

-- Create Admins table
CREATE TABLE IF NOT EXISTS Admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- Create Teachers table
CREATE TABLE IF NOT EXISTS Teachers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- Create Students table
CREATE TABLE IF NOT EXISTS Students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- Create answer keys table (needs to be created before Tests table)
CREATE TABLE IF NOT EXISTS answer_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id INT NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    upload_date DATETIME NOT NULL,
    FOREIGN KEY (teacher_id) REFERENCES Teachers(id)
);

-- Create Tests table
CREATE TABLE IF NOT EXISTS Tests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id INT,
    test_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    answer_key_id INT,
    FOREIGN KEY (teacher_id) REFERENCES Teachers(id),
    FOREIGN KEY (answer_key_id) REFERENCES answer_keys(id)
);

-- Create Questions table
CREATE TABLE IF NOT EXISTS Questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    test_id INT,
    question_text TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    FOREIGN KEY (test_id) REFERENCES Tests(id)
);

-- Create Answers table
CREATE TABLE IF NOT EXISTS Answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT,
    student_id INT,
    student_answer TEXT,
    score FLOAT,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    feedback TEXT,
    FOREIGN KEY (question_id) REFERENCES Questions(id),
    FOREIGN KEY (student_id) REFERENCES Students(id)
);

-- Insert default admin user
INSERT INTO Admins (username, password) VALUES ('admin', 'admin123');

-- Add answer_key_id to Tests table
ALTER TABLE Tests ADD COLUMN answer_key_id INT;

-- Add score and feedback to Answers table
ALTER TABLE Answers ADD COLUMN score FLOAT;
ALTER TABLE Answers ADD COLUMN feedback TEXT; 