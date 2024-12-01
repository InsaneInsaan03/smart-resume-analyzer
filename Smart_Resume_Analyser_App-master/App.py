"""Main application file for the Smart Resume Analyzer."""

import streamlit as st
import pandas as pd
import time
import os
from modules.auth.auth_ui import AuthUI
import sqlite3
import hashlib
from pathlib import Path
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')
from nltk.tokenize import word_tokenize
import base64, random
import datetime
from custom_parser import CustomResumeParser
from resume_scorer import ResumeScorer
from course_recommender import CourseRecommender
from constants import UPLOAD_DIR, DB_PATH, DB_FILE
from database_utils import init_db, insert_user_data, get_user_data
from ui_utils import get_custom_css, show_header, get_table_download_link, create_score_bar
from streamlit_tags import st_tags
from PIL import Image
import plotly.express as px
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io
import requests

# Set page config first
st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon='📄',
    layout='wide'
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'current_file' not in st.session_state:
    st.session_state.current_file = None
if 'resume_data' not in st.session_state:
    st.session_state.resume_data = None
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = None

# Database functions
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, user_type TEXT)''')
    conn.commit()
    conn.close()

def add_user(username, password, user_type):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (username, hashed_pw, user_type))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password, user_type FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hashlib.sha256(password.encode()).hexdigest():
        return True, result[1]
    return False, None

# Initialize database
init_db()

# Custom CSS for navbar
st.markdown("""
    <style>
    .navbar {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 1rem;
        background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
        border-radius: 10px;
        margin-bottom: 1rem;
        gap: 1rem;
    }
    .nav-item {
        color: white;
        text-decoration: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        background-color: rgba(255,255,255,0.1);
    }
    .auth-form {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        z-index: 1000;
        width: 300px;
    }
    </style>
""", unsafe_allow_html=True)

# Navbar
def navbar():
    if st.session_state.authenticated:
        st.markdown(f"""
            <div class="navbar">
                <div style="color: white; margin-right: auto;">
                    Welcome, {st.session_state.get('username', '')} ({st.session_state.get('user_type', '')})
                </div>
                <a href="#" class="nav-item" onclick="signOut()">Sign Out</a>
            </div>
        """, unsafe_allow_html=True)
    else:
        col1, col2, col3 = st.columns([6,1,1])
        with col2:
            if st.button("Sign In"):
                st.session_state.show_signin = True
        with col3:
            if st.button("Sign Up"):
                st.session_state.show_signup = True

# Authentication forms
if 'show_signin' in st.session_state and st.session_state.show_signin:
    with st.form("signin_form"):
        st.subheader("Sign In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        user_type = st.selectbox("User Type", ["Normal User", "Admin"])
        submitted = st.form_submit_button("Sign In")
        if submitted:
            success, stored_type = verify_user(username, password)
            if success and stored_type == user_type:
                st.session_state.authenticated = True
                st.session_state.user = {'username': username, 'user_type': user_type}
                st.session_state.show_signin = False
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

if 'show_signup' in st.session_state and st.session_state.show_signup:
    with st.form("signup_form"):
        st.subheader("Sign Up")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        user_type = st.selectbox("User Type", ["Normal User", "Admin"])
        submitted = st.form_submit_button("Sign Up")
        if submitted:
            if new_password != confirm_password:
                st.error("Passwords do not match")
            elif not new_username or not new_password:
                st.error("Please fill all fields")
            else:
                if add_user(new_username, new_password, user_type):
                    st.success("Account created successfully!")
                    st.session_state.show_signup = False
                    st.experimental_rerun()
                else:
                    st.error("Username already exists")

def extract_text_from_pdf(pdf_path):
    """Extract text from uploaded PDF file"""
    try:
        # Create a PDF resource manager object
        resource_manager = PDFResourceManager()
        
        # Create a string buffer object
        fake_file_handle = io.StringIO()
        
        # Create a converter object
        converter = TextConverter(
            resource_manager, 
            fake_file_handle, 
            laparams=LAParams()
        )
        
        # Create a PDF interpreter object
        interpreter = PDFPageInterpreter(resource_manager, converter)
        
        # Open the PDF file using the full path
        pdf_file_obj = open(pdf_path, 'rb')
        
        # Get pages from the PDF file
        for page in PDFPage.get_pages(
            pdf_file_obj, 
            caching=True,
            check_extractable=True
        ):
            interpreter.process_page(page)
            
        # Get the text from the StringIO buffer
        text = fake_file_handle.getvalue()
        
        # Close all objects
        converter.close()
        fake_file_handle.close()
        pdf_file_obj.close()
        
        return text
        
    except Exception as e:
        st.error(f'Error processing PDF: {str(e)}')
        return None

def main():
    """Main function for the Smart Resume Analyzer App"""
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    # Authentication handling
    auth_ui = AuthUI()
    
    if not st.session_state.authenticated:
        auth_ui.render()
        return
    
    # Main app UI after authentication
    show_header()
    
    user = st.session_state.user
    st.write(f"Welcome {user['username']}!")
    
    # Display navbar
    navbar()
    
    # Sidebar user selection with modern design
    st.sidebar.markdown("""
        <div style="
            background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        ">
            <h2 style="
                color: white;
                margin: 0;
                font-size: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            ">
                <span>👤</span> Choose User Type
            </h2>
        </div>
    """, unsafe_allow_html=True)
    
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("", activities)  # Removed label as it's in the header

    if choice == 'Normal User':
        st.markdown("""
            <div style="
                background: linear-gradient(120deg, #a1c4fd 0%, #c2e9fb 100%);
                padding: 25px;
                border-radius: 15px;
                margin: 25px 0;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            ">
                <h1 style="
                    color: #2b5876;
                    margin: 0 0 10px 0;
                    font-size: 28px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    <span>📋</span> Smart Resume Analyzer
                </h1>
                <p style="
                    color: #2b5876;
                    margin: 0;
                    font-size: 16px;
                ">Upload your resume to get personalized insights and recommendations.</p>
            </div>
        """, unsafe_allow_html=True)

        # Ensure upload directory exists
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)

        # File upload with modern design
        st.markdown("""
            <div style="
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                margin-bottom: 20px;
            ">
                <div style="
                    color: #2b5876;
                    font-weight: 500;
                    margin-bottom: 10px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                ">
                    <span>📤</span> Upload Your Resume
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        pdf_file = st.file_uploader(
            "Upload Your Resume", 
            type=["pdf"],
            help="Please upload a PDF file"
        )
        
        if pdf_file is None:
            st.markdown("""
                <div style="
                    background: #f8f9fa;
                    border-left: 4px solid #2b5876;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                ">
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        color: #2b5876;
                    ">
                        <span style="font-size: 24px;">👋</span>
                        <div>
                            <div style="font-weight: 500; margin-bottom: 5px;">Welcome!</div>
                            <div style="color: #666; font-size: 14px;">Please upload your resume in PDF format to begin the analysis.</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            return

        # Process new file
        if pdf_file is not None and pdf_file.name not in st.session_state.processed_files:
            try:
                # Create upload directory if it doesn't exist
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                
                # Save uploaded file to UPLOAD_DIR
                save_path = os.path.join(UPLOAD_DIR, pdf_file.name)
                with open(save_path, "wb") as f:
                    f.write(pdf_file.getbuffer())

                # Extract text from PDF using the saved file path
                resume_text = extract_text_from_pdf(save_path)
                
                if resume_text:
                    st.session_state.resume_text = resume_text
                    st.session_state.current_file = pdf_file.name
                    st.session_state.processed_files.add(pdf_file.name)
                    
                    # Parse resume
                    parser = CustomResumeParser(save_path)  # Pass the file path instead of text
                    resume_data = parser.get_extracted_data()  # Use the correct method name
                    st.session_state.resume_data = resume_data
                    
                    st.success("Resume processed successfully!")
                    st.rerun()
                
            except Exception as e:
                st.error(f"Error processing resume: {str(e)}")
                return

        # Display resume analysis
        if st.session_state.resume_data:
            resume_data = st.session_state.resume_data
            
            # Initialize resume scorer
            scorer = ResumeScorer()
            score_details = scorer.score_resume(resume_data)
            
            st.markdown("### 📊 Resume Analysis Results")
            
            # Calculate weighted total score
            total_score = round(
                score_details['experience_score'] * 0.35 +
                score_details['skills_score'] * 0.30 +
                score_details['education_score'] * 0.20 +
                score_details['completeness_score'] * 0.15
            )
            
            # Score breakdown in a modern card with gradient
            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
                    padding: 25px;
                    border-radius: 15px;
                    margin: 25px 0;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    color: white;
                ">
                    <h2 style="
                        margin: 0 0 20px 0;
                        font-size: 24px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    ">
                        <span>📊</span> Resume Score Analysis
                    </h2>
                    <div style="
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                    ">
                        <div style="
                            background: rgba(255,255,255,0.1);
                            padding: 15px;
                            border-radius: 10px;
                            text-align: center;
                        ">
                            <div style="font-size: 32px; font-weight: bold;">{total_score}%</div>
                            <div style="opacity: 0.9;">Overall Score</div>
                        </div>
                        <div style="
                            background: rgba(255,255,255,0.1);
                            padding: 15px;
                            border-radius: 10px;
                            text-align: center;
                        ">
                            <div style="font-size: 24px; font-weight: bold;">{score_details['experience_score']}%</div>
                            <div style="opacity: 0.9;">Experience</div>
                        </div>
                        <div style="
                            background: rgba(255,255,255,0.1);
                            padding: 15px;
                            border-radius: 10px;
                            text-align: center;
                        ">
                            <div style="font-size: 24px; font-weight: bold;">{score_details['skills_score']}%</div>
                            <div style="opacity: 0.9;">Skills</div>
                        </div>
                        <div style="
                            background: rgba(255,255,255,0.1);
                            padding: 15px;
                            border-radius: 10px;
                            text-align: center;
                        ">
                            <div style="font-size: 24px; font-weight: bold;">{score_details['education_score']}%</div>
                            <div style="opacity: 0.9;">Education</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            ## Skills recommendation
            st.subheader("**Skills Recommendation💡**")
            ## Skill shows
            keywords = st_tags(label='### Skills that you have',
                               text='See our skills recommendation',
                               value=resume_data['skills'], key='1')

            ##  recommendation
            recommended_skills = []
            reco_field = ''
            rec_course = ''

            # Define skill keywords
            ds_keyword = ['tensorflow','keras','pytorch','machine learning','deep Learning','flask',
                           'streamlit','python','pandas','data analysis','scipy','numpy','data science',
                           'matplotlib','statistics','analytics','visualization','sql','database']
            
            web_keyword = ['react', 'django', 'node js', 'react js', 'php', 'laravel', 'magento', 'wordpress',
                            'javascript', 'angular js', 'c#', 'flask', 'html', 'css', 'bootstrap', 'jquery']
            
            android_keyword = ['android','android development','flutter','kotlin','xml','kivy',
                                'java','mobile development','firebase','sdk','android studio']
            
            ios_keyword = ['ios','ios development','swift','cocoa','cocoa touch','xcode',
                            'objective c','mobile development','apple','swift ui']
            
            uiux_keyword = ['ux','adobe xd','figma','zeplin','balsamiq','ui','prototyping',
                            'wireframes','storyframes','adobe photoshop','photoshop','editing',
                            'adobe illustrator','illustrator','adobe after effects','after effects',
                            'adobe premier pro','premier pro','adobe indesign','indesign','wireframe',
                            'solid','grasp','user research','user experience','sketch','principle','invision']

            ## Courses recommendation based on skills
            for skill in resume_data['skills']:
                check_skill = skill.lower()
                ## Data science recommendation
                if check_skill in ds_keyword:
                    reco_field = 'Data Science'
                    st.success("** Our analysis says you are looking for Data Science Jobs **")
                    recommended_skills = ['Data Visualization','Predictive Analysis','Statistical Modeling',
                                          'Data Mining','Clustering & Classification','Data Analytics',
                                          'Quantitative Analysis','Web Scraping','ML Algorithms','Keras',
                                          'Pytorch','Probability','Scikit-learn','Tensorflow',"Flask",
                                          'Streamlit']
                    recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                   text='Recommended skills generated from your profile',
                                                   value=recommended_skills, key='2')
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to your resume will boost🚀 the chances of getting a Job💼</h4>''',
                              unsafe_allow_html=True)
                    rec_course = ds_course
                    break

                ## Web development recommendation
                elif check_skill in web_keyword:
                    reco_field = 'Web Development'
                    st.success("** Our analysis says you are looking for Web Development Jobs **")
                    recommended_skills = ['React','Django','Node JS','React JS','php','laravel',
                                           'Magento','wordpress','Javascript','Angular JS','c#','Flask',
                                           'SDK']
                    recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                   text='Recommended skills generated from your profile',
                                                   value=recommended_skills, key='3')
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to your resume will boost🚀 the chances of getting a Job💼</h4>''',
                              unsafe_allow_html=True)
                    rec_course = web_course
                    break

                ## Android App Development
                elif check_skill in android_keyword:
                    reco_field = 'Android Development'
                    st.success("** Our analysis says you are looking for Android App Development Jobs **")
                    recommended_skills = ['Android','Android development','Flutter','Kotlin','XML','Java',
                                          'Kivy','GIT','SDK','SQLite']
                    recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                   text='Recommended skills generated from your profile',
                                                   value=recommended_skills, key='4')
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to your resume will boost🚀 the chances of getting a Job💼</h4>''',
                              unsafe_allow_html=True)
                    rec_course = android_course
                    break

                ## IOS App Development
                elif check_skill in ios_keyword:
                    reco_field = 'IOS Development'
                    st.success("** Our analysis says you are looking for IOS App Development Jobs **")
                    recommended_skills = ['IOS','IOS Development','Swift','Cocoa','Cocoa Touch','Xcode',
                                          'Objective-C','SQLite','Plist','StoreKit','UI-Kit','AV Foundation',
                                          'Auto-Layout']
                    recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                   text='Recommended skills generated from your profile',
                                                   value=recommended_skills, key='5')
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to your resume will boost🚀 the chances of getting a Job💼</h4>''',
                              unsafe_allow_html=True)
                    rec_course = ios_course
                    break

                ## Ui-UX Recommendation
                elif check_skill in uiux_keyword:
                    reco_field = 'UI-UX Development'
                    st.success("** Our analysis says you are looking for UI-UX Development Jobs **")
                    recommended_skills = ['UI','User Experience','Adobe XD','Figma','Zeplin','Balsamiq',
                                          'Prototyping','Wireframes','Storyframes','Adobe Photoshop','Editing',
                                          'Illustrator','After Effects','Premier Pro','Indesign','Wireframe',
                                          'Solid','Grasp','User Research']
                    recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                   text='Recommended skills generated from your profile',
                                                   value=recommended_skills, key='6')
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to your resume will boost🚀 the chances of getting a Job💼</h4>''',
                              unsafe_allow_html=True)
                    rec_course = uiux_course
                    break

            ## Insert into table
            ts = time.time()
            cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            if reco_field:
                # Define candidate level based on pages
                if resume_data['no_of_pages'] == 1:
                    cand_level = "Beginner"
                elif resume_data['no_of_pages'] == 2:
                    cand_level = "Intermediate"
                else:
                    cand_level = "Expert"
                    
                ## Resume writing recommendation
                st.markdown("### Resume Tips & Ideas💡")
                
                # Create columns for tips
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("""
                        <div style='background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>
                            <div style="font-size: 1.2em; margin-bottom: 10px;">🎯 Career Objective</div>
                            <div style="color: #666; font-size: 0.9em;">Add your career intention to help recruiters understand your goals</div>
                        </div>
                        
                        <div style='background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>
                            <div style="font-size: 1.2em; margin-bottom: 10px;">✍ Declaration</div>
                            <div style="color: #666; font-size: 0.9em;">Include a declaration to verify the authenticity of your information</div>
                        </div>
                        
                        <div style='background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>
                            <div style="font-size: 1.2em; margin-bottom: 10px;">⚽ Hobbies</div>
                            <div style="color: #666; font-size: 0.9em;">Show your personality and cultural fit through your interests</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                        <div style='background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>
                            <div style="font-size: 1.2em; margin-bottom: 10px;">🏅 Achievements</div>
                            <div style="color: #666; font-size: 0.9em;">Highlight your accomplishments to demonstrate your capabilities</div>
                        </div>
                        
                        <div style='background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>
                            <div style="font-size: 1.2em; margin-bottom: 10px;">👨‍💻 Projects</div>
                            <div style="color: #666; font-size: 0.9em;">Showcase relevant work experience through your projects</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Calculate resume score
                resume_score = score_details['total_score']
                
                # Initialize database connection
                connection = sqlite3.connect(DB_PATH + DB_FILE)
                cursor = connection.cursor()
                
                # Create table with all necessary columns
                cursor.execute('''CREATE TABLE IF NOT EXISTS user_data
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
                                PDF_Name TEXT)''')
                connection.commit()
                
                ## Insert into table
                insert_data = (
                    None,  # ID will be auto-generated
                    resume_data['name'],
                    resume_data['email'],
                    resume_score,
                    cur_date,
                    resume_data['no_of_pages'],
                    reco_field,
                    cand_level,
                    str(resume_data['skills']),
                    str(recommended_skills),
                    str(rec_course),
                    pdf_file.name
                )
                
                cursor.execute('''INSERT INTO user_data 
                                (ID, Name, Email, Resume_Score, Timestamp, Total_Page,
                                Predicted_Field, User_Level, Actual_Skills,
                                Recommended_Skills, Recommended_Courses, PDF_Name)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', insert_data)
                connection.commit()
                connection.close()

                ## Recommending courses
                st.markdown("""
                    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 10px;">
                        <h2 style="color: #0e1117; margin-bottom: 15px;">🎓 Learning Path Recommendations</h2>
                    </div>
                """, unsafe_allow_html=True)
                
                if rec_course:
                    # Course selection slider with better labels
                    no_of_reco = st.slider(
                        "Adjust course count",
                        min_value=1,
                        max_value=len(rec_course),
                        value=3,
                        format="%d courses",
                        help="Drag to adjust the number of courses you want to see"
                    )
                    
                    # Course counter
                    st.markdown(f'''
                        <div style="
                            text-align: right;
                            color: #2b5876;
                            font-size: 0.9rem;
                            margin: 0.5rem 0 1rem 0;
                        ">
                            Showing {no_of_reco} out of {len(rec_course)} courses
                        </div>
                    ''', unsafe_allow_html=True)
                    
                    # Display selected number of courses
                    for i, (course_name, course_link) in enumerate(rec_course[:no_of_reco]):
                        st.markdown(f'''
                            <a href="{course_link}" 
                               target="_blank"
                               style="
                                    display: block;
                                    text-decoration: none;
                                    cursor: pointer;
                                    padding: 1rem;
                                    margin: 0.8rem 0;
                                    background: #f0f2f6;
                                    border-radius: 8px;
                                    border-left: 4px solid #2b5876;
                                    color: #2b5876;
                                ">
                                <span>🔗 {course_name}</span>
                                <span style="float: right;">↗️</span>
                            </a>
                        ''', unsafe_allow_html=True)
                else:
                    st.info("Add skills to get personalized course recommendations")
                
                # Modern Resume Insights Section with Enhanced UI
                st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
                        padding: 25px;
                        border-radius: 15px;
                        margin: 25px 0;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    ">
                        <h2 style="
                            color: white;
                            margin-bottom: 15px;
                            font-size: 24px;
                            display: flex;
                            align-items: center;
                            gap: 10px;
                        ">
                            <span>📋</span> Resume Intelligence Report
                        </h2>
                        <p style="color: #e0e0e0; margin: 0;">Comprehensive analysis of your professional profile</p>
                    </div>
                """, unsafe_allow_html=True)

                # Strengths Analysis with Modern Cards
                st.markdown("""
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        margin: 20px 0;
                        background: linear-gradient(90deg, #43cea2 0%, #185a9d 100%);
                        padding: 15px;
                        border-radius: 10px;
                        color: white;
                    ">
                        <span style="font-size: 24px;">💪</span>
                        <h3 style="margin: 0; color: white;">Professional Strengths</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                strengths = []
                
                # Technical Skills Analysis
                skills = resume_data['skills']
                if len(skills) >= 5:
                    skill_strength = "🛠️ Strong technical skill set with {} different skills".format(len(skills))
                    if len(skills) >= 8:
                        skill_strength += " - Impressive variety! 🌟"
                    strengths.append(skill_strength)
                    
                    # Check for in-demand skills
                    in_demand_skills = ['python', 'java', 'javascript', 'react', 'sql', 'machine learning', 'aws', 'docker']
                    matched_demands = [skill for skill in skills if any(demand in skill.lower() for demand in in_demand_skills)]
                    if matched_demands:
                        strengths.append("🚀 Possesses in-demand skills: " + ", ".join(matched_demands[:3]))

                # Experience Analysis
                experience = resume_data['experience']
                if experience:
                    exp_years = len(experience)
                    if exp_years >= 2:
                        strengths.append(f"💼 Strong work history with {exp_years} different roles")
                    
                    detailed_exp = [exp for exp in experience if len(exp.split()) > 10]
                    if detailed_exp:
                        strengths.append("📝 Detailed work experience descriptions")
                    
                    achievement_keywords = ['achieved', 'improved', 'increased', 'reduced', 'led', 'managed', 'developed']
                    achievements = [exp for exp in experience if any(keyword in exp.lower() for keyword in achievement_keywords)]
                    if achievements:
                        strengths.append("🏆 Contains quantifiable achievements and leadership examples")

                # Education Analysis
                education = resume_data['education']
                if education:
                    edu_str = "🎓 Strong educational background with {} qualification(s)".format(len(education))
                    higher_edu_keywords = ['master', 'phd', 'bachelor', 'degree']
                    if any(keyword in str(education).lower() for keyword in higher_edu_keywords):
                        edu_str += " including higher education ✨"
                    strengths.append(edu_str)

                # Overall Score Analysis
                if total_score >= 80:
                    strengths.append(f"⭐ Exceptional overall resume score: {total_score}%")
                elif total_score >= 60:
                    strengths.append(f"📈 Above average resume score: {total_score}%")

                # Display strengths in modern cards
                for strength in strengths:
                    st.markdown(f"""
                        <div style="
                            margin: 10px 0;
                            padding: 15px;
                            background: white;
                            border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                            border-left: 5px solid #43cea2;
                            font-size: 16px;
                            color: #2c3e50;
                        ">{strength}</div>
                    """, unsafe_allow_html=True)

                # Areas for Improvement with Modern UI
                st.markdown("""
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        margin: 30px 0 20px 0;
                        background: linear-gradient(90deg, #ff6b6b 0%, #556270 100%);
                        padding: 15px;
                        border-radius: 10px;
                        color: white;
                    ">
                        <span style="font-size: 24px;">🎯</span>
                        <h3 style="margin: 0; color: white;">Growth Opportunities</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                improvements = []
                
                # Skills Improvements
                if len(skills) < 5:
                    improvements.append({
                        'icon': '⚡',
                        'area': 'Technical Skills',
                        'issue': f"Currently only {len(skills)} skills listed",
                        'suggestion': "Add more relevant technical skills, especially those mentioned in job descriptions in your field"
                    })
                else:
                    improvements.append({
                        'icon': '🔍',
                        'area': 'Skills Organization',
                        'issue': 'Skills could be better organized',
                        'suggestion': "Consider grouping your skills into categories (e.g., Programming Languages, Tools, Soft Skills)"
                    })

                # Experience Improvements
                if not experience:
                    improvements.append({
                        'icon': '💼',
                        'area': 'Work Experience',
                        'issue': 'Limited work experience section',
                        'suggestion': "Add internships, projects, or volunteer work if you're new to the field"
                    })
                else:
                    if not any(len(exp.split()) > 15 for exp in experience):
                        improvements.append({
                            'icon': '📝',
                            'area': 'Experience Descriptions',
                            'issue': 'Brief experience descriptions',
                            'suggestion': "Expand your role descriptions with specific responsibilities and achievements"
                        })
                    
                    if not any(keyword in str(experience).lower() for keyword in ['achieved', 'improved', 'increased', 'reduced']):
                        improvements.append({
                            'icon': '📊',
                            'area': 'Achievements',
                            'issue': 'Limited quantifiable achievements',
                            'suggestion': "Add specific metrics and numbers to showcase your impact (e.g., 'Improved efficiency by 25%')"
                        })

                # Education Improvements
                if not education:
                    improvements.append({
                        'icon': '🎓',
                        'area': 'Education',
                        'issue': 'Education section needs enhancement',
                        'suggestion': "Add your educational background, including relevant coursework and certifications"
                    })

                # Score-based Improvements
                if total_score < 60:
                    improvements.append({
                        'icon': '📈',
                        'area': 'Overall Resume',
                        'issue': f"Current resume score: {total_score}%",
                        'suggestion': "Focus on adding more detailed experience descriptions and relevant skills to improve your score"
                    })

                # Display improvements in modern cards
                for imp in improvements:
                    st.markdown(f"""
                        <div style="
                            margin: 15px 0;
                            padding: 20px;
                            background: white;
                            border-radius: 12px;
                            box-shadow: 0 3px 12px rgba(0,0,0,0.07);
                            border-left: 5px solid #ff6b6b;
                        ">
                            <div style="
                                display: flex;
                                align-items: center;
                                gap: 10px;
                                margin-bottom: 10px;
                            ">
                                <span style="font-size: 24px;">{imp['icon']}</span>
                                <div style="
                                    color: #2b5876;
                                    font-weight: 600;
                                    font-size: 18px;
                                ">{imp['area']}</div>
                            </div>
                            <div style="
                                color: #666;
                                margin-bottom: 8px;
                                font-size: 14px;
                            ">Current: {imp['issue']}</div>
                            <div style="
                                color: #1e88e5;
                                font-size: 15px;
                                line-height: 1.5;
                            ">💡 {imp['suggestion']}</div>
                        </div>
                    """, unsafe_allow_html=True)

                # Enhanced Action Steps with Modern UI
                if improvements:
                    st.markdown("""
                        <div style="
                            display: flex;
                            align-items: center;
                            gap: 10px;
                            margin: 30px 0 20px 0;
                            background: linear-gradient(90deg, #4e54c8 0%, #8f94fb 100%);
                            padding: 15px;
                            border-radius: 10px;
                            color: white;
                        ">
                            <span style="font-size: 24px;">🚀</span>
                            <h3 style="margin: 0; color: white;">Next Steps for Success</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("""
                        <div style="
                            background: white;
                            padding: 25px;
                            border-radius: 12px;
                            box-shadow: 0 3px 12px rgba(0,0,0,0.07);
                            margin: 10px 0;
                        ">
                            <div style="
                                color: #2b5876;
                                font-weight: 500;
                                margin-bottom: 20px;
                                font-size: 17px;
                            ">Follow these steps to elevate your resume:</div>
                            <ol style="
                                margin: 0;
                                padding-left: 20px;
                                color: #2c3e50;
                            ">
                                <li style="margin: 12px 0;">🎯 Review and prioritize the improvement suggestions above based on your career goals</li>
                                <li style="margin: 12px 0;">📊 Add measurable achievements to showcase your impact</li>
                                <li style="margin: 12px 0;">🔍 Align your skills with industry requirements</li>
                                <li style="margin: 12px 0;">🔑 Incorporate relevant keywords from target job descriptions</li>
                                <li style="margin: 12px 0;">🔄 Re-analyze your resume here after making updates</li>
                            </ol>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.error('Something went wrong..')
    else:
        ## Admin Side with modern design
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
                padding: 25px;
                border-radius: 15px;
                margin: 25px 0;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            ">
                <h2 style="
                    color: white;
                    margin: 0 0 10px 0;
                    font-size: 24px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    <span>👨‍💼</span> Admin Dashboard
                </h2>
                <p style="color: #e0e0e0; margin: 0;">Access administrative features and analytics</p>
            </div>
        """, unsafe_allow_html=True)

        # Admin login with modern card design
        st.markdown("""
            <div style="
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 3px 12px rgba(0,0,0,0.07);
                margin: 20px 0;
            ">
                <div style="
                    color: #2b5876;
                    font-weight: 500;
                    margin-bottom: 20px;
                    font-size: 18px;
                ">🔐 Admin Login</div>
            </div>
        """, unsafe_allow_html=True)
        
        ad_user = st.text_input("Username")
        ad_password = st.text_input("Password", type='password')
        if st.button('Login'):
            if ad_user == 'Admin' and ad_password == '9632':
                st.success("Welcome Dear Admin")
                # Display Data
                connection = sqlite3.connect(DB_PATH + DB_FILE)
                cursor = connection.cursor()
                
                # First, let's get the table structure
                cursor.execute("PRAGMA table_info(user_data)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # Now get the data
                cursor.execute('SELECT * FROM user_data')
                data = cursor.fetchall()
                st.header("**User's👨‍💻 Data**")
                
                # Create DataFrame with actual columns from database
                df = pd.DataFrame(data, columns=columns)
                
                # Rename columns for display if needed
                column_mapping = {
                    'Resume_Score': 'Resume Score',
                    'Total_Page': 'Total Pages',
                    'Predicted_Field': 'Predicted Field',
                    'User_Level': 'User Level',
                    'Actual_Skills': 'Actual Skills',
                    'Recommended_Skills': 'Recommended Skills',
                    'Recommended_Courses': 'Recommended Courses',
                    'PDF_Name': 'PDF Name'
                }
                df = df.rename(columns=column_mapping)
                st.dataframe(df)
                st.markdown(get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)
                
                ## Fetch data for plots
                query = 'SELECT Predicted_Field, User_Level FROM user_data'
                plot_data = pd.read_sql(query, connection)
                
                if not plot_data.empty:
                    ## Pie chart for predicted field recommendations
                    st.subheader("📈 **Predicted Field Distribution**")
                    
                    field_counts = plot_data['Predicted_Field'].value_counts()
                    field_df = pd.DataFrame({
                        'Field': field_counts.index,
                        'Count': field_counts.values
                    })
                    
                    if not field_df.empty:
                        fig = px.pie(field_df, values='Count', names='Field',
                                   title='Distribution of Predicted Fields')
                        st.plotly_chart(fig)
                    else:
                        st.info("No field data available for visualization")

                    ### Pie chart for User's Experience Level
                    st.subheader("📈 **Experience Level Distribution**")
                    
                    level_counts = plot_data['User_Level'].value_counts()
                    level_df = pd.DataFrame({
                        'Level': level_counts.index,
                        'Count': level_counts.values
                    })
                    
                    if not level_df.empty:
                        fig = px.pie(level_df, values='Count', names='Level',
                                   title='Distribution of Experience Levels')
                        st.plotly_chart(fig)
                    else:
                        st.info("No experience level data available for visualization")
                else:
                    st.info("No data available for visualization")
                
                # Close database connection
                connection.close()
                
if __name__ == "__main__":
    main()
