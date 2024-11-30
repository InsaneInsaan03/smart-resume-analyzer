from fpdf import FPDF
import markdown
import os

class PDF(FPDF):
    def header(self):
        # Logo
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Smart Resume Analyzer', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf():
    # Create PDF object
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Set styles
    pdf.set_font("Arial", "B", size=24)
    pdf.cell(0, 20, "Smart Resume Analyzer", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    
    # Content sections
    sections = [
        ("Overview", """
The Smart Resume Analyzer is a comprehensive application that combines Streamlit's web interface 
with a native Android mobile app to provide intelligent resume analysis and career guidance.
        """),
        
        ("Key Features", """
1. Resume Analysis
   - PDF parsing and text extraction
   - Automatic information detection
   - Skills and expertise identification
   - Experience level assessment

2. Career Guidance
   - Field-specific recommendations
   - Personalized skill suggestions
   - Course recommendations
   - Career path guidance

3. Technical Capabilities
   - Mobile-first design
   - Secure file handling
   - Real-time analysis
   - Database integration
        """),
        
        ("How It Works", """
1. Resume Upload
   - Select PDF resume through mobile app
   - Secure file storage
   - Immediate preview
   - Text content extraction

2. Analysis Process
   - Parse resume content
   - Identify key information
   - Analyze skills and experience
   - Determine professional field

3. Recommendations
   - Suggest relevant skills
   - Recommend courses
   - Provide career guidance
   - Offer improvement tips
        """),
        
        ("Technical Architecture", """
Web Application (Streamlit):
- Built with Python
- PDF processing
- Text analysis
- Database management
- Interactive UI

Mobile Application (Android):
- Native Android with WebView
- File upload support
- Seamless navigation
- Offline capabilities
- Minimum SDK: Android 8.0
        """),
        
        ("Security Features", """
1. Secure file handling
2. Data encryption
3. Private storage
4. Access control
5. User authentication
        """),
        
        ("Benefits", """
For Job Seekers:
- Professional guidance
- Skill gap analysis
- Career path suggestions
- Learning resources

For Recruiters:
- Standardized analysis
- Skill verification
- Candidate assessment
- Efficient screening
        """),
        
        ("Future Enhancements", """
1. Enhanced Analytics
   - Deep learning integration
   - Pattern recognition
   - Trend analysis

2. Additional Features
   - Resume templates
   - Interview preparation
   - Job matching
   - Career tracking

3. Platform Expansion
   - iOS support
   - Desktop application
   - Cloud synchronization
        """)
    ]
    
    # Add content
    for title, content in sections:
        pdf.set_font("Arial", "B", size=16)
        pdf.cell(0, 10, title, ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, content.strip())
        pdf.ln(10)
    
    # Save the PDF
    pdf.output("Smart_Resume_Analyzer_Documentation.pdf")

if __name__ == "__main__":
    create_pdf()
