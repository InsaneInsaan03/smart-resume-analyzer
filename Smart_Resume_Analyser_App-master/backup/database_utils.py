"""Database utility functions for the resume analyzer."""

import os
import sqlite3
from constants import DB_PATH, DB_FILE, USER_TABLE_SCHEMA

def init_db():
    """Initialize database and create table if it doesn't exist."""
    # Create the database directory if it doesn't exist
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH + DB_FILE)
    cursor = conn.cursor()
    
    # Drop the existing table if it has wrong schema
    cursor.execute("DROP TABLE IF EXISTS user_data")
    
    # Create table with correct schema
    cursor.execute(USER_TABLE_SCHEMA)
    
    conn.commit()
    conn.close()

def insert_user_data(data):
    """Insert user data into the database."""
    conn = sqlite3.connect(DB_PATH + DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''INSERT INTO user_data 
                    (Name, Email, Resume_Score, Total_Page, Predicted_Field, 
                    User_Level, Actual_Skills, Recommended_Skills, 
                    Recommended_Courses, PDF_Name) 
                    VALUES (?,?,?,?,?,?,?,?,?,?)''', 
                    (data['Name'], data['Email'], data['Resume_Score'],
                    data['Total_Page'], data['Predicted_Field'], data['User_Level'],
                    data['Actual_Skills'], data['Recommended_Skills'],
                    data['Recommended_Courses'], data['PDF_Name']))
    
    conn.commit()
    conn.close()

def get_user_data():
    """Retrieve all user data from the database."""
    conn = sqlite3.connect(DB_PATH + DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM user_data")
    data = cursor.fetchall()
    
    conn.close()
    return data
