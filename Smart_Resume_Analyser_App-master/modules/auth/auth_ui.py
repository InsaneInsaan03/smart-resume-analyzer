import streamlit as st
import time
from .auth_manager import AuthManager

class AuthUI:
    def __init__(self):
        self.auth_manager = AuthManager()
        if 'auth_stage' not in st.session_state:
            st.session_state.auth_stage = 'login'
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False

    def render_login_form(self):
        """Render login form"""
        st.title("👋 Welcome Back!")
        
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Login")
            with col2:
                if st.form_submit_button("Create Account"):
                    st.session_state.auth_stage = 'register'
                    st.rerun()
            
            if submit and email and password:
                success, result = self.auth_manager.login_user(email, password)
                if success:
                    st.session_state.user = result
                    st.session_state.authenticated = True
                    st.success("Login successful!")
                    time.sleep(1)  # Give time for success message
                    st.rerun()
                else:
                    st.error(result)

    def render_register_form(self):
        """Render registration form"""
        st.title("🚀 Create Account")
        
        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            user_type = st.selectbox("Account Type", ["applicant", "recruiter"])
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Register")
            with col2:
                if st.form_submit_button("Back to Login"):
                    st.session_state.auth_stage = 'login'
                    st.rerun()
            
            if submit and username and email and password:
                success, message = self.auth_manager.register_user(
                    username, email, password, user_type
                )
                if success:
                    st.success(message)
                    st.session_state.auth_stage = 'login'
                    st.rerun()
                else:
                    st.error(message)

    def render(self):
        """Main render method"""
        if st.session_state.auth_stage == 'login':
            self.render_login_form()
        else:
            self.render_register_form()

    def is_authenticated(self):
        return st.session_state.authenticated
