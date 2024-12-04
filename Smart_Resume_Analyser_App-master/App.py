"""Main application file for the Smart Resume Analyzer."""

import streamlit as st
import pandas as pd
import time
from pathlib import Path
import os
import nltk
from nltk.corpus import stopwords
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
    nltk.download('punkt')
from nltk.tokenize import word_tokenize
import base64, random
import datetime
from custom_parser import CustomResumeParser
from resume_scorer import ResumeScorer
from course_recommender import CourseRecommender
from constants import UPLOAD_DIR, DB_PATH, DB_FILE
from database_utils import (
    init_db, get_user_data, delete_user, delete_admin,
    insert_user_data
)
from ui_utils import (
    get_custom_css, 
    show_header,
    get_table_download_link,
    create_score_bar
)
from streamlit_tags import st_tags
from PIL import Image
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io
import requests
try:
    from login import LoginUI
except ImportError:
    # Fallback for Streamlit Cloud
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from login import LoginUI
from hashlib import sha256

# Set page configuration
st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon='📄',
    layout='wide'
)

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Create necessary directories if they don't exist
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(DB_PATH, exist_ok=True)
except Exception as e:
    st.warning(f"Note: Directory creation failed - this is normal in Streamlit Cloud. Error: {e}")

# Initialize login system
login_ui = LoginUI()

# Initialize resume database
def init_db():
    """Initialize the database and create tables if they don't exist"""
    try:
        # Use absolute path for database in Streamlit Cloud
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resume_data.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Create user_data table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS user_data
                    (ID TEXT PRIMARY KEY,
                    Name TEXT,
                    Email TEXT,
                    Resume_Score TEXT,
                    Timestamp TEXT,
                    Total_Page TEXT,
                    Predicted_Field TEXT,
                    User_Level TEXT,
                    Actual_Skills TEXT,
                    Recommended_Skills TEXT,
                    Recommended_Courses TEXT,
                    PDF_Name TEXT,
                    Original_Resume_Path TEXT)''')
        
        # Check if Original_Resume_Path column exists, if not add it
        cursor = conn.execute('PRAGMA table_info(user_data)')
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'Original_Resume_Path' not in columns:
            try:
                c.execute('ALTER TABLE user_data ADD COLUMN Original_Resume_Path TEXT')
                conn.commit()
            except sqlite3.Error as e:
                st.error(f"Error adding column: {e}")
        
        conn.commit()
    except Exception as e:
        st.error(f"Database initialization error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# Initialize session state
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'current_file' not in st.session_state:
    st.session_state.current_file = None
if 'resume_data' not in st.session_state:
    st.session_state.resume_data = None
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = None

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

# Database functions
def init_db():
    """Initialize the database and create required tables if they don't exist."""
    try:
        conn = sqlite3.connect('resume_data.db', timeout=20)
        cursor = conn.cursor()
        
        # Drop existing table if it exists
        cursor.execute('DROP TABLE IF EXISTS user_data')
        
        # Create user_data table with correct structure
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                ID TEXT PRIMARY KEY,
                Name TEXT,
                Email TEXT,
                Resume_Score TEXT,
                Timestamp TEXT,
                Total_Page TEXT,
                Predicted_Field TEXT,
                User_Level TEXT,
                Actual_Skills TEXT,
                Recommended_Skills TEXT,
                Recommended_Courses TEXT,
                PDF_Name TEXT,
                Original_Resume_Path TEXT
            )
        ''')
        
        conn.commit()
        st.success("Database initialized successfully!")
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

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

def download_resume(resume_data, applicant_name):
    # Create a temporary file with the resume content
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as tmp:
        tmp.write(str(resume_data))
        tmp_path = tmp.name
    
    # Read the file content for download
    with open(tmp_path, 'rb') as file:
        content = file.read()
    
    # Clean up the temporary file
    os.unlink(tmp_path)
    
    return content

def process_resume(uploaded_file):
    try:
        # Save the original file
        file_path = os.path.join("Uploaded_Resumes", uploaded_file.name)
        os.makedirs("Uploaded_Resumes", exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        # Process the resume content
        resume_text = extract_text_from_pdf(file_path)
        if resume_text:
            parser = CustomResumeParser(file_path)
            resume_data = parser.get_extracted_data()
            if resume_data:
                resume_data['original_resume_path'] = file_path  # Store the path to original resume
                return resume_data
        return None
    except Exception as e:
        st.error(f'Error processing PDF: {str(e)}')
        return None

def main():
    """Main function for the Smart Resume Analyzer App"""
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    # Initialize database
    init_db()
    
    # Initialize login UI
    login_ui = LoginUI()
    
    # Show header
    show_header()
    
    # Handle user authentication
    if not login_ui.is_authenticated():
        login_ui.render_login_ui()
        return
    
    # Get user type
    user_type = login_ui.get_user_type()
    
    # Show navigation bar with logout option
    st.markdown("""
        <div class="navbar">
            <div style="color: white; margin-right: auto;">
                Welcome, {} ({})
            </div>
            <a href="#" class="nav-item" id="logout-btn">Logout</a>
        </div>
    """.format(login_ui.get_username(), user_type.title()), unsafe_allow_html=True)
    
    if st.sidebar.button("Logout"):
        login_ui.logout()
        st.rerun()

    # Add delete account section in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚠️ Account Management")
    
    # Create two columns for the delete button and confirmation
    del_col1, del_col2 = st.sidebar.columns(2)
    
    if "show_delete_confirmation" not in st.session_state:
        st.session_state.show_delete_confirmation = False
    
    if del_col1.button("Delete Account", type="secondary"):
        st.session_state.show_delete_confirmation = True
    
    if st.session_state.show_delete_confirmation:
        st.sidebar.warning("⚠️ This action cannot be undone!")
        confirm_col1, confirm_col2 = st.sidebar.columns(2)
        
        if confirm_col1.button("Yes, Delete", type="primary", key="confirm_delete"):
            if user_type == "admin":
                if delete_admin(st.session_state.username):
                    st.sidebar.success("Admin account deleted successfully!")
                    login_ui.logout()
                    st.rerun()
            else:
                if delete_user(st.session_state.username):
                    st.sidebar.success("User account deleted successfully!")
                    login_ui.logout()
                    st.rerun()
        
        if confirm_col2.button("Cancel", type="secondary", key="cancel_delete"):
            st.session_state.show_delete_confirmation = False

    # Show application status for normal users in sidebar
    if user_type == "normal":
        st.sidebar.markdown("### 📋 Your Applications")
        applications = login_ui.get_user_applications(st.session_state.username, 'normal')
        
        if applications:
            for company, date, status in applications:
                status_color = {
                    'pending': '🟡',
                    'accepted': '🟢',
                    'rejected': '🔴'
                }.get(status.lower(), '⚪')
                
                st.sidebar.markdown(f"""
                    <div style="
                        background: white;
                        padding: 10px;
                        border-radius: 5px;
                        margin-bottom: 10px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    ">
                        <div style="font-weight: bold; margin-bottom: 5px;">
                            {company} {status_color}
                        </div>
                        <div style="color: #666; font-size: 0.9em;">
                            Status: {status.title()}<br>
                            Date: {date}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.sidebar.info("No applications submitted yet")

    if user_type == "admin":
        st.markdown("""
            <div style="
                background: linear-gradient(120deg, #2b5876 0%, #4e4376 100%);
                padding: 25px;
                border-radius: 15px;
                margin: 25px 0;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            ">
                <h1 style="
                    color: white;
                    margin: 0 0 10px 0;
                    font-size: 28px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    <span>👔</span> Admin Dashboard
                </h1>
                <p style="
                    color: rgba(255,255,255,0.9);
                    margin: 0;
                    font-size: 16px;
                ">View and manage resume submissions and applications.</p>
            </div>
        """, unsafe_allow_html=True)

        # Add choices for admin
        choice = st.selectbox("Choose your task", ["View Applications", "Visual Analytics"])

        if choice == "View Applications":
            # Get applications for this admin
            applications = login_ui.get_user_applications(st.session_state.username, 'admin')
            
            if applications:
                # Convert to DataFrame for better display
                applications_df = pd.DataFrame(
                    applications,
                    columns=['Applicant', 'Resume Data', 'Resume Score', 'Application Date', 'Status']
                )
                
                # Summary statistics
                st.markdown("### 📊 Summary Statistics")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                        <div style="
                            padding: 20px;
                            background: white;
                            border-radius: 10px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                            text-align: center;
                        ">
                            <div style="font-size: 32px; color: #2b5876; font-weight: bold;">
                                {len(applications_df)}
                            </div>
                            <div style="color: #666;">Total Applications</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    avg_score = applications_df['Resume Score'].astype(float).mean()
                    st.markdown(f"""
                        <div style="
                            padding: 20px;
                            background: white;
                            border-radius: 10px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                            text-align: center;
                        ">
                            <div style="font-size: 32px; color: #2b5876; font-weight: bold;">
                                {avg_score:.1f}%
                            </div>
                            <div style="color: #666;">Average Score</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    pending_count = len(applications_df[applications_df['Status'] == 'pending'])
                    st.markdown(f"""
                        <div style="
                            padding: 20px;
                            background: white;
                            border-radius: 10px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                            text-align: center;
                        ">
                            <div style="font-size: 32px; color: #2b5876; font-weight: bold;">
                                {pending_count}
                            </div>
                            <div style="color: #666;">Pending Applications</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Display applications
                st.markdown("### 📝 Applications")
                for index, row in applications_df.iterrows():
                    with st.expander(f"Application from {row['Applicant']} - {row['Application Date']}"):
                        st.markdown("""
                        <style>
                        .info-box {
                            background-color: #f8f9fa;
                            border-radius: 5px;
                            padding: 15px;
                            margin: 10px 0;
                        }
                        .info-title {
                            color: #2b5876;
                            font-weight: bold;
                            margin-bottom: 5px;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                        # Basic Information
                        st.markdown('<div class="info-box">', unsafe_allow_html=True)
                        st.markdown('<p class="info-title">📋 Basic Information</p>', unsafe_allow_html=True)
                        st.write(f"**Name:** {row['Applicant']}")
                        
                        # Parse resume data
                        try:
                            resume_data = eval(row['Resume Data'])
                            email = resume_data.get('email', 'Not provided')
                            mobile = resume_data.get('mobile_number', 'Not provided')
                            skills = resume_data.get('skills', [])
                            
                            st.write(f"**Email:** {email}")
                            st.write(f"**Mobile:** {mobile}")
                        except:
                            st.write("Error parsing resume data")
                        st.markdown('</div>', unsafe_allow_html=True)

                        # Skills and Score
                        st.markdown('<div class="info-box">', unsafe_allow_html=True)
                        st.markdown('<p class="info-title">🎯 Skills & Score</p>', unsafe_allow_html=True)
                        if 'skills' in locals():
                            st.write("**Skills:**", ", ".join(skills) if skills else "No skills listed")
                        st.write(f"**Resume Score:** {row['Resume Score']}%")
                        st.write(f"**Current Status:** {row['Status'].title()}")
                        st.markdown('</div>', unsafe_allow_html=True)

                        # Download Resume Button
                        st.markdown('<div class="info-box">', unsafe_allow_html=True)
                        st.markdown('<p class="info-title">📄 Resume</p>', unsafe_allow_html=True)
                        
                        try:
                            # Get resume data and original file path
                            resume_data = eval(row['Resume Data'])
                            original_resume_path = resume_data.get('original_resume_path')
                            
                            if original_resume_path and os.path.exists(original_resume_path):
                                with open(original_resume_path, 'rb') as file:
                                    resume_content = file.read()
                                    file_name = os.path.basename(original_resume_path)
                                    
                                st.download_button(
                                    label="📥 Download Original Resume",
                                    data=resume_content,
                                    file_name=file_name,
                                    mime="application/pdf",
                                    help="Click to download the original resume",
                                    key=f"download_{index}"
                                )
                            else:
                                st.warning("Original resume file not available")
                        except Exception as e:
                            st.error(f"Error preparing resume download: {str(e)}")
                            
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        if row['Status'] == 'pending':
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button('Accept', key=f'accept_{index}'):
                                    if login_ui.update_application_status(row['Applicant'], st.session_state.username, 'accepted'):
                                        st.success('Application accepted!')
                                        st.rerun()
                            with col2:
                                if st.button('Reject', key=f'reject_{index}'):
                                    if login_ui.update_application_status(row['Applicant'], st.session_state.username, 'rejected'):
                                        st.success('Application rejected!')
                                        st.rerun()
            else:
                st.info("No applications received yet")

        elif choice == "Visual Analytics":
            # Get applications for analytics
            applications = login_ui.get_user_applications(st.session_state.username, 'admin')
            
            if applications:
                # Convert to DataFrame for analytics
                applications_df = pd.DataFrame(
                    applications,
                    columns=['Applicant', 'Resume Data', 'Resume Score', 'Application Date', 'Status']
                )
                
                st.markdown("### 📊 Application Analytics")
                
                # Create two columns for charts
                col1, col2 = st.columns(2)
                
                with col1:
                    # Application Status Distribution
                    status_counts = applications_df['Status'].value_counts()
                    
                    # Create donut chart for application statuses
                    fig = go.Figure(data=[go.Pie(
                        labels=status_counts.index,
                        values=status_counts.values,
                        hole=0.5,
                        marker=dict(colors=['#ff9999', '#66b3ff', '#99ff99'])
                    )])
                    
                    fig.update_layout(
                        title="Distribution of Application Statuses",
                        showlegend=True,
                        annotations=[dict(text='Status', x=0.5, y=0.5, font_size=20, showarrow=False)],
                        width=400,
                        height=400
                    )
                    
                    st.plotly_chart(fig)
                
                with col2:
                    # Resume Score Distribution
                    fig = px.histogram(
                        applications_df,
                        x='Resume Score',
                        nbins=10,
                        title='Distribution of Resume Scores',
                        color_discrete_sequence=['#2b5876']
                    )
                    
                    fig.update_layout(
                        xaxis_title="Resume Score (%)",
                        yaxis_title="Number of Applications",
                        showlegend=False,
                        width=400,
                        height=400
                    )
                    
                    st.plotly_chart(fig)
                
                # Additional analytics
                st.markdown("### 📈 Detailed Analytics")
                
                # Score statistics
                score_stats = applications_df['Resume Score'].astype(float).describe()
                
                stats_cols = st.columns(4)
                with stats_cols[0]:
                    st.metric("Average Score", f"{score_stats['mean']:.1f}%")
                with stats_cols[1]:
                    st.metric("Median Score", f"{score_stats['50%']:.1f}%")
                with stats_cols[2]:
                    st.metric("Highest Score", f"{score_stats['max']:.1f}%")
                with stats_cols[3]:
                    st.metric("Lowest Score", f"{score_stats['min']:.1f}%")
                
                # Time series of applications
                applications_df['Application Date'] = pd.to_datetime(applications_df['Application Date'])
                daily_apps = applications_df.groupby('Application Date').size().reset_index(name='count')
                
                fig = px.line(
                    daily_apps,
                    x='Application Date',
                    y='count',
                    title='Applications Over Time',
                    color_discrete_sequence=['#2b5876']
                )
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Number of Applications",
                    showlegend=False
                )
                
                st.plotly_chart(fig)
                
            else:
                st.info("No applications data available for analysis")
                
        elif choice == "Uploaded Resumes":
            st.write("#### Data Visualization")
            
            # Initialize database connection
            connection = sqlite3.connect('users.db')
            cursor = connection.cursor()
            
            ## Create the DB
            cursor.execute('''CREATE TABLE IF NOT EXISTS Predictions
                            (Name TEXT,
                             Predicted_Field TEXT,
                             Prediction_Probability NUMBER,
                             Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
                             ''')
            connection.commit()
            
            ## Fetch data
            cursor.execute('''SELECT COUNT(Predicted_Field) as Count, Predicted_Field 
                            FROM Predictions
                            GROUP BY Predicted_Field''')
            data = cursor.fetchall()
            
            # Close the connection
            cursor.close()
            connection.close()
            
            if data:
                field_counts = pd.DataFrame(data, columns=['Count', 'Category'])
                
                # Plot
                fig = px.bar(field_counts, 
                           x='Category',
                           y='Count',
                           title='Category Distribution in Uploaded Resumes')
                st.plotly_chart(fig)
            else:
                st.info("No data to display yet")
                
        elif choice == "Prediction Results":
            st.write("### 📊 Prediction Analysis")
            
            # Initialize database connection
            conn = sqlite3.connect('resume_data.db')
            cursor = conn.cursor()
            
            # Get prediction data
            cursor.execute('''
                SELECT Name, Predicted_Field, Resume_Score, Timestamp 
                FROM user_data 
                ORDER BY Timestamp DESC
            ''')
            predictions = cursor.fetchall()
            conn.close()
            
            if predictions:
                pred_df = pd.DataFrame(
                    predictions,
                    columns=['Name', 'Predicted Field', 'Resume Score', 'Submission Date']
                )
                
                # Show predictions table
                st.write("#### Recent Predictions")
                st.dataframe(pred_df)
                
                # Visualization
                st.write("#### Field Distribution")
                field_counts = pred_df['Predicted Field'].value_counts()
                fig = px.pie(
                    values=field_counts.values,
                    names=field_counts.index,
                    title='Distribution of Predicted Fields',
                    color_discrete_sequence=px.colors.sequential.Viridis
                )
                st.plotly_chart(fig)
                
                # Score Distribution
                st.write("#### Score Distribution")
                fig = px.histogram(
                    pred_df,
                    x='Resume Score',
                    nbins=20,
                    title='Distribution of Resume Scores',
                    color_discrete_sequence=['#2b5876']
                )
                st.plotly_chart(fig)
            else:
                st.info("No prediction data available")
                
        elif choice == "Ranked Resumes":
            st.write("### 🏆 Resume Rankings")
            
            # Initialize database connection
            conn = sqlite3.connect('resume_data.db')
            cursor = conn.cursor()
            
            # Get resume data with scores
            cursor.execute('''
                SELECT Name, Predicted_Field, Resume_Score, User_Level, Timestamp 
                FROM user_data 
                ORDER BY Resume_Score DESC
            ''')
            rankings = cursor.fetchall()
            conn.close()
            
            if rankings:
                rank_df = pd.DataFrame(
                    rankings,
                    columns=['Name', 'Field', 'Score', 'Experience Level', 'Submission Date']
                )
                
                # Add rank column
                rank_df['Rank'] = range(1, len(rank_df) + 1)
                
                # Reorder columns to show rank first
                rank_df = rank_df[['Rank', 'Name', 'Field', 'Score', 'Experience Level', 'Submission Date']]
                
                # Show rankings
                st.write("#### Top Resumes")
                st.dataframe(rank_df)
                
                # Visualization
                st.write("#### Score Distribution by Field")
                fig = px.box(
                    rank_df,
                    x='Field',
                    y='Score',
                    title='Resume Scores by Field',
                    color='Field',
                    points='all'
                )
                st.plotly_chart(fig)
                
                # Experience Level Distribution
                st.write("#### Experience Level Distribution")
                level_counts = rank_df['Experience Level'].value_counts()
                fig = px.pie(
                    values=level_counts.values,
                    names=level_counts.index,
                    title='Distribution of Experience Levels',
                    color_discrete_sequence=px.colors.sequential.Viridis
                )
                st.plotly_chart(fig)
            else:
                st.info("No ranking data available")
                
        elif choice == "Recommendations":
            st.write("### 💡 Resume Improvement Recommendations")
            
            # Initialize database connection
            conn = sqlite3.connect('resume_data.db')
            cursor = conn.cursor()
            
            # Get resume data
            cursor.execute('''
                SELECT Name, Resume_Score, Actual_Skills, Recommended_Skills, 
                       Recommended_Courses, User_Level 
                FROM user_data 
                ORDER BY Timestamp DESC
            ''')
            recommendations = cursor.fetchall()
            conn.close()
            
            if recommendations:
                for name, score, actual_skills, recommended_skills, courses, level in recommendations:
                    with st.expander(f"Recommendations for {name} (Score: {score}%)"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("""
                                <div style="
                                    background: white;
                                    padding: 20px;
                                    border-radius: 10px;
                                    margin-bottom: 10px;
                                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                                ">
                                    <h4 style="color: #2b5876; margin-bottom: 10px;">
                                        🎯 Current Profile
                                    </h4>
                                    <p><strong>Experience Level:</strong> {}</p>
                                    <p><strong>Current Skills:</strong></p>
                                    {}
                                </div>
                            """.format(
                                level,
                                "<br>".join([f"• {skill.strip()}" for skill in eval(actual_skills)])
                            ), unsafe_allow_html=True)
                            
                        with col2:
                            st.markdown("""
                                <div style="
                                    background: white;
                                    padding: 20px;
                                    border-radius: 10px;
                                    margin-bottom: 10px;
                                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                                ">
                                    <h4 style="color: #2b5876; margin-bottom: 10px;">
                                        💪 Recommended Improvements
                                    </h4>
                                    <p><strong>Skills to Add:</strong></p>
                                    {}
                                </div>
                            """.format(
                                "<br>".join([f"• {skill.strip()}" for skill in eval(recommended_skills)])
                            ), unsafe_allow_html=True)
                        
                        st.markdown("""
                            <div style="
                                background: white;
                                padding: 20px;
                                border-radius: 10px;
                                margin-top: 10px;
                                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                            ">
                                <h4 style="color: #2b5876; margin-bottom: 10px;">
                                    📚 Recommended Courses
                                </h4>
                                {}
                            </div>
                        """.format(
                            "<br>".join([f"• {course.strip()}" for course in eval(courses)])
                        ), unsafe_allow_html=True)
            else:
                st.info("No recommendation data available")
                
        else:
            st.write("### About")
            st.write("""
            #### Smart Resume Analyzer
            - Analyzes resumes and provides insights
            - Uses ML for predictions
            - Helps streamline recruitment
            
            #### Features
            1. Resume Parsing
            2. Skill Analysis
            3. Category Prediction
            4. Resume Score
            5. Recommendations
            
            #### Technologies
            - Python
            - Streamlit
            - Machine Learning
            - NLP
            """)

    if user_type == "normal":
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
                    <div style="display: flex; align-items: center; gap: 10px; color: #2b5876;">
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
                # Process the resume
                resume_data = process_resume(pdf_file)
                
                if resume_data:
                    st.session_state.resume_text = extract_text_from_pdf(os.path.join("Uploaded_Resumes", pdf_file.name))
                    st.session_state.current_file = pdf_file.name
                    st.session_state.processed_files.add(pdf_file.name)
                    
                    # Calculate predicted field based on skills
                    skills = resume_data.get('skills', [])
                    predicted_field = 'Unknown'
                    if skills:
                        tech_skills = ['python', 'java', 'javascript', 'react', 'sql', 'machine learning', 'aws', 'docker']
                        data_skills = ['python', 'r', 'sql', 'machine learning', 'deep learning']
                        if any(skill in tech_skills for skill in skills):
                            predicted_field = 'Software Development'
                        elif any(skill in data_skills for skill in skills):
                            predicted_field = 'Data Science'

                    # Determine experience level
                    experience = resume_data.get('experience', [])
                    exp_level = 'Entry Level'
                    if experience and len(experience) > 2:
                        exp_level = 'Senior Level'
                    elif experience and len(experience) > 0:
                        exp_level = 'Mid Level'

                    # Calculate score
                    scorer = ResumeScorer()
                    score_details = scorer.score_resume(resume_data)
                    total_score = round(
                        score_details['experience_score'] * 0.35 +
                        score_details['skills_score'] * 0.30 +
                        score_details['education_score'] * 0.20 +
                        score_details['completeness_score'] * 0.15
                    )
                    
                    # Generate recommended skills based on actual skills
                    skills = resume_data.get('skills', [])
                    skill_recommendations = {
                        'python': ['django', 'flask', 'pandas', 'numpy', 'scikit-learn'],
                        'java': ['spring', 'hibernate', 'maven', 'junit'],
                        'javascript': ['react', 'angular', 'node.js', 'express'],
                        'web': ['html5', 'css3', 'javascript', 'react', 'node.js'],
                        'data': ['python', 'r', 'sql', 'tableau', 'power bi'],
                        'machine learning': ['tensorflow', 'pytorch', 'scikit-learn', 'keras'],
                        'cloud': ['aws', 'azure', 'docker', 'kubernetes'],
                        'database': ['sql', 'mongodb', 'postgresql', 'mysql'],
                        'mobile': ['react native', 'flutter', 'android', 'ios']
                    }
                    
                    recommended_skills = set()
                    for skill in skills:
                        skill_lower = skill.lower()
                        for category, related_skills in skill_recommendations.items():
                            if category in skill_lower or skill_lower in category:
                                recommended_skills.update(related_skills)
                    
                    # Remove skills that the candidate already has
                    recommended_skills = list(recommended_skills - set(skill.lower() for skill in skills))
                    
                    # Prepare data for database
                    user_data = {
                        'Name': resume_data.get('name', 'Unknown'),
                        'Email': resume_data.get('email', 'unknown@email.com'),
                        'Resume_Score': total_score,
                        'Total_Page': resume_data.get('no_of_pages', 0),
                        'Predicted_Field': predicted_field,
                        'User_Level': exp_level,
                        'Actual_Skills': ', '.join(skills),
                        'Recommended_Skills': ', '.join(recommended_skills[:5]),  # Top 5 recommendations
                        'Recommended_Courses': ', '.join(score_details.get('recommended_courses', [])),
                        'PDF_Name': pdf_file.name,
                        'Original_Resume_Path': resume_data.get('original_resume_path')
                    }
                    
                    # Save to database
                    insert_user_data(user_data)
                    
                    # Store in session state for display
                    st.session_state.resume_data = resume_data
                    st.session_state.score_details = score_details
                    
                    st.success("Resume processed and saved successfully!")
                    st.rerun()
                else:
                    st.error("Failed to extract data from resume")
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
                
                # Initialize database connection with timeout
                conn = sqlite3.connect('resume_data.db', timeout=20)
                cursor = conn.cursor()
                
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
                                PDF_Name TEXT,
                                Original_Resume_Path TEXT)''')
                conn.commit()
                
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
                    pdf_file.name,
                    resume_data.get('original_resume_path')
                )
                
                try:
                    cursor.execute('''INSERT INTO user_data 
                                    (ID, Name, Email, Resume_Score, Timestamp, Total_Page,
                                    Predicted_Field, User_Level, Actual_Skills,
                                    Recommended_Skills, Recommended_Courses, PDF_Name,
                                    Original_Resume_Path)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', insert_data)
                    conn.commit()
                except sqlite3.Error as e:
                    st.error(f"Database error: {str(e)}")
                
                finally:
                    cursor.close()
                    conn.close()

                ## Recommending courses
                st.markdown("""
                    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 10px;">
                        <h2 style="color: #2b5876; margin-bottom: 10px;">🎓 Learning Path Recommendations</h2>
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
                            margin: 0 0 10px 0;
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
                
                # Apply to companies
                st.markdown("""
                    <div style="
                        background: white;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                        margin: 20px 0;
                    ">
                        <h3 style="color: #2b5876; margin-bottom: 15px;">Apply to Companies</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                # Get list of admin users (companies)
                companies = login_ui.get_admin_users()
                
                if companies:
                    selected_companies = st.multiselect(
                        "Select companies to apply to:",
                        companies,
                        help="You can select multiple companies"
                    )
                    
                    if selected_companies:
                        if st.button("Submit Applications"):
                            success_count = 0
                            for company in selected_companies:
                                # Convert resume data to string for storage
                                resume_data_str = str(resume_data)
                                if login_ui.submit_application(
                                    st.session_state.username,
                                    company,
                                    resume_data_str,
                                    str(total_score)
                                ):
                                    success_count += 1
                            
                            if success_count > 0:
                                st.success(f"Successfully submitted applications to {success_count} companies!")
                            if success_count < len(selected_companies):
                                st.warning("Some applications failed to submit. Please try again.")
                else:
                    st.info("No companies are currently registered in the system.")
                
                # Show user's application history
                st.markdown("### Your Application History")
                applications = login_ui.get_user_applications(st.session_state.username, 'normal')
                if applications:
                    application_df = pd.DataFrame(
                        applications,
                        columns=['Company', 'Application Date', 'Status']
                    )
                    st.dataframe(application_df)
                else:
                    st.info("You haven't submitted any applications yet.")
            
if __name__ == "__main__":
    main()
