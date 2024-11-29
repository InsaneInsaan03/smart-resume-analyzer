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
        name_pattern = r'[A-Z][a-z]+ (?:[A-Z][a-z]+ )*[A-Z][a-z]+'
        matches = re.findall(name_pattern, self.text)
        return matches[0] if matches else ''
        
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
            'python', 'java', 'c++', 'ruby', 'matlab', 'javascript',
            'hadoop', 'spark', 'aws', 'docker', 'kubernetes',
            'php', 'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
            'html', 'css', 'react', 'angular', 'vue', 'node',
            'machine learning', 'deep learning', 'nlp', 'computer vision'
        ]
        
        found_skills = []
        text_lower = self.text.lower()
        for skill in skills_pattern:
            if skill in text_lower:
                found_skills.append(skill)
                
        return list(set(found_skills))
        
    def extract_education(self):
        education_pattern = [
            'bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'degree'
        ]
        
        education = []
        for line in self.text_lines:
            line_lower = line.lower()
            for pattern in education_pattern:
                if pattern in line_lower:
                    education.append(line.strip())
                    break
                    
        return list(set(education))
        
    def extract_experience(self):
        exp_pattern = [
            'experience', 'work history', 'employment', 'work experience'
        ]
        
        experience = []
        for line in self.text_lines:
            line_lower = line.lower()
            for pattern in exp_pattern:
                if pattern in line_lower:
                    experience.append(line.strip())
                    break
                    
        return list(set(experience))
        
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
