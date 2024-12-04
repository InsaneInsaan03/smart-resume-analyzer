import streamlit as st
import sqlite3
from hashlib import sha256
import streamlit.components.v1 as components

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
            # Get user data
            c.execute("SELECT password, user_type FROM users WHERE username=?", 
                     (username,))
            result = c.fetchone()
            
            if not result:
                return False
                
            stored_password, stored_user_type = result
            input_password_hash = sha256(password.encode()).hexdigest()
            
            # Verify credentials
            if stored_password == input_password_hash and stored_user_type == user_type:
                # Set session state
                st.session_state.authenticated = True
                st.session_state.user_type = stored_user_type
                st.session_state.username = username
                return True
            return False
        except Exception as e:
            st.error(f"Database error: {str(e)}")
            return False
        finally:
            conn.close()

    def render_login_ui(self):
        st.markdown("""
        <style>
        .login-container {
            max-width: 500px;
            margin: 0 auto;
            padding: 30px;
            background: linear-gradient(135deg, #ffffff 0%, #f5f7fa 100%);
            border-radius: 15px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
        }
        .login-header {
            text-align: center;
            background: linear-gradient(45deg, #2b5876 0%, #4e4376 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 30px;
        }
        .stButton>button {
            width: 100%;
            padding: 12px 0;
            margin: 8px 0;
            border: none;
            border-radius: 25px;
            background: linear-gradient(45deg, #2b5876 0%, #4e4376 100%);
            color: white;
            font-weight: 600;
            font-size: 16px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        }
        /* Fix for input fields */
        .stTextInput>div>div>input {
            border-radius: 10px !important;
            padding: 15px 20px !important;
            border: 1px solid #e0e0e0 !important;
            transition: all 0.3s ease !important;
            background-color: white !important;
            color: #333 !important;
            outline: none !important;
        }
        .stTextInput>div>div>input:focus {
            border-color: #2b5876 !important;
            box-shadow: 0 0 0 1px #2b5876 !important;
            outline: none !important;
        }
        .stTextInput>div>div>input:hover {
            border-color: #2b5876 !important;
        }
        /* Remove any red outlines */
        .stTextInput>div {
            border: none !important;
            outline: none !important;
        }
        .stTextInput>div:focus-within {
            box-shadow: none !important;
            outline: none !important;
        }
        .signup-text {
            text-align: center;
            margin-top: 20px;
            font-size: 15px;
            color: #666;
        }
        .form-container {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            margin-top: 20px;
        }
        .stSelectbox>div>div {
            border-radius: 10px !important;
        }
        /* Style for form labels */
        .stMarkdown h5 {
            color: #2b5876;
            margin-bottom: 5px;
            margin-top: 15px;
        }
        </style>
        """, unsafe_allow_html=True)

        # Add custom icons and header
        st.markdown("""
        <div style='text-align: center; margin-bottom: 30px;'>
            <svg width="50" height="50" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" fill="url(#grad1)"/>
                <defs>
                    <linearGradient id="grad1" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                        <stop offset="0%" style="stop-color:#2b5876"/>
                        <stop offset="100%" style="stop-color:#4e4376"/>
                    </linearGradient>
                </defs>
            </svg>
        </div>
        <h1 class='login-header'>Smart Resume Analyzer</h1>
        """, unsafe_allow_html=True)

        # Create container for buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("👤 User Login"):
                st.session_state.show_login = "normal"
                st.session_state.show_signup = False
        
        with col2:
            if st.button("🏢 Admin Login"):
                st.session_state.show_login = "admin"
                st.session_state.show_signup = False
        
        with col3:
            if st.button("✨ Sign Up"):
                st.session_state.show_signup = True
                st.session_state.show_login = None

        # Show login form based on selection
        if hasattr(st.session_state, 'show_login') and st.session_state.show_login:
            user_type = st.session_state.show_login
            with st.form(f"{user_type}_login_form"):
                st.markdown(f"<h2 style='text-align: center; color: #2b5876; margin-bottom: 20px;'>{user_type.title()} Login</h2>", unsafe_allow_html=True)
                
                st.markdown("##### 👤 Username")
                username = st.text_input("", placeholder="Enter your username", key="username_input")
                
                st.markdown("##### 🔒 Password")
                password = st.text_input("", type="password", placeholder="Enter your password", key="password_input")
                
                if st.form_submit_button("Login 🚀"):
                    if self.verify_user(username, password, user_type):
                        st.success("🎉 Welcome {}!".format(username))
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")

        # Show signup form
        elif hasattr(st.session_state, 'show_signup') and st.session_state.show_signup:
            with st.form("signup_form"):
                st.markdown("<h2 style='text-align: center; color: #2b5876; margin-bottom: 20px;'>Create Account</h2>", unsafe_allow_html=True)
                
                st.markdown("##### 👤 Username")
                new_username = st.text_input("", placeholder="Choose a username", key="new_username")
                
                st.markdown("##### 🔒 Password")
                new_password = st.text_input("", type="password", placeholder="Create a password", key="new_password")
                
                st.markdown("##### 🔒 Confirm Password")
                confirm_password = st.text_input("", type="password", placeholder="Confirm your password", key="confirm_password")
                
                st.markdown("##### 👥 User Type")
                user_type = st.selectbox("", ["normal", "admin"], key="user_type")
                
                if st.form_submit_button("Sign Up ✨"):
                    if new_password != confirm_password:
                        st.error("❌ Passwords do not match!")
                    elif not new_username or not new_password:
                        st.error("❌ Please fill in all fields!")
                    else:
                        if self.add_user(new_username, new_password, user_type):
                            st.success("✅ Account created successfully! Please login.")
                            st.session_state.show_signup = False
                            st.rerun()
                        else:
                            st.error("❌ Username already exists!")

    def is_authenticated(self):
        """Check if user is authenticated"""
        return st.session_state.authenticated

    def get_user_type(self):
        """Get the current user type, defaults to 'normal' if not set"""
        return st.session_state.get('user_type', 'normal')

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
