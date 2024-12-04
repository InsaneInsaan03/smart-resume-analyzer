import re
import nltk
from nltk.corpus import stopwords
from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io

class CustomResumeParser:
    def __init__(self, resume_path):
        self.resume_path = resume_path
        self.text = ''
        
        # Get number of pages
        self.no_of_pages = 0
        with open(resume_path, 'rb') as file:
            for page in PDFPage.get_pages(file):
                self.no_of_pages += 1
        
        # Extract text from PDF
        self.text = self.extract_text_from_pdf()
        
        # Basic text processing
        self.text_lines = [line.strip() for line in self.text.split('\n') if line.strip()]
        self.tokens = [word.strip() for word in self.text.split() if word.strip()]
        
    def extract_text_from_pdf(self):
        with open(self.resume_path, 'rb') as fh:
            rsrcmgr = PDFResourceManager()
            sio = io.StringIO()
            device = TextConverter(rsrcmgr, sio, codec='utf-8', laparams=LAParams())
            interpreter = PDFPageInterpreter(rsrcmgr, device)

            for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
                interpreter.process_page(page)

            text = sio.getvalue()
            device.close()
            sio.close()
            return text
            
    def extract_name(self):
        """Extract name from resume text"""
        try:
            # First few lines are most likely to contain the name
            first_lines = '\n'.join(self.text_lines[:10])
            
            # List of job titles to exclude
            job_titles = ['data scientist', 'software engineer', 'developer', 'engineer', 'analyst',
                         'manager', 'consultant', 'programmer', 'architect', 'designer',
                         'lead', 'senior', 'junior', 'full stack', 'backend', 'frontend']
            
            # Method 1: NLTK's Named Entity Recognition (most reliable)
            try:
                tokens = nltk.word_tokenize(first_lines)
                pos_tags = nltk.pos_tag(tokens)
                chunks = nltk.ne_chunk(pos_tags)
                
                # Extract person names from chunks
                names = []
                for chunk in chunks:
                    if hasattr(chunk, 'label') and chunk.label() == 'PERSON':
                        name = ' '.join(c[0] for c in chunk.leaves())
                        # Verify it's not a job title
                        if len(name.split()) >= 2 and not any(title in name.lower() for title in job_titles):
                            names.append(name)
                
                if names:
                    # Return the first valid name found
                    return names[0]
            except Exception:
                pass
            
            # Method 2: Look for name after common resume headers
            name_headers = ['name:', 'full name:', 'candidate name:', 'applicant:']
            for line in self.text_lines[:10]:
                line_lower = line.lower()
                for header in name_headers:
                    if line_lower.startswith(header):
                        name = line[len(header):].strip()
                        # Verify it's not a job title
                        if len(name.split()) >= 2 and not any(title in name.lower() for title in job_titles):
                            return name
            
            # Method 3: Look for properly capitalized name pattern at the start
            name_pattern = r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}$'
            for line in self.text_lines[:5]:
                line = line.strip()
                if re.match(name_pattern, line):
                    # Verify it's not a job title
                    if not any(title in line.lower() for title in job_titles):
                        return line
            
            # If no name found with above methods, return Unknown
            return 'Unknown'
            
        except Exception as e:
            print(f"Error in name extraction: {str(e)}")
            return 'Unknown'
        
    def extract_email(self):
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, self.text)
        return matches[0] if matches else ''
        
    def extract_mobile_number(self):
        phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        matches = re.findall(phone_pattern, self.text)
        return matches[0] if matches else ''
    
    def extract_skills(self):
        skills_pattern = [
            # Programming Languages
            'python', 'java', 'c++', 'ruby', 'matlab', 'javascript', 'php', 'typescript',
            'scala', 'kotlin', 'swift', 'r', 'golang', 'rust', 'perl',
            
            # Web Technologies
            'html', 'css', 'react', 'angular', 'vue', 'node', 'express', 'django',
            'flask', 'spring', 'asp.net', 'jquery', 'bootstrap', 'sass', 'less',
            
            # Databases
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'cassandra',
            'elasticsearch', 'dynamodb', 'firebase',
            
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'terraform',
            'ansible', 'circleci', 'travis', 'nginx', 'apache',
            
            # Big Data & ML
            'hadoop', 'spark', 'kafka', 'airflow', 'machine learning', 'deep learning',
            'nlp', 'computer vision', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas',
            'numpy', 'scipy', 'matplotlib', 'seaborn',
            
            # Mobile Development
            'android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic',
            
            # Other Tools & Technologies
            'jira', 'confluence', 'slack', 'trello', 'postman', 'swagger',
            'selenium', 'junit', 'jest', 'mocha', 'cypress'
        ]
        
        found_skills = []
        text_lower = self.text.lower()
        
        # Look for exact matches
        for skill in skills_pattern:
            if skill in text_lower:
                found_skills.append(skill)
        
        # Look for variations with dots (e.g., asp.net)
        text_no_dots = text_lower.replace('.', '')
        for skill in skills_pattern:
            skill_no_dots = skill.replace('.', '')
            if skill_no_dots in text_no_dots and skill not in found_skills:
                found_skills.append(skill)
        
        # Look for skills in education section (degrees, certifications)
        education_skills = [
            'computer science', 'software engineering', 'information technology',
            'data science', 'artificial intelligence', 'web development',
            'cloud computing', 'cybersecurity', 'network engineering'
        ]
        
        for skill in education_skills:
            if skill in text_lower:
                found_skills.append(skill)
                
        return list(set(found_skills))
        
    def extract_education(self):
        """
        Extract education details using multiple approaches
        """
        education = []
        
        # Common education keywords
        education_keywords = [
            'education', 'qualification', 'academic', 'degree',
            'bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'b.e', 'm.e',
            'b.sc', 'm.sc', 'b.a', 'm.a', 'diploma', 'university', 'college',
            'institute', 'school'
        ]
        
        # Common degree patterns
        degree_patterns = [
            r'(?i)b\.?tech|bachelor of technology',
            r'(?i)m\.?tech|master of technology',
            r'(?i)b\.?e|bachelor of engineering',
            r'(?i)m\.?e|master of engineering',
            r'(?i)b\.?sc|bachelor of science',
            r'(?i)m\.?sc|master of science',
            r'(?i)b\.?a|bachelor of arts',
            r'(?i)m\.?a|master of arts',
            r'(?i)phd|ph\.?d|doctor of philosophy',
            r'(?i)diploma in \w+'
        ]
        
        # Find education section
        education_section = []
        in_education_section = False
        
        for line in self.text_lines:
            line_lower = line.lower()
            
            # Check if we're entering education section
            if any(keyword in line_lower for keyword in education_keywords):
                in_education_section = True
                continue
            
            # Check if we're leaving education section
            if in_education_section and line.strip() and not any(keyword in line_lower for keyword in education_keywords):
                if any(re.search(pattern, line) for pattern in degree_patterns):
                    education_section.append(line.strip())
                elif any(word.isupper() for word in line.split()):  # Likely an institution name
                    education_section.append(line.strip())
            
            # Exit education section if we hit another section
            if in_education_section and any(keyword in line_lower for keyword in ['experience', 'skills', 'projects']):
                in_education_section = False
        
        # Extract degrees and institutions using patterns
        for line in self.text_lines:
            # Look for degree patterns
            for pattern in degree_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match and line.strip() not in education:
                    education.append(line.strip())
        
        # Add education section contents
        education.extend([item for item in education_section if item not in education])
        
        return list(set(education))

    def extract_experience(self):
        """
        Extract work experience details
        """
        experience = []
        
        # Experience section keywords
        exp_keywords = [
            'experience', 'employment', 'work history', 'professional background',
            'career history', 'work experience', 'professional experience'
        ]
        
        # Date patterns
        date_pattern = r'(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s*\d{4}\s*-\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december|present)\s*\d{0,4}'
        
        # Find experience section
        in_experience_section = False
        current_experience = []
        
        for line in self.text_lines:
            line_lower = line.lower()
            
            # Check if we're entering experience section
            if any(keyword in line_lower for keyword in exp_keywords):
                in_experience_section = True
                if line.strip() and not any(keyword == line_lower for keyword in exp_keywords):
                    current_experience.append(line.strip())
                continue
            
            # Collect experience details
            if in_experience_section:
                if line.strip():
                    # Check for date patterns
                    if re.search(date_pattern, line):
                        if current_experience:
                            experience.append(' | '.join(current_experience))
                            current_experience = []
                        current_experience.append(line.strip())
                    # Check for company names (usually in caps)
                    elif any(word.isupper() for word in line.split()):
                        current_experience.append(line.strip())
                    # Check for position titles (usually starts with capital)
                    elif line[0].isupper():
                        current_experience.append(line.strip())
                    # Add bullet points
                    elif line.strip().startswith(('•', '-', '*')):
                        current_experience.append(line.strip())
            
            # Exit experience section if we hit another section
            if in_experience_section and any(keyword in line_lower for keyword in ['education', 'skills', 'projects', 'achievements']):
                in_experience_section = False
                if current_experience:
                    experience.append(' | '.join(current_experience))
        
        # Add any remaining experience
        if current_experience:
            experience.append(' | '.join(current_experience))
        
        return experience

    def get_extracted_data(self):
        return {
            'name': self.extract_name(),
            'email': self.extract_email(),
            'mobile_number': self.extract_mobile_number(),
            'skills': self.extract_skills(),
            'education': self.extract_education(),
            'experience': self.extract_experience(),
            'no_of_pages': self.no_of_pages
        }
