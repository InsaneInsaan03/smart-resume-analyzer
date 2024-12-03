"""Database utility functions for the resume analyzer."""

import os
import sqlite3
import streamlit as st
from constants import DB_PATH, DB_FILE

def get_db_path():
    """Get the appropriate database path based on environment"""
    try:
        # For Streamlit Cloud, use the current directory
        if os.getenv('STREAMLIT_SHARING') or os.getenv('STREAMLIT_CLOUD'):
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILE)
        # For local development, use the configured path
        return os.path.join(DB_PATH, DB_FILE)
    except Exception as e:
        st.error(f"Error determining database path: {e}")
        return DB_FILE  # Fallback to just the filename

def init_db():
    """Initialize the database with required tables."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create user_data table with all necessary columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT,
                Email TEXT,
                Resume_Score REAL,
                Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                Total_Page INTEGER,
                Predicted_Field TEXT,
                User_Level TEXT,
                Actual_Skills TEXT,
                Recommended_Skills TEXT,
                Recommended_Courses TEXT,
                PDF_Name TEXT
            )
        ''')
        
        conn.commit()
    except Exception as e:
        st.error(f"Error initializing database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def insert_user_data(data):
    """Insert user data into the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure recommended skills is a string
        if 'Recommended_Skills' in data and isinstance(data['Recommended_Skills'], (list, set)):
            data['Recommended_Skills'] = ', '.join(data['Recommended_Skills'])
            
        # Ensure actual skills is a string
        if 'Actual_Skills' in data and isinstance(data['Actual_Skills'], (list, set)):
            data['Actual_Skills'] = ', '.join(data['Actual_Skills'])
        
        # Insert data into database
        cursor.execute('''
            INSERT INTO user_data (
                Name, Email, Resume_Score, Total_Page,
                Predicted_Field, User_Level, Actual_Skills,
                Recommended_Skills, Recommended_Courses, PDF_Name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('Name', ''),
            data.get('Email', ''),
            data.get('Resume_Score', 0),
            data.get('Total_Page', 0),
            data.get('Predicted_Field', ''),
            data.get('User_Level', ''),
            data.get('Actual_Skills', ''),
            data.get('Recommended_Skills', ''),
            data.get('Recommended_Courses', ''),
            data.get('PDF_Name', '')
        ))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error inserting data: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def get_user_data():
    """Retrieve all user data from the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_data ORDER BY Timestamp DESC')
        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        
        return columns, data
    except Exception as e:
        st.error(f"Error retrieving data: {e}")
        return [], []
    finally:
        if 'conn' in locals():
            conn.close()
