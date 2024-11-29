import streamlit as st
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')
from nltk.tokenize import word_tokenize
import pandas as pd
import base64, random
import time, datetime
from custom_parser import CustomResumeParser
from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io, random
from streamlit_tags import st_tags
from PIL import Image
import sqlite3
import os
import plotly.express as px
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos

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

# Create a database connection
def init_db():
    db_path = 'resume_data.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    
    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS user_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  email TEXT,
                  res_score TEXT,
                  timestamp TEXT,
                  no_of_pages TEXT,
                  reco_field TEXT,
                  cand_level TEXT,
                  skills TEXT,
                  recommended_skills TEXT,
                  courses TEXT)''')
    conn.commit()
    return conn, c

# Initialize database connection
connection, cursor = init_db()

def insert_data(name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills, courses):
    DB_table_name = 'user_data'
    insert_sql = f"INSERT INTO {DB_table_name} (name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills, courses) VALUES (?,?,?,?,?,?,?,?,?,?)"
    rec_values = (name, email, str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, skills, recommended_skills, courses)
    cursor.execute(insert_sql, rec_values)
    connection.commit()


st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon="📄",
)


def create_default_logo():
    # Create a simple colored rectangle as default logo
    img = Image.new('RGB', (250, 250), color='#2E86C1')
    return img

def ensure_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh,
                                    caching=True,
                                    check_extractable=True):
            page_interpreter.process_page(page)
            print(page)
        text = fake_file_handle.getvalue()

    # close open handles
    converter.close()
    fake_file_handle.close()
    return text

def get_table_download_link(df, filename, text):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def run():
    # Ensure required directories exist
    ensure_dir('./Uploaded_Resumes')
    
    # Custom CSS styling
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #2e86c1;
            text-align: center;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 2rem;
            background: #f8f9fa;
        }
        .sub-header {
            font-size: 1.5rem;
            color: #34495e;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Main header with styling
    st.markdown('<h1 class="main-header">📄 Smart Resume Analyser</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.markdown('<h2 class="sub-header">👤 Choose User</h2>', unsafe_allow_html=True)
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Select User Type:", activities)

    if choice == 'Normal User':
        st.markdown("""
            <div style="background-color: #f0f8ff; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h4 style="color: #2e86c1; margin-bottom: 10px;">📋 Upload Your Resume</h4>
                <p style="color: #34495e;">Get smart recommendations based on your resume content.</p>
            </div>
        """, unsafe_allow_html=True)

        pdf_file = st.file_uploader("Choose your Resume (PDF)", type=["pdf"])
        if pdf_file is not None:
            try:
                save_image_path = os.path.join('./Uploaded_Resumes', pdf_file.name)
                with open(save_image_path, "wb") as f:
                    f.write(pdf_file.getbuffer())
                
                show_pdf(save_image_path)
                resume_data = CustomResumeParser(save_image_path).get_extracted_data()
                
                if resume_data:
                    ## Get the whole resume data
                    resume_text = pdf_reader(save_image_path)

                    st.markdown('<h2 class="sub-header">📊 Resume Analysis</h2>', unsafe_allow_html=True)
                    st.success(f"Hello {resume_data['name']}")
                    
                    # Display basic info in a modern card layout
                    st.markdown("""
                        <div style="background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <h3 style="color: #2e86c1; margin-bottom: 15px;">Basic Information</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"📧 Email: {resume_data['email']}")
                        st.info(f"📱 Contact: {resume_data['mobile_number']}")
                    with col2:
                        st.info(f"📄 Pages: {resume_data['no_of_pages']}")
                        
                    cand_level = ''
                    if resume_data['no_of_pages'] == 1:
                        cand_level = "Fresher"
                        st.markdown('''<h4 style='text-align: left; color: #d73b5c;'>You are looking Fresher.</h4>''',
                                    unsafe_allow_html=True)
                    elif resume_data['no_of_pages'] == 2:
                        cand_level = "Intermediate"
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''',
                                    unsafe_allow_html=True)
                    elif resume_data['no_of_pages'] >= 3:
                        cand_level = "Experienced"
                        st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''',
                                    unsafe_allow_html=True)

                    st.subheader("**Skills Recommendation💡**")
                    ## Skill shows
                    keywords = st_tags(label='### Skills that you have',
                                       text='See our skills recommendation',
                                       value=resume_data['skills'], key='1')

                    ##  recommendation
                    ds_keyword = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep Learning', 'flask',
                                  'streamlit']
                    web_keyword = ['react', 'django', 'node jS', 'react js', 'php', 'laravel', 'magento', 'wordpress',
                                   'javascript', 'angular js', 'c#', 'flask']
                    android_keyword = ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy']
                    ios_keyword = ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode']
                    uiux_keyword = ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes',
                                    'storyframes', 'adobe photoshop', 'photoshop', 'editing', 'adobe illustrator',
                                    'illustrator', 'adobe after effects', 'after effects', 'adobe premier pro',
                                    'premier pro', 'adobe indesign', 'indesign', 'wireframe', 'solid', 'grasp',
                                    'user research', 'user experience']

                    recommended_skills = []
                    reco_field = ''
                    rec_course = ''
                    ## Courses recommendation
                    for i in resume_data['skills']:
                        ## Data science recommendation
                        if i.lower() in ds_keyword:
                            print(i.lower())
                            reco_field = 'Data Science'
                            st.success("** Our analysis says you are looking for Data Science Jobs.**")
                            recommended_skills = ['Data Visualization', 'Predictive Analysis', 'Statistical Modeling',
                                                  'Data Mining', 'Clustering & Classification', 'Data Analytics',
                                                  'Quantitative Analysis', 'Web Scraping', 'ML Algorithms', 'Keras',
                                                  'Pytorch', 'Probability', 'Scikit-learn', 'Tensorflow', "Flask",
                                                  'Streamlit']
                            recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                           text='Recommended skills generated from System',
                                                           value=recommended_skills, key='2')
                            st.markdown(
                                '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                                unsafe_allow_html=True)
                            rec_course = course_recommender(ds_course)
                            break

                        ## Web development recommendation
                        elif i.lower() in web_keyword:
                            print(i.lower())
                            reco_field = 'Web Development'
                            st.success("** Our analysis says you are looking for Web Development Jobs **")
                            recommended_skills = ['React', 'Django', 'Node JS', 'React JS', 'php', 'laravel', 'Magento',
                                                  'wordpress', 'Javascript', 'Angular JS', 'c#', 'Flask', 'SDK']
                            recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                           text='Recommended skills generated from System',
                                                           value=recommended_skills, key='3')
                            st.markdown(
                                '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                                unsafe_allow_html=True)
                            rec_course = course_recommender(web_course)
                            break

                        ## Android App Development
                        elif i.lower() in android_keyword:
                            print(i.lower())
                            reco_field = 'Android Development'
                            st.success("** Our analysis says you are looking for Android App Development Jobs **")
                            recommended_skills = ['Android', 'Android development', 'Flutter', 'Kotlin', 'XML', 'Java',
                                                  'Kivy', 'GIT', 'SDK', 'SQLite']
                            recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                           text='Recommended skills generated from System',
                                                           value=recommended_skills, key='4')
                            st.markdown(
                                '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                                unsafe_allow_html=True)
                            rec_course = course_recommender(android_course)
                            break

                        ## IOS App Development
                        elif i.lower() in ios_keyword:
                            print(i.lower())
                            reco_field = 'IOS Development'
                            st.success("** Our analysis says you are looking for IOS App Development Jobs **")
                            recommended_skills = ['IOS', 'IOS Development', 'Swift', 'Cocoa', 'Cocoa Touch', 'Xcode',
                                                  'Objective-C', 'SQLite', 'Plist', 'StoreKit', "UI-Kit", 'AV Foundation',
                                                  'Auto-Layout']
                            recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                           text='Recommended skills generated from System',
                                                           value=recommended_skills, key='5')
                            st.markdown(
                                '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                                unsafe_allow_html=True)
                            rec_course = course_recommender(ios_course)
                            break

                        ## Ui-UX Recommendation
                        elif i.lower() in uiux_keyword:
                            print(i.lower())
                            reco_field = 'UI-UX Development'
                            st.success("** Our analysis says you are looking for UI-UX Development Jobs **")
                            recommended_skills = ['UI', 'User Experience', 'Adobe XD', 'Figma', 'Zeplin', 'Balsamiq',
                                                  'Prototyping', 'Wireframes', 'Storyframes', 'Adobe Photoshop', 'Editing',
                                                  'Illustrator', 'After Effects', 'Premier Pro', 'Indesign', 'Wireframe',
                                                  'Solid', 'Grasp', 'User Research']
                            recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                           text='Recommended skills generated from System',
                                                           value=recommended_skills, key='6')
                            st.markdown(
                                '''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',
                                unsafe_allow_html=True)
                            rec_course = course_recommender(uiux_course)
                            break

                    #
                    ## Insert into table
                    ts = time.time()
                    cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    timestamp = str(cur_date + '_' + cur_time)

                    ### Resume writing recommendation
                    st.subheader("**Resume Tips & Ideas💡**")
                    resume_score = 0
                    if 'Objective' in resume_text:
                        resume_score = resume_score + 20
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Objective</h4>''',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add your career objective, it will give your career intension to the Recruiters.</h4>''',
                            unsafe_allow_html=True)

                    if 'Declaration' in resume_text:
                        resume_score = resume_score + 20
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Delcaration✍/h4>''',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Declaration✍. It will give the assurance that everything written on your resume is true and fully acknowledged by you</h4>''',
                            unsafe_allow_html=True)

                    if 'Hobbies' or 'Interests' in resume_text:
                        resume_score = resume_score + 20
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Hobbies⚽</h4>''',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Hobbies⚽. It will show your persnality to the Recruiters and give the assurance that you are fit for this role or not.</h4>''',
                            unsafe_allow_html=True)

                    if 'Achievements' in resume_text:
                        resume_score = resume_score + 20
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements🏅 </h4>''',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Achievements🏅. It will show that you are capable for the required position.</h4>''',
                            unsafe_allow_html=True)

                    if 'Projects' in resume_text:
                        resume_score = resume_score + 20
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects👨‍💻 </h4>''',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Projects👨‍💻. It will show that you have done work related the required position or not.</h4>''',
                            unsafe_allow_html=True)

                    st.subheader("**Resume Score📝**")
                    st.markdown(
                        """
                        <style>
                            .stProgress > div > div > div > div {
                                background-color: #d73b5c;
                            }
                        </style>""",
                        unsafe_allow_html=True,
                    )
                    my_bar = st.progress(0)
                    score = 0
                    for percent_complete in range(resume_score):
                        score += 1
                        time.sleep(0.1)
                        my_bar.progress(percent_complete + 1)
                    st.success('** Your Resume Writing Score: ' + str(score) + '**')
                    st.warning(
                        "** Note: This score is calculated based on the content that you have added in your Resume. **")
                    st.balloons()

                    insert_data(resume_data['name'], resume_data['email'], str(resume_score), timestamp,
                                str(resume_data['no_of_pages']), reco_field, cand_level, str(resume_data['skills']),
                                str(recommended_skills), str(rec_course))

                    ## Resume writing video
                    st.header("**Resume Writing Tips💡**")
                    st.markdown("""
                    Here are some helpful tips for writing a great resume:
                    1. Keep it concise and well-organized
                    2. Highlight your relevant skills and achievements
                    3. Use action verbs and quantify results
                    4. Proofread carefully
                    5. Customize for each job application
                    
                    For more detailed tips, check out these resources:
                    * [Resume Writing Guide](https://www.indeed.com/career-advice/resumes-cover-letters/how-to-write-a-resume)
                    * [Resume Templates](https://www.canva.com/resumes/templates/)
                    """)

                    connection.commit()
                else:
                    st.error('Something went wrong..')
            except Exception as e:
                st.error(f"An error occurred: {e}")
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
                cursor.execute('''SELECT*FROM user_data''')
                data = cursor.fetchall()
                st.header("**User's👨‍💻 Data**")
                df = pd.DataFrame(data, columns=['ID', 'Name', 'Email', 'Resume Score', 'Timestamp', 'Total Page',
                                                 'Predicted Field', 'User Level', 'Actual Skills', 'Recommended Skills',
                                                 'Recommended Course'])
                st.dataframe(df)
                st.markdown(get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)
                
                ## Admin Side Data
                query = 'select * from user_data;'
                plot_data = pd.read_sql(query, connection)

                ## Pie chart for predicted field recommendations
                labels = plot_data['reco_field'].unique()
                values = plot_data['reco_field'].value_counts()
                st.subheader("📈 **Pie-Chart for Predicted Field Recommendations**")
                
                # Create a DataFrame for the pie chart
                pie_chart_data = pd.DataFrame({
                    'Field': labels,
                    'Count': values
                })
                
                fig = px.pie(pie_chart_data, values='Count', names='Field', 
                           title='Predicted Field according to the Skills')
                st.plotly_chart(fig)

                ### Pie chart for User's👨‍💻 Experienced Level
                labels = plot_data['cand_level'].unique()
                values = plot_data['cand_level'].value_counts()
                st.subheader("📈 **Pie-Chart for User's👨‍💻 Experience Level**")
                
                # Create a DataFrame for the pie chart
                pie_chart_data = pd.DataFrame({
                    'Level': labels,
                    'Count': values
                })
                
                fig = px.pie(pie_chart_data, values='Count', names='Level', 
                           title="User's Experience Level")
                st.plotly_chart(fig)


            else:
                st.error("Wrong ID & Password Provided")


run()
