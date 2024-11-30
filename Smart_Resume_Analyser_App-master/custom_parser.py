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
        """
        Extract name from resume text using multiple methods:
        1. Look for common name patterns at the start of the resume
        2. Use NLTK's Named Entity Recognition
        3. Look for name after common resume headers
        """
        try:
            # First few lines are most likely to contain the name
            first_lines = '\n'.join(self.text_lines[:5])
            
            # Method 1: Common name pattern at the start
            # This pattern looks for 2-3 word combinations with proper capitalization
            name_pattern = r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}$'
            for line in self.text_lines[:5]:
                line = line.strip()
                if re.match(name_pattern, line):
                    return line
            
            # Method 2: NLTK's Named Entity Recognition
            try:
                tokens = nltk.word_tokenize(first_lines)
                pos_tags = nltk.pos_tag(tokens)
                chunks = nltk.ne_chunk(pos_tags)
                
                # Extract person names from chunks
                names = []
                for chunk in chunks:
                    if hasattr(chunk, 'label') and chunk.label() == 'PERSON':
                        name = ' '.join(c[0] for c in chunk.leaves())
                        names.append(name)
                
                if names:
                    # Return the longest name found (likely to be full name)
                    return max(names, key=len)
            except Exception:
                pass  # Continue with other methods if NLTK fails
            
            # Method 3: Look for name after common resume headers
            name_headers = ['name:', 'full name:', 'candidate name:']
            for line in self.text_lines[:10]:  # Check first 10 lines
                line_lower = line.lower()
                for header in name_headers:
                    if line_lower.startswith(header):
                        name = line[len(header):].strip()
                        if name:  # Verify it's not empty
                            return name
            
            # If no name found, look for first capitalized words
            for line in self.text_lines[:5]:
                words = line.split()
                if len(words) >= 2:  # At least first and last name
                    potential_name = ' '.join(w for w in words if w[0].isupper())
                    if potential_name and len(potential_name.split()) >= 2:
                        return potential_name
            
            return ''  # Return empty string if no name found
            
        except Exception as e:
            print(f"Error in name extraction: {str(e)}")
            return ''
        
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
