import sqlite3
import hashlib
import os

class AuthManager:
    def __init__(self):
        self.db_path = 'db/users.db'
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and tables exist"""
        if not os.path.exists('db'):
            os.makedirs('db')
            
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create users table
        c.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT NOT NULL,
                     email TEXT UNIQUE NOT NULL,
                     password TEXT NOT NULL,
                     user_type TEXT NOT NULL)''')
        
        conn.commit()
        conn.close()

    def _hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, email, password, user_type):
        """Register a new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check if email exists
            c.execute("SELECT id FROM users WHERE email = ?", (email,))
            if c.fetchone():
                return False, "Email already registered"
            
            # Hash password and store user
            hashed_password = self._hash_password(password)
            c.execute("""INSERT INTO users 
                        (username, email, password, user_type)
                        VALUES (?, ?, ?, ?)""",
                     (username, email, hashed_password, user_type))
            
            conn.commit()
            return True, "Registration successful"
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False, f"Registration failed: {str(e)}"
        finally:
            conn.close()

    def login_user(self, email, password):
        """Login a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get user by email
            c.execute("""SELECT id, username, password, user_type 
                        FROM users WHERE email = ?""", (email,))
            user = c.fetchone()
            
            if not user:
                return False, "Email not found"
            
            # Verify password
            hashed_password = self._hash_password(password)
            if hashed_password != user[2]:
                return False, "Incorrect password"
            
            # Return user info
            return True, {
                'id': user[0],
                'username': user[1],
                'email': email,
                'user_type': user[3]
            }
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False, f"Login failed: {str(e)}"
        finally:
            conn.close()
