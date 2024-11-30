"""UI utility functions for the resume analyzer."""

import streamlit as st
import base64
from constants import TYPING_MESSAGES

def setup_page_config():
    """Configure the Streamlit page settings."""
    st.set_page_config(
        page_title="Smart Resume Analyzer",
        page_icon='📄',
        layout='wide'
    )

def get_custom_css():
    """Return custom CSS styles for the application."""
    return """
        <style>
            .typing-container {
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 50px;
            }

            .typing {
                font-size: 1.2rem;
                font-weight: 500;
                color: #1e88e5;
                position: relative;
                width: 0;
                overflow: hidden;
                white-space: nowrap;
                border-right: none;
                animation: typing 5s steps(30) infinite;
            }

            .typing::after {
                content: "|";
                position: absolute;
                right: -8px;
                animation: blink 1s infinite step-end;
            }

            @keyframes typing {
                0% { width: 0 }
                30% { width: 385px }
                80% { width: 385px }
                90% { width: 0 }
                100% { width: 0 }
            }

            @keyframes blink {
                from, to { opacity: 1 }
                50% { opacity: 0 }
            }

            .typing::before {
                content: "Unlock Your Career Potential 🚀";
                animation: content 20s infinite;
            }

            @keyframes content {
                0%, 25% { content: "Unlock Your Career Potential 🚀"; }
                25.1%, 50% { content: "Get Smart Resume Analysis 📊"; }
                50.1%, 75% { content: "Discover Your Perfect Career Path 🎯"; }
                75.1%, 100% { content: "Enhance Your Professional Journey 💼"; }
            }

            .main-header {
                background: linear-gradient(-45deg, #2b5876, #4e4376);
                color: white;
                padding: 2rem;
                border-radius: 15px;
                text-align: center;
                margin-bottom: 2rem;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            }

            .info-card {
                background: white;
                padding: 1.5rem;
                border-radius: 12px;
                margin: 1rem 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-left: 5px solid #2b5876;
            }

            .score-bar {
                display: flex;
                align-items: center;
                margin-bottom: 8px;
                background: #f0f2f6;
                border-radius: 6px;
                height: 20px;
                position: relative;
                overflow: hidden;
            }

            .score-bar-label {
                position: absolute;
                left: 8px;
                font-size: 0.85rem;
                font-weight: 500;
                z-index: 2;
                color: #1e1e1e;
            }

            .score-bar-value {
                position: absolute;
                right: 8px;
                font-size: 0.85rem;
                font-weight: 500;
                z-index: 2;
                color: #1e1e1e;
            }

            .score-bar-fill {
                position: absolute;
                left: 0;
                top: 0;
                height: 100%;
                transition: width 0.5s ease;
                border-radius: 6px;
            }
        </style>
    """

def show_header():
    """Display the main header with typing animation."""
    st.markdown('''
        <div class="main-header">
            <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem;">📄 Smart Resume Analyzer</h1>
            <div class="typing-container">
                <span class="typing"></span>
            </div>
        </div>
    ''', unsafe_allow_html=True)

def get_table_download_link(df, filename, text):
    """Generate a link to download the dataframe as CSV."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'data:file/csv;base64,{b64}'
    return f'<a href="{href}" download="{filename}">{text}</a>'

def create_score_bar(label, score, color):
    """Create a compact score bar with label and value."""
    st.markdown(f"""
        <div class="score-bar">
            <span class="score-bar-label">{label}</span>
            <span class="score-bar-value">{score}%</span>
            <div class="score-bar-fill" style="width: {score}%; background-color: {color}; opacity: 0.2;"></div>
        </div>
    """, unsafe_allow_html=True)
