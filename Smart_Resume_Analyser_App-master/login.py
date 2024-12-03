import streamlit as st
import sqlite3
from hashlib import sha256

class LoginUI:
    def __init__(self):
        self.init_db()
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_type' not in st.session_state:
            st.session_state.user_type = None
        if 'username' not in st.session_state:
            st.session_state.username = None

    def init_db(self):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                    (username TEXT PRIMARY KEY, 
                     password TEXT NOT NULL,
                     user_type TEXT NOT NULL)''')
                     
        # Create applications table
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
        conn.commit()
        conn.close()

    def add_user(self, username, password, user_type):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            # Check if user exists
            c.execute("SELECT username FROM users WHERE username=?", (username,))
            if c.fetchone():
                return False
                
            # Add new user
            hashed_pw = sha256(password.encode()).hexdigest()
            c.execute("INSERT INTO users VALUES (?, ?, ?)", 
                     (username, hashed_pw, user_type))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            st.error(f"Database error: {str(e)}")
            return False
        finally:
            conn.close()

    def verify_user(self, username, password, user_type):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            # Debug information
            st.write("Checking credentials for:", username)
            st.write("User type:", user_type)
            
            # Get user data
            c.execute("SELECT password, user_type FROM users WHERE username=?", 
                     (username,))
            result = c.fetchone()
            
            if not result:
                st.write("User not found in database")
                return False
                
            stored_password, stored_user_type = result
            input_password_hash = sha256(password.encode()).hexdigest()
            
            # Debug password match
            st.write("Stored user type:", stored_user_type)
            password_match = stored_password == input_password_hash
            type_match = stored_user_type == user_type
            
            st.write("Password match:", password_match)
            st.write("User type match:", type_match)
            
            return password_match and type_match
        except Exception as e:
            st.error(f"Database error: {str(e)}")
            return False
        finally:
            conn.close()

    def render_login_ui(self):
        st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .login-header {
            text-align: center;
            color: #2b5876;
            margin-bottom: 20px;
        }
        .stButton>button {
            width: 100%;
            margin-top: 10px;
            background-color: #2b5876;
            color: white;
        }
        .signup-text {
            text-align: center;
            margin-top: 15px;
            font-size: 14px;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("<h1 class='login-header'>Smart Resume Analyzer</h1>", 
                   unsafe_allow_html=True)

        # Create three columns for the buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Normal User Login"):
                st.session_state.show_login = "normal"
                st.session_state.show_signup = False
        
        with col2:
            if st.button("Admin Login"):
                st.session_state.show_login = "admin"
                st.session_state.show_signup = False
        
        with col3:
            if st.button("Sign Up"):
                st.session_state.show_signup = True
                st.session_state.show_login = None

        # Show login form based on selection
        if hasattr(st.session_state, 'show_login') and st.session_state.show_login:
            user_type = st.session_state.show_login
            with st.form(f"{user_type}_login_form"):
                st.subheader(f"{user_type.title()} Login")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Login"):
                    if self.verify_user(username, password, user_type):
                        st.session_state.authenticated = True
                        st.session_state.user_type = user_type
                        st.session_state.username = username
                        st.success(f"Welcome {username}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

        # Show signup form
        elif hasattr(st.session_state, 'show_signup') and st.session_state.show_signup:
            with st.form("signup_form"):
                st.subheader("Sign Up")
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                user_type = st.selectbox("User Type", ["normal", "admin"])
                
                if st.form_submit_button("Sign Up"):
                    if new_password != confirm_password:
                        st.error("Passwords do not match!")
                    elif not new_username or not new_password:
                        st.error("Please fill in all fields!")
                    else:
                        if self.add_user(new_username, new_password, user_type):
                            st.success("Account created successfully! Please login.")
                            st.session_state.show_signup = False
                            st.rerun()
                        else:
                            st.error("Username already exists!")

    def is_authenticated(self):
        """Check if user is authenticated"""
        return st.session_state.authenticated

    def get_user_type(self):
        return st.session_state.user_type

    def get_username(self):
        return st.session_state.username

    def logout(self):
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = None

    def get_admin_users(self):
        """Get list of all admin users (companies)"""
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE user_type='admin'")
        admins = [row[0] for row in c.fetchall()]
        conn.close()
        return admins

    def submit_application(self, applicant_username, company_username, resume_data, resume_score):
        """Submit a job application to a company"""
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO applications 
                (applicant_username, company_username, resume_data, resume_score)
                VALUES (?, ?, ?, ?)
            """, (applicant_username, company_username, resume_data, resume_score))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error submitting application: {str(e)}")
            return False
        finally:
            conn.close()

    def get_user_applications(self, username, user_type):
        """Get applications based on user type"""
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            if user_type == 'normal':
                # Get applications submitted by the user
                c.execute("""
                    SELECT company_username, application_date, status
                    FROM applications
                    WHERE applicant_username = ?
                    ORDER BY application_date DESC
                """, (username,))
            else:
                # Get applications received by the company
                c.execute("""
                    SELECT applicant_username, resume_data, resume_score, application_date, status
                    FROM applications
                    WHERE company_username = ?
                    ORDER BY application_date DESC
                """, (username,))
            return c.fetchall()
        finally:
            conn.close()

    def update_application_status(self, applicant_username, company_username, new_status):
        """Update the status of a job application"""
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute("""
                UPDATE applications 
                SET status = ?
                WHERE applicant_username = ? AND company_username = ?
            """, (new_status, applicant_username, company_username))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error updating application status: {str(e)}")
            return False
        finally:
            conn.close()
