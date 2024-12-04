"""Constants used throughout the application."""

import os

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'Uploaded_Resumes')
DATABASE_DIR = os.path.join(BASE_DIR, 'database')

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATABASE_DIR, exist_ok=True)

# Database paths
DB_PATH = DATABASE_DIR
DB_FILE = os.path.join(DATABASE_DIR, 'resume_data.db')
USERS_DB = os.path.join(DATABASE_DIR, 'users.db')

# Create .gitkeep file to preserve the database directory
gitkeep_file = os.path.join(DATABASE_DIR, '.gitkeep')
if not os.path.exists(gitkeep_file):
    with open(gitkeep_file, 'w') as f:
        pass

# Database schema
USER_TABLE_SCHEMA = '''CREATE TABLE IF NOT EXISTS user_data
                    (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT,
                    Email TEXT,
                    Resume_Score INTEGER,
                    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    Total_Page INTEGER,
                    Predicted_Field TEXT,
                    User_Level TEXT,
                    Actual_Skills TEXT,
                    Recommended_Skills TEXT,
                    Recommended_Courses TEXT,
                    PDF_Name TEXT)'''

# Styling constants
TYPING_MESSAGES = [
    "Unlock Your Career Potential ",
    "Get Smart Resume Analysis ",
    "Discover Your Perfect Career Path ",
    "Enhance Your Professional Journey "
]
