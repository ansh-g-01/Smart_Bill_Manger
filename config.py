import streamlit as st

# Email config
EMAIL = st.secrets["EMAIL"]
APP_PASSWORD = st.secrets["APP_PASSWORD"]
OCR_API_KEY = st.secrets["OCR_API_KEY"]
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")  # Optional, if using Groq