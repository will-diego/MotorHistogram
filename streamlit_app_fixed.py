#!/usr/bin/env python3
"""
Streamlit Motor Data Analysis Dashboard - Fixed Version
Interactive web interface for PostHog motor data visualization and analysis
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob
import os
import subprocess
import sys
from pathlib import Path
import re
from datetime import datetime, timedelta
import pytz
import hashlib

# Configure page
st.set_page_config(
    page_title="🚗 Motor Data Analysis Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .css-1d391kg {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# === AUTHENTICATION SYSTEM ===

# Safe import of authentication config
try:
    from config import AUTH_USERS, POSTHOG_API_KEY, POSTHOG_PROJECT_ID
    USERS = AUTH_USERS
    st.success("✅ Config imported successfully")
except ImportError as e:
    st.error(f"❌ Config import failed: {e}")
    # Fallback authentication for debugging
    USERS = {
        "will": "832816e4cdf8e0501116098ef850deb1a42bf3cbdc07af319086c4439b14c407",
        "bimotal": "e4f009916270bff8106f9bbd562d1937e4fdb92b1df2ad570458767e8051d71e"
    }
    POSTHOG_API_KEY = "phx_ETiyf25aQLPtOPBBnPHYi6vJCPvKOtalYtaAWIZ1XhvNs6n"
    POSTHOG_PROJECT_ID = "113002"
    st.warning("⚠️ Using fallback authentication")
except Exception as e:
    st.error(f"❌ Unexpected error loading config: {e}")
    st.error(f"Error type: {type(e)}")
    st.error(f"Error details: {str(e)}")
    st.stop()

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_authentication():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def authenticate_user(username, password):
    """Authenticate user with username and password"""
    if username in USERS and USERS[username] == hash_password(password):
        st.session_state.authenticated = True
        st.session_state.username = username
        return True
    return False

def logout():
    """Logout user"""
    st.session_state.authenticated = False
    if 'username' in st.session_state:
        del st.session_state.username
    st.rerun()

def show_login_page():
    """Display the login page"""
    st.markdown("""
    <div style="text-align: center; padding: 3rem 0;">
        <h1 style="color: #1f2937; font-size: 3rem; margin-bottom: 0.5rem;">🚗 Motor Data Analysis</h1>
        <p style="color: #6b7280; font-size: 1.2rem; margin-bottom: 3rem;">Secure Dashboard Access</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login to Dashboard")
        
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔑 Password", type="password", placeholder="Enter your password")
            
            col_login1, col_login2, col_login3 = st.columns([1, 2, 1])
            with col_login2:
                login_button = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")
            
            if login_button:
                if username and password:
                    if authenticate_user(username, password):
                        st.success("✅ Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("⚠️ Please enter both username and password")

def main():
    """Main application function"""
    
    # Debug information
    st.sidebar.markdown("### 🔧 Debug Info")
    st.sidebar.text(f"Python: {sys.version[:5]}")
    st.sidebar.text(f"Streamlit: {st.__version__}")
    st.sidebar.text(f"Working Dir: {os.getcwd()}")
    
    # Check authentication first
    if not check_authentication():
        show_login_page()
        return
    
    # Welcome header
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="color: #1f2937;">🚗 Motor Data Analysis Dashboard</h1>
        <p style="color: #6b7280;">Interactive analysis of PostHog motor data with real-time visualization</p>
    </div>
    """, unsafe_allow_html=True)
    
    # User info and logout
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"**Welcome, {st.session_state.username}!** 👋")
    with col2:
        if st.button("🚪 Logout", type="secondary"):
            logout()
    
    # Simple dashboard content
    st.markdown("## 📊 Dashboard Content")
    st.info("🎉 Authentication working! App is running successfully on Streamlit Cloud.")
    
    # Test basic functionality
    st.markdown("### 🧪 System Tests")
    
    # Test imports
    try:
        import requests
        st.success("✅ Requests module available")
    except ImportError:
        st.error("❌ Requests module not available")
    
    try:
        import pandas as pd
        st.success("✅ Pandas module available")
    except ImportError:
        st.error("❌ Pandas module not available")
    
    # Test file system
    if os.path.exists("csv_outputs"):
        st.success("✅ CSV outputs directory exists")
    else:
        st.warning("⚠️ CSV outputs directory not found")
    
    if os.path.exists("scripts/GetPostHog.py"):
        st.success("✅ GetPostHog script found")
    else:
        st.warning("⚠️ GetPostHog script not found")
    
    # Show environment info
    st.markdown("### 🌍 Environment")
    st.text(f"POSTHOG_API_KEY: {'Set' if POSTHOG_API_KEY else 'Not set'}")
    st.text(f"POSTHOG_PROJECT_ID: {POSTHOG_PROJECT_ID}")
    st.text(f"Users configured: {len(USERS)}")

if __name__ == "__main__":
    main() 