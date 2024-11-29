# Smart Resume Analyzer Mobile App

This is a WebView-based Android application that wraps the Smart Resume Analyzer web application.

## Prerequisites

1. Android Studio
2. JDK 8 or higher
3. Android SDK

## Building the App

1. Open Android Studio
2. Select "Open an existing Android Studio project"
3. Navigate to the `android` folder in this repository
4. Wait for the project to sync and download dependencies

## Configuration

Before building the app:

1. Host your Streamlit application on a publicly accessible server
2. Update the URL in `MainActivity.java`:
   ```java
   webView.loadUrl("https://your-streamlit-app-url.com");
   ```

## Building the APK

1. In Android Studio, go to Build > Build Bundle(s) / APK(s) > Build APK(s)
2. The APK will be generated in `app/build/outputs/apk/debug/`

## Hosting the Streamlit App

1. Install required packages:
   ```bash
   pip install streamlit pandas nltk pdfminer3
   ```

2. Run the Streamlit app:
   ```bash
   streamlit run App.py
   ```

3. Deploy the app to a hosting service like:
   - Streamlit Cloud
   - Heroku
   - Google Cloud Platform
   - AWS

## Features

- Web-based interface wrapped in native Android app
- PDF resume parsing
- Information extraction:
  - Name
  - Email
  - Phone number
  - Skills
  - Education
  - Work experience
- Mobile-friendly UI

## Security Notes

- Enable HTTPS for your hosted Streamlit app
- Implement proper authentication if needed
- Handle file uploads securely
- Follow Android security best practices
