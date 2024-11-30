"""Constants used throughout the application."""

# Database configuration
DB_PATH = "database/"  # Database directory
DB_FILE = "user_data.db"  # Database file name

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
    "Unlock Your Career Potential 🚀",
    "Get Smart Resume Analysis 📊",
    "Discover Your Perfect Career Path 🎯",
    "Enhance Your Professional Journey 💼"
]

# File paths
UPLOAD_DIR = './Uploaded_Resumes'
