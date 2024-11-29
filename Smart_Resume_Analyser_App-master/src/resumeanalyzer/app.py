import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
from custom_parser import CustomResumeParser

class SmartResumeAnalyzer(toga.App):
    def __init__(self):
        super().__init__()

    def startup(self):
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Create main box with vertical layout
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        
        # Add title
        title_label = toga.Label(
            'Smart Resume Analyzer',
            style=Pack(padding=(0, 0, 10, 0), font_size=20)
        )
        
        # Add file selection button
        self.file_button = toga.Button(
            'Select Resume (PDF)',
            on_press=self.select_file,
            style=Pack(padding=5)
        )
        
        # Add result display
        self.result_display = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, padding=5)
        )
        
        # Add analyze button
        self.analyze_button = toga.Button(
            'Analyze Resume',
            on_press=self.analyze_resume,
            style=Pack(padding=5)
        )
        self.analyze_button.enabled = False
        
        # Add widgets to main box
        main_box.add(title_label)
        main_box.add(self.file_button)
        main_box.add(self.analyze_button)
        main_box.add(self.result_display)
        
        # Set main window content
        self.main_window.content = main_box
        self.main_window.show()
        
    async def select_file(self, widget):
        try:
            self.resume_file = await self.main_window.select_file_dialog(
                "Select Resume PDF",
                file_types=['pdf']
            )
            if self.resume_file:
                self.analyze_button.enabled = True
                self.result_display.value = f"Selected file: {os.path.basename(self.resume_file)}\n"
        except Exception as e:
            self.result_display.value = f"Error selecting file: {str(e)}\n"
            
    def analyze_resume(self, widget):
        try:
            if hasattr(self, 'resume_file'):
                parser = CustomResumeParser(self.resume_file)
                data = parser.get_extracted_data()
                
                # Format results
                result_text = "Resume Analysis Results:\n\n"
                result_text += f"Name: {data.get('name', 'Not found')}\n"
                result_text += f"Email: {data.get('email', 'Not found')}\n"
                result_text += f"Phone: {data.get('mobile_number', 'Not found')}\n\n"
                
                result_text += "Skills:\n"
                for skill in data.get('skills', []):
                    result_text += f"- {skill}\n"
                
                result_text += "\nEducation:\n"
                for edu in data.get('education', []):
                    result_text += f"- {edu}\n"
                    
                result_text += "\nExperience:\n"
                for exp in data.get('experience', []):
                    result_text += f"- {exp}\n"
                
                self.result_display.value = result_text
            else:
                self.result_display.value = "Please select a resume file first."
        except Exception as e:
            self.result_display.value = f"Error analyzing resume: {str(e)}"

def main():
    return SmartResumeAnalyzer()
