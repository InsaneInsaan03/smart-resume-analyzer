"""Database utility functions for the resume analyzer."""

import os
import sqlite3
import streamlit as st
from constants import DB_PATH, DB_FILE
from hashlib import sha256

def get_db_path():
    """Get the database path and ensure the directory exists"""
    # Get the directory where the script is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(base_dir, 'database')
    
    # Create the database directory if it doesn't exist
    os.makedirs(db_dir, exist_ok=True)
    
    return os.path.join(db_dir, 'users.db')

def init_db():
    """Initialize the database with tables and default admin user"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create users table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS users
                (username TEXT PRIMARY KEY, 
                 password TEXT NOT NULL,
                 user_type TEXT NOT NULL)''')

    # Create applications table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS applications
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 applicant_username TEXT NOT NULL,
                 company_username TEXT NOT NULL,
                 resume_data TEXT NOT NULL,
                 resume_score TEXT,
                 application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 status TEXT DEFAULT 'pending',
                 FOREIGN KEY (applicant_username) REFERENCES users(username),
                 FOREIGN KEY (company_username) REFERENCES users(username))''')

    # Check if default admin exists
    c.execute("SELECT username FROM users WHERE username=? AND user_type=?", ('admin', 'admin'))
    if not c.fetchone():
        # Create default admin user if it doesn't exist
        default_password = 'admin123'  # You can change this default password
        hashed_password = sha256(default_password.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)",
                 ('admin', hashed_password, 'admin'))
        st.info("Default admin account created. Username: admin, Password: admin123")

    conn.commit()
    conn.close()

def get_resume_db_path():
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

def init_resume_db():
    """Initialize the resume database with required tables."""
    try:
        db_path = get_resume_db_path()
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
        
        # Create login_data table for user authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_data (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                user_type TEXT,
                Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
    except Exception as e:
        st.error(f"Error initializing database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def insert_user_data(data):
    """Insert or update user data in the database."""
    try:
        db_path = get_resume_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First check if user_data table exists, if not create it
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_data'
        """)
        if not cursor.fetchone():
            # Create user_data table if it doesn't exist
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
        
        # Ensure recommended skills is a string
        if 'Recommended_Skills' in data and isinstance(data['Recommended_Skills'], (list, set)):
            data['Recommended_Skills'] = ', '.join(data['Recommended_Skills'])
            
        # Ensure actual skills is a string
        if 'Actual_Skills' in data and isinstance(data['Actual_Skills'], (list, set)):
            data['Actual_Skills'] = ', '.join(data['Actual_Skills'])
        
        # Check if user already has a submission
        cursor.execute('SELECT ID FROM user_data WHERE Email = ? AND Name = ?', 
                      (data.get('Email', ''), data.get('Name', '')))
        existing_entry = cursor.fetchone()
        
        if existing_entry:
            # Update existing entry
            cursor.execute('''
                UPDATE user_data SET 
                    Resume_Score = ?,
                    Total_Page = ?,
                    Predicted_Field = ?,
                    User_Level = ?,
                    Actual_Skills = ?,
                    Recommended_Skills = ?,
                    Recommended_Courses = ?,
                    PDF_Name = ?,
                    Timestamp = CURRENT_TIMESTAMP
                WHERE Email = ? AND Name = ?
            ''', (
                data.get('Resume_Score', 0),
                data.get('Total_Page', 0),
                data.get('Predicted_Field', ''),
                data.get('User_Level', ''),
                data.get('Actual_Skills', ''),
                data.get('Recommended_Skills', ''),
                data.get('Recommended_Courses', ''),
                data.get('PDF_Name', ''),
                data.get('Email', ''),
                data.get('Name', '')
            ))
        else:
            # Insert new entry
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
        st.error(f"Error inserting/updating data: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def get_user_data():
    """Retrieve all user data from the database."""
    try:
        db_path = get_resume_db_path()
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

def delete_user(email):
    """Delete a user from both resume_data.db and users.db databases."""
    success = True
    
    # Delete from resume_data.db
    try:
        db_path = get_resume_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First check if the table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_data'
        """)
        if cursor.fetchone():
            cursor.execute('DELETE FROM user_data WHERE Email = ?', (email,))
            conn.commit()
    except Exception as e:
        st.error(f"Error deleting from resume database: {e}")
        success = False
    finally:
        if 'conn' in locals():
            conn.close()
    
    # Delete from users.db
    try:
        # Use direct path for users.db since it's in the root directory
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Delete from applications table first (due to foreign key constraint)
        cursor.execute('DELETE FROM applications WHERE applicant_username = ?', (email,))
        
        # Then delete from users table
        cursor.execute('DELETE FROM users WHERE username = ?', (email,))
        
        conn.commit()
    except Exception as e:
        st.error(f"Error deleting from users database: {e}")
        success = False
    finally:
        if 'conn' in locals():
            conn.close()
            
    return success

def delete_admin(username):
    """Delete an admin from users.db database."""
    try:
        # Delete from users.db
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Verify it's an admin before deleting
        cursor.execute('SELECT user_type FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user and user[0] == 'admin':
            cursor.execute('DELETE FROM users WHERE username = ?', (username,))
            conn.commit()
            return True
        else:
            st.error("User not found or not an admin.")
            return False
            
    except Exception as e:
        st.error(f"Error deleting admin: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
