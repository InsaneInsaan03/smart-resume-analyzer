"""Main application file for the Smart Resume Analyzer."""

import streamlit as st
import pandas as pd
import time
from pathlib import Path
import os
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
from ui_utils import (
    setup_page_config, 
    get_custom_css, 
    show_header,
    get_table_download_link,
    create_score_bar
)
from streamlit_tags import st_tags
from PIL import Image
import sqlite3
import plotly.express as px
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io
import requests

# Initialize database on startup
init_db()

def pdf_reader(file):
    """Extract text from PDF file."""
    try:
        parser = CustomResumeParser(file)
        return parser.get_extracted_data()
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def show_pdf(file_path):
    try:
        st.write("### Resume Preview")
        st.write("📄 For security reasons, please use the download button to view the PDF.")
        
        # Create columns for better layout
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Read and provide download button
            with open(file_path, "rb") as pdf_file:
                PDFbyte = pdf_file.read()
                
            st.download_button(
                label="📥 Download Resume",
                data=PDFbyte,
                file_name=os.path.basename(file_path),
                mime='application/pdf',
                key='download-resume'
            )
        
        with col2:
            # Show file information
            file_size = os.path.getsize(file_path) / 1024  # Convert to KB
            st.info(f"""
            📋 File Information:
            • Name: {os.path.basename(file_path)}
            • Size: {file_size:.1f} KB
            """)
            
    except Exception as e:
        st.error(f"Error processing PDF: {e}")

def create_default_logo():
    # Create a simple colored rectangle as default logo
    img = Image.new('RGB', (250, 250), color='#2E86C1')
    return img

def ensure_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def fetch_yt_video(link):
    try:
        # video = pafy.new(link)
        # return video.title
        return "Video Title" # Placeholder since pafy is not being used
    except:
        return link

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def get_score_insight(score):
    if score >= 90:
        return "Outstanding resume! Your profile demonstrates exceptional qualifications and presentation."
    elif score >= 80:
        return "Great resume! You have a strong profile with well-rounded qualifications."
    elif score >= 70:
        return "Good resume! Consider adding more details to strengthen your profile further."
    elif score >= 60:
        return "Decent resume. There's room for improvement in several areas."
    else:
        return "Your resume needs significant improvement. Focus on adding more details and achievements."

def get_level_description(level):
    descriptions = {
        "Beginner": "Entry-level professional with foundational skills and knowledge.",
        "Intermediate": "Mid-level professional with solid experience and proven capabilities.",
        "Expert": "Senior professional with extensive experience and demonstrated leadership."
    }
    return descriptions.get(level, "")

def main():
    """Main function to run the Streamlit application."""
    # Setup page configuration
    setup_page_config()
    
    # Add custom CSS
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    # Show header with typing animation
    show_header()

    # Initialize session state
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = set()
    if 'current_file' not in st.session_state:
        st.session_state.current_file = None
    if 'resume_data' not in st.session_state:
        st.session_state.resume_data = None
    if 'resume_text' not in st.session_state:
        st.session_state.resume_text = None

    # Sidebar user selection
    st.sidebar.markdown('<h2 class="sub-header">👤 Choose User</h2>', unsafe_allow_html=True)
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Select User Type:", activities)

    if choice == 'Normal User':
        st.markdown("""
            <div class="info-card">
                <h4>📋 Upload Your Resume</h4>
                <p>Get smart recommendations based on your resume content.</p>
            </div>
        """, unsafe_allow_html=True)

        # Create upload directory if it doesn't exist
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)

        # File upload
        pdf_file = st.file_uploader("Choose your Resume (PDF)", type=["pdf"])
        
        if pdf_file is None:
            st.info("👋 Welcome! Please upload your resume in PDF format to begin the analysis.")
            st.markdown("""
                <div style='background-color: #f0f2f6; padding: 15px; border-radius: 5px; margin-top: 10px;'>
                    <h4>📝 Getting Started:</h4>
                    <ol>
                        <li>Prepare your resume in PDF format</li>
                        <li>Click the 'Browse files' button above</li>
                        <li>Select your resume file</li>
                    </ol>
                </div>
            """, unsafe_allow_html=True)
            return

        # Process new file
        if pdf_file is not None and pdf_file.name not in st.session_state.processed_files:
            try:
                # Save and process the file
                save_path = os.path.join(UPLOAD_DIR, pdf_file.name)
                with open(save_path, "wb") as f:
                    f.write(pdf_file.getbuffer())

                # Extract and parse resume data
                st.session_state.resume_text = pdf_reader(save_path)
                if not st.session_state.resume_text:
                    raise ValueError("Could not extract text from PDF")
                
                st.session_state.resume_data = CustomResumeParser(save_path).get_extracted_data()
                if not st.session_state.resume_data:
                    raise ValueError("Could not parse resume data")
                
                st.session_state.processed_files.add(pdf_file.name)
                
                # Show loading progress
                loading_placeholder = st.empty()
                progress_bar = st.progress(0)
                loading_time = random.uniform(5, 8)
                steps = int(loading_time * 2)
                
                for i in range(steps):
                    progress = min(100, int((i + 1) / steps * 100))
                    progress_bar.progress(progress / 100)
                    loading_placeholder.info(f"Analyzing your resume... {progress}%")
                    time.sleep(loading_time / steps)
                
                loading_placeholder.empty()
                progress_bar.empty()
                
                # Show success message
                success_placeholder = st.empty()
                success_placeholder.success("🎉 Analysis Complete! We've analyzed your resume and prepared personalized recommendations for you!")
                time.sleep(3)
                success_placeholder.empty()
                
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
            
            # Score breakdown in a compact card
            st.markdown(f"""
                <div style="
                    background: white;
                    padding: 1.2rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                    margin-bottom: 1.5rem;
                ">
                    <div style="
                        display: flex;
                        align-items: center;
                        margin-bottom: 1rem;
                    ">
                        <div style="
                            font-size: 2rem;
                            font-weight: bold;
                            color: #1e88e5;
                            margin-right: 1rem;
                        ">
                            {total_score}%
                        </div>
                        <div>
                            <div style="font-weight: 500; color: #666;">Overall Score</div>
                            <div style="color: #1e88e5; font-weight: 500;">
                                {score_details['experience_level']} Level
                            </div>
                        </div>
                    </div>
                    <div style="margin-bottom: 0.5rem;">Score Breakdown</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Score bars
            create_score_bar("Experience", score_details['experience_score'], "#43a047")
            create_score_bar("Skills", score_details['skills_score'], "#fb8c00")
            create_score_bar("Education", score_details['education_score'], "#8e24aa")
            create_score_bar("Completeness", score_details['completeness_score'], "#1e88e5")
            
            # Key insights in a compact format
            st.markdown(f"""
                <div style="
                    background: white;
                    padding: 1.2rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                    margin: 1.5rem 0;
                ">
                    <div style="font-weight: 500; margin-bottom: 1rem;">🎯 Key Insights</div>
                    <div style="
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 1rem;
                    ">
                        <div>
                            <div style="color: #666; font-size: 0.9rem;">Technical Skills</div>
                            <div style="font-weight: 500;">{len(score_details['technical_skills'])} found</div>
                        </div>
                        <div>
                            <div style="color: #666; font-size: 0.9rem;">Soft Skills</div>
                            <div style="font-weight: 500;">{len(score_details['soft_skills'])} found</div>
                        </div>
                        <div>
                            <div style="color: #666; font-size: 0.9rem;">Education</div>
                            <div style="font-weight: 500;">{len(resume_data['education'])} qualifications</div>
                        </div>
                        <div>
                            <div style="color: #666; font-size: 0.9rem;">Experience</div>
                            <div style="font-weight: 500;">{len(resume_data['experience'])} roles</div>
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
                            <div style="
                                padding: 1rem;
                                margin: 0.8rem 0;
                                background: linear-gradient(135deg, #f6f9fc 0%, #f1f4f9 100%);
                                border-radius: 8px;
                                color: #2b5876;
                                text-decoration: none;
                                transition: all 0.3s ease;
                                border-left: 4px solid transparent;
                            ">
                                <span style="
                                    color: #2b5876;
                                    margin-right: 1rem;
                                    font-size: 1.1rem;
                                ">🔗</span>
                                <a href="{course_link}" 
                                   target="_blank" 
                                   style="
                                    color: #2b5876;
                                    text-decoration: none;
                                    font-weight: 500;
                                    flex-grow: 1;
                                    &:hover {{
                                        text-decoration: underline;
                                    }}
                                ">{course_name}</a>
                            </div>
                        ''', unsafe_allow_html=True)
                else:
                    st.info("Add skills to get personalized course recommendations")
        else:
            st.error('Something went wrong..')
    else:
        ## Admin Side
        st.success('Welcome to Admin Side')
        # st.sidebar.subheader('**ID / Password Required!**')

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
