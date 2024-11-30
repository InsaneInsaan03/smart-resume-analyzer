class ResumeScorer:
    def __init__(self):
        # Define skill categories
        self.technical_skills = {
            'programming': ['python', 'java', 'javascript', 'c++', 'ruby', 'php', 'swift', 'kotlin', 'golang'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'elasticsearch'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins'],
            'ai_ml': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn', 'nlp']
        }
        
        self.soft_skills = [
            'communication', 'leadership', 'teamwork', 'problem solving', 'critical thinking',
            'time management', 'adaptability', 'creativity', 'project management', 'analytical',
            'collaboration', 'presentation', 'negotiation', 'organization', 'decision making'
        ]
        
        self.domain_skills = {
            'finance': ['financial analysis', 'trading', 'investment', 'risk management', 'portfolio management'],
            'marketing': ['digital marketing', 'seo', 'social media', 'content marketing', 'brand management'],
            'healthcare': ['clinical', 'patient care', 'medical records', 'healthcare management'],
            'consulting': ['business strategy', 'management consulting', 'process improvement'],
            'sales': ['sales management', 'business development', 'account management', 'crm']
        }

    def score_resume(self, resume_data):
        """Score a resume based on multiple criteria."""
        scores = {
            'experience_score': self._calculate_experience_score(resume_data),
            'skills_score': self._calculate_skills_score(resume_data),
            'education_score': self._calculate_education_score(resume_data),
            'completeness_score': self._calculate_completeness_score(resume_data)
        }
        
        # Calculate total score with weights
        weights = {
            'experience_score': 0.35,
            'skills_score': 0.30,
            'education_score': 0.20,
            'completeness_score': 0.15
        }
        
        total_score = sum(scores[key] * weights[key] for key in weights)
        scores['total_score'] = round(total_score)
        
        # Determine experience level
        scores['experience_level'] = self._determine_experience_level(total_score, resume_data)
        
        # Add skill breakdown
        skill_breakdown = self._get_skill_breakdown(resume_data)
        scores.update(skill_breakdown)
        
        return scores

    def _calculate_experience_score(self, resume_data):
        """Calculate experience score based on work history."""
        experience_list = resume_data.get('experience', [])
        if not experience_list:
            return 0
        
        total_score = 0
        for exp in experience_list:
            # Points for having experience entry
            total_score += 20
            
            # Additional points for detailed description
            if len(exp.split()) > 10:  # If description has more than 10 words
                total_score += 10
                
            # Points for leadership/senior terms
            leadership_terms = ['lead', 'senior', 'manager', 'supervisor', 'head', 'chief', 'director']
            if any(term in exp.lower() for term in leadership_terms):
                total_score += 15
        
        return min(100, total_score)

    def _calculate_skills_score(self, resume_data):
        """Calculate skills score based on skill categories."""
        skills = set(skill.lower() for skill in resume_data.get('skills', []))
        if not skills:
            return 0
        
        # Base score for having any skills
        base_score = min(len(skills) * 10, 40)  # Up to 40 points just for having skills
        
        # Calculate category scores
        tech_score = self._calculate_category_score(skills, self.technical_skills)
        soft_score = self._calculate_soft_skills_score(skills)
        domain_score = self._calculate_category_score(skills, self.domain_skills)
        
        # Weight the scores
        weighted_score = (tech_score * 0.3) + (soft_score * 0.15) + (domain_score * 0.15) + base_score
        return round(min(weighted_score, 100))

    def _calculate_category_score(self, skills, category_dict):
        """Calculate score for a specific skill category."""
        total_matches = 0
        for category, category_skills in category_dict.items():
            # Count partial matches as well
            for skill in category_skills:
                if any(s in skills for s in [skill, skill.replace(' ', ''), skill.replace('.', '')]):
                    total_matches += 1
        
        # More lenient scoring - expect fewer matches for full score
        max_expected = 5  # Expected number of skills per category
        score = min(100, (total_matches / max_expected) * 100)
        return score

    def _calculate_soft_skills_score(self, skills):
        """Calculate soft skills score."""
        matches = 0
        for skill in self.soft_skills:
            # Check for variations of the skill
            variations = [
                skill,
                skill.replace(' ', ''),
                skill.replace('-', ''),
                skill.replace(' ', '-')
            ]
            if any(var in ' '.join(skills).lower() for var in variations):
                matches += 1
        
        # More lenient scoring for soft skills
        max_expected = 3  # Expected number of soft skills
        return min(100, (matches / max_expected) * 100)

    def _calculate_education_score(self, resume_data):
        """Calculate education score."""
        education = resume_data.get('education', [])
        if not education:
            return 0
        
        score = 40  # Base score for having any education
        
        degree_weights = {
            'phd': 100,
            'doctorate': 100,
            'master': 90,
            'mba': 90,
            'bachelor': 80,
            'btech': 80,
            'bsc': 80,
            'associate': 70,
            'diploma': 60,
            'certification': 50
        }
        
        for edu in education:
            edu_lower = edu.lower()
            
            # Check for degree level
            for degree, weight in degree_weights.items():
                if degree in edu_lower:
                    score = max(score, weight)
                    break
            
            # Additional points for prestigious terms
            prestigious_terms = [
                'distinction', 'honors', 'first class', 
                'magna cum laude', 'summa cum laude',
                'high distinction', 'merit', 'dean\'s list'
            ]
            if any(term in edu_lower for term in prestigious_terms):
                score = min(score + 10, 100)
            
            # Points for GPA or percentage if mentioned
            if any(term in edu_lower for term in ['gpa', 'cgpa', '%', 'percent']):
                score = min(score + 5, 100)
        
        return score

    def _calculate_completeness_score(self, resume_data):
        """Calculate completeness score based on resume sections."""
        sections = {
            'name': 10,
            'email': 10,
            'mobile_number': 10,
            'skills': 20,
            'experience': 25,
            'education': 25
        }
        
        score = 0
        for section, weight in sections.items():
            if resume_data.get(section):
                score += weight
                
                # Bonus points for detailed sections
                if section in ['skills', 'experience', 'education']:
                    content = resume_data.get(section, [])
                    if isinstance(content, list) and len(content) >= 3:
                        score = min(score + 5, 100)
        
        return score

    def _determine_experience_level(self, total_score, resume_data):
        """Determine experience level based on scores and experience."""
        experience_count = len(resume_data.get('experience', []))
        
        if total_score >= 85 and experience_count >= 3:
            return "Expert"
        elif total_score >= 70 and experience_count >= 2:
            return "Intermediate"
        else:
            return "Beginner"

    def _get_skill_breakdown(self, resume_data):
        """Get detailed breakdown of skills by category."""
        skills = set(skill.lower() for skill in resume_data.get('skills', []))
        
        breakdown = {
            'technical_skills': {},
            'soft_skills': [],
            'domain_skills': {}
        }
        
        # Technical skills breakdown
        for category, skills_list in self.technical_skills.items():
            matched = [skill for skill in skills_list if any(s in skills for s in [skill, skill.replace(' ', '')])]
            if matched:
                breakdown['technical_skills'][category] = matched
        
        # Soft skills
        breakdown['soft_skills'] = [skill for skill in self.soft_skills 
                                  if any(s in skills for s in [skill, skill.replace(' ', '')])]
        
        # Domain skills
        for domain, skills_list in self.domain_skills.items():
            matched = [skill for skill in skills_list if any(s in skills for s in [skill, skill.replace(' ', '')])]
            if matched:
                breakdown['domain_skills'][domain] = matched
        
        return breakdown
