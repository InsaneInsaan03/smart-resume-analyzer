"""Course recommendation module for the resume analyzer."""

class CourseRecommender:
    def __init__(self):
        # Define course categories and their corresponding courses
        self.courses = {
            'programming': [
                ('Python for Everybody - Coursera', 'https://www.coursera.org/specializations/python'),
                ('Java Programming Masterclass - Udemy', 'https://www.udemy.com/course/java-the-complete-java-developer-course/'),
                ('The Web Developer Bootcamp - Udemy', 'https://www.udemy.com/course/the-web-developer-bootcamp/'),
                ('Complete C++ Developer Course - Udemy', 'https://www.udemy.com/course/complete-cpp-developer-course/')
            ],
            'web_development': [
                ('The Complete 2024 Web Development Bootcamp', 'https://www.udemy.com/course/the-complete-web-development-bootcamp/'),
                ('React - The Complete Guide', 'https://www.udemy.com/course/react-the-complete-guide-incl-redux/'),
                ('Angular - The Complete Guide', 'https://www.udemy.com/course/the-complete-guide-to-angular-2/'),
                ('Node.js Developer Course', 'https://www.udemy.com/course/the-complete-nodejs-developer-course-2/')
            ],
            'data_science': [
                ('Data Science Specialization - Coursera', 'https://www.coursera.org/specializations/jhu-data-science'),
                ('Machine Learning - Stanford Online', 'https://www.coursera.org/learn/machine-learning'),
                ('Deep Learning Specialization', 'https://www.coursera.org/specializations/deep-learning'),
                ('TensorFlow Developer Certificate', 'https://www.coursera.org/professional-certificates/tensorflow-in-practice')
            ],
            'cloud': [
                ('AWS Certified Solutions Architect', 'https://www.udemy.com/course/aws-certified-solutions-architect-associate-saa-c03/'),
                ('Microsoft Azure Fundamentals', 'https://www.udemy.com/course/microsoft-azure-fundamentals-az-900/'),
                ('Google Cloud Platform Fundamentals', 'https://www.coursera.org/learn/gcp-fundamentals'),
                ('Docker & Kubernetes: The Complete Guide', 'https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/')
            ],
            'business': [
                ('Business Foundations Specialization', 'https://www.coursera.org/specializations/wharton-business-foundations'),
                ('Digital Marketing Specialization', 'https://www.coursera.org/specializations/digital-marketing'),
                ('Project Management Professional (PMP)', 'https://www.udemy.com/course/pmp-certification-exam-prep-course-pmbok-6th-edition/'),
                ('Financial Markets - Yale', 'https://www.coursera.org/learn/financial-markets-global')
            ]
        }

    def get_recommended_courses(self, skills, predicted_field, max_courses=5):
        """Get course recommendations based on skills and predicted field."""
        recommended_courses = []
        
        # Map predicted field to course categories
        field_to_category = {
            'IT': ['programming', 'web_development'],
            'Web Development': ['web_development', 'programming'],
            'Data Science': ['data_science', 'programming'],
            'Cloud Computing': ['cloud', 'programming'],
            'Business': ['business'],
            'Other': ['programming', 'business']  # Default categories
        }
        
        # Get relevant course categories
        categories = field_to_category.get(predicted_field, ['programming', 'business'])
        
        # Add courses from relevant categories
        for category in categories:
            if category in self.courses:
                recommended_courses.extend(self.courses[category])
        
        # Prioritize courses based on missing skills
        skill_set = set(skill.lower() for skill in skills)
        prioritized_courses = []
        
        for course in recommended_courses:
            course_name = course[0].lower()
            # Check if course teaches skills not in the resume
            relevance_score = sum(1 for skill in skill_set if skill not in course_name)
            prioritized_courses.append((relevance_score, course))
        
        # Sort by relevance and take top courses
        prioritized_courses.sort(reverse=True)
        return [course for _, course in prioritized_courses[:max_courses]]

    def get_interview_prep_resources(self):
        """Get interview preparation resources."""
        return [
            ('Cracking the Coding Interview Course', 'https://www.udemy.com/course/master-the-coding-interview-data-structures-algorithms/'),
            ('System Design Interview Course', 'https://www.educative.io/courses/grokking-the-system-design-interview'),
            ('Behavioral Interview Preparation', 'https://www.coursera.org/learn/interview-preparation'),
            ('Mock Interview Practice Platform', 'https://www.pramp.com/')
        ]

    def get_resume_writing_resources(self):
        """Get resume writing and improvement resources."""
        return [
            ('Professional Resume Writing', 'https://www.coursera.org/learn/how-to-write-a-resume'),
            ('LinkedIn Profile Optimization', 'https://www.linkedin.com/learning/learning-linkedin-for-students'),
            ('Personal Branding Course', 'https://www.udemy.com/course/personal-branding-course/'),
            ('Career Development Specialization', 'https://www.coursera.org/specializations/career-development')
        ]
