#!/usr/bin/env python3
"""
Streamlit Motor Data Analysis Dashboard
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

# Import authentication config from external file
try:
    from config import AUTH_USERS, POSTHOG_API_KEY, POSTHOG_PROJECT_ID
    USERS = AUTH_USERS
    # This ensures environment variables are set for subprocess calls
except ImportError:
    st.error("❌ Authentication configuration file not found. Please contact administrator.")
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
        # Login card
        st.markdown("""
        <div style="
            background: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border: 1px solid #e5e7eb;
        ">
        </div>
        """, unsafe_allow_html=True)
        
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
        

        
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #6b7280; font-size: 0.9rem;">
            <p>🔒 Secure access to motor data analytics and visualization tools</p>
            <p>Built with Streamlit • PostHog Integration • Interactive Charts</p>
        </div>
        """, unsafe_allow_html=True)

def format_timestamp_readable(timestamp_str):
    """Convert ISO timestamp to readable American format with Pacific Time"""
    try:
        # Parse the ISO timestamp
        if timestamp_str.endswith('Z'):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        elif '+00:00' in timestamp_str:
            dt = datetime.fromisoformat(timestamp_str)
        else:
            # Try parsing without timezone info, assume UTC
            dt = datetime.fromisoformat(timestamp_str.replace('Z', ''))
            dt = dt.replace(tzinfo=pytz.UTC)
        
        # Convert to Pacific Time
        pacific = pytz.timezone('US/Pacific')
        pt_time = dt.astimezone(pacific)
        
        # Format as MM/DD/YYYY HH:MM:SS AM/PM PT
        formatted = pt_time.strftime('%m/%d/%Y %I:%M:%S %p PT')
        return formatted
    except Exception as e:
        # If parsing fails, return original timestamp
        return timestamp_str

def load_available_data():
    """Load all available CSV data files"""
    data = {}
    csv_pattern = "csv_outputs/posthog_event_*.csv"
    csv_files = glob.glob(csv_pattern)
    
    # Only load data if it exists AND we're not in initial empty state
    if not csv_files:
        return {}
    
    # Check if files are very small (just headers) and skip if so
    for file_path in csv_files:
        try:
            # Check file size - if less than 100 bytes, probably just headers
            if os.path.getsize(file_path) < 100:
                continue
                
            df = pd.read_csv(file_path)
            if len(df) == 0:  # Empty dataframe
                continue
                
            # Extract category name from filename
            filename = os.path.basename(file_path)
            category = filename.replace("posthog_event_", "").replace(".csv", "")
            data[category] = df
        except Exception as e:
            st.warning(f"Could not load {file_path}: {e}")
    
    return data

def load_histogram_data():
    """Load histogram data files"""
    data = {}
    csv_pattern = "histogram_outputs/*_numeric_values.csv"
    csv_files = glob.glob(csv_pattern)
    
    # Only load if files exist and have content
    for file_path in csv_files:
        try:
            # Check file size 
            if os.path.getsize(file_path) < 50:
                continue
                
            df = pd.read_csv(file_path)
            if len(df) == 0:
                continue
                
            # Extract category name from filename
            filename = os.path.basename(file_path)
            category = filename.replace("_numeric_values.csv", "")
            data[category] = df
        except Exception as e:
            st.warning(f"Could not load {file_path}: {e}")
    
    return data

def create_interactive_histogram(df, category):
    """Create an interactive Plotly histogram"""
    fig = go.Figure()
    
    # Create bar chart
    fig.add_trace(go.Bar(
        x=df['Numeric_Label'],
        y=df['Value'],
        text=df['Value'],
        textposition='auto',
        hovertemplate='<b>Index:</b> %{x}<br><b>Value:</b> %{y}<br><b>Property:</b> %{customdata}<extra></extra>',
        customdata=df['Original_Property'],
        marker=dict(
            color=df['Value'],
            colorscale='viridis',
            showscale=True,
            colorbar=dict(title="Value")
        )
    ))
    
    fig.update_layout(
        title=f'{category.replace("_", " ").title()} - Interactive Analysis',
        xaxis_title='Index',
        yaxis_title='Values',
        height=500,
        showlegend=False
    )
    
    return fig

def parse_events_from_output(output):
    """Parse events from GetPostHog.py output"""
    events = []
    lines = output.split('\n')
    
    for line in lines:
        line = line.strip()
        # Look for numbered event lines like "1. 2025-06-25T21:02:12.715Z (Session: xxxxx, 46 properties)"
        if line and (line[0].isdigit() and '. ' in line):
            try:
                # Split on the first '. ' to separate number from rest
                parts = line.split('. ', 1)
                if len(parts) >= 2:
                    event_text = parts[1]
                    
                    # Extract timestamp (ISO format)
                    import re
                    timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?', event_text)
                    
                    # Extract session ID from (Session: xxxxx, properties)
                    session_match = re.search(r'Session:\s*([^,)]+)', event_text)
                    session_id = session_match.group(1).strip() if session_match else "Unknown"
                    
                    # Extract property count from ", XX properties)"
                    properties_match = re.search(r'(\d+)\s+properties', event_text)
                    properties_count = properties_match.group(1) if properties_match else "Unknown"
                    
                    if timestamp_match:
                        timestamp = timestamp_match.group()
                        events.append({
                            'timestamp': timestamp,
                            'session_id': session_id,
                            'properties_count': properties_count,
                            'line': line
                        })
            except Exception:
                continue
        # Alternative format: lines with timestamp patterns directly
        elif 'T' in line and ('Z' in line or '+' in line):
            import re
            timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})', line)
            if timestamp_match:
                timestamp = timestamp_match.group()
                events.append({
                    'timestamp': timestamp,
                    'session_id': "Unknown",
                    'properties_count': "Unknown",
                    'line': line
                })
    
    return events

def fetch_motor_data(person_id, session_id=None):
    """Fetch motor data from PostHog for the given person ID"""
    try:
        # Use sys.executable to ensure same Python environment
        cmd = [sys.executable, "-W", "ignore", "scripts/GetPostHog.py", "-p", person_id]
        
        if session_id and session_id.strip():
            cmd.extend(["-s", session_id.strip()])
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            return True, "Data fetched successfully!"
        else:
            return False, f"Error: {result.stderr}"
    except Exception as e:
        return False, f"Failed to fetch data: {str(e)}"

def fetch_events_list(person_id):
    """Fetch list of available events for the person"""
    try:
        # Ensure output directories exist
        os.makedirs("csv_outputs", exist_ok=True)
        os.makedirs("histogram_outputs", exist_ok=True)
        
        # Use sys.executable to ensure same Python environment  
        cmd = [sys.executable, "-W", "ignore", "scripts/GetPostHog.py", "-p", person_id, "-s", "", "-l"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            # Parse the output to extract events
            events = parse_events_from_output(result.stdout)
            
            return True, events
        else:
            st.error(f"Failed to fetch events (exit code {result.returncode})")
            if result.stderr:
                st.error(f"Error details: {result.stderr}")
            return False, []
    except Exception as e:
        st.error(f"Failed to fetch events: {str(e)}")
        return False, []

def fetch_specific_event_data(person_id, timestamp):
    """Fetch data for a specific event timestamp"""
    try:
        # Ensure output directories exist
        os.makedirs("csv_outputs", exist_ok=True)
        os.makedirs("histogram_outputs", exist_ok=True)
        
        # Use sys.executable to ensure same Python environment
        cmd = [sys.executable, "-W", "ignore", "scripts/GetPostHog.py", "-p", person_id, "-t", timestamp, "-s", ""]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".", timeout=60)
        
        if result.returncode == 0:
            st.success("✅ Event data downloaded successfully!")
            return True, "Event data fetched successfully!"
        else:
            st.error(f"❌ Failed to download event data")
            if result.stderr:
                st.error(f"Error details: {result.stderr}")
            return False, f"Error: {result.stderr or 'Unknown error'}"
    except subprocess.TimeoutExpired:
        st.error("⏰ Download timed out after 60 seconds")
        return False, "Download timed out"
    except Exception as e:
        st.error(f"❌ Failed to fetch event data: {str(e)}")
        return False, f"Failed to fetch event data: {str(e)}"

def run_data_collection(person_id, session_id=None, timestamp=None):
    """Run the data collection script"""
    # Use sys.executable to ensure same Python environment
    cmd = [sys.executable, "-W", "ignore", "scripts/GetPostHog.py", "-p", person_id]
    
    if session_id:
        cmd.extend(["-s", session_id])
    if timestamp:
        cmd.extend(["-t", timestamp])
    
    try:
        with st.spinner("Downloading data from PostHog..."):
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        st.success("✅ Data downloaded successfully!")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        # Check if it's a timestamp not found issue
        if "No event found with timestamp matching" in str(e.stdout):
            st.warning("⚠️ Timestamp not found in available data.")
            
            # Extract available timestamps from output
            if "Available timestamps:" in str(e.stdout):
                lines = str(e.stdout).split('\n')
                timestamps = []
                capture_timestamps = False
                for line in lines:
                    if "Available timestamps:" in line:
                        capture_timestamps = True
                        continue
                    if capture_timestamps and line.strip().startswith('- '):
                        timestamp = line.strip()[2:]  # Remove '- ' prefix
                        timestamps.append(timestamp)
                
                if timestamps:
                    st.info("💡 Try using one of these available timestamps instead:")
                    for ts in timestamps[:5]:  # Show first 5
                        st.code(ts)
                    
                    st.info("🔧 Or clear the timestamp field to fetch the most recent data.")
            
            return False, "Timestamp not found"
        
        # Check if it's just a warning issue
        elif "NotOpenSSLWarning" in str(e.stderr) or "urllib3" in str(e.stderr):
            st.warning("⚠️ This appears to be just an SSL warning. The script may have run successfully.")
            st.info("💡 Check the CSV outputs folder to see if data was downloaded.")
            return True, e.stderr
        else:
            st.error(f"❌ Error downloading data:")
            return False, e.stderr

def run_histogram_generation():
    """Run the histogram generation script"""
    try:
        # Ensure output directories exist
        os.makedirs("csv_outputs", exist_ok=True)
        os.makedirs("histogram_outputs", exist_ok=True)
        
        with st.spinner("Generating histograms..."):
            # Use sys.executable to ensure same Python environment
            result = subprocess.run(
                [sys.executable, "-W", "ignore", "scripts/create_histograms.py"], 
                capture_output=True, text=True, check=True
            )
        st.success("✅ Histograms generated successfully!")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        # Check if it's just a warning issue
        if "NotOpenSSLWarning" in e.stderr or "urllib3" in e.stderr:
            st.warning("⚠️ SSL warning encountered, but script may have run successfully. Check the results.")
            return True, e.stderr
        else:
            st.error(f"❌ Error generating histograms: {e.stderr}")
            return False, e.stderr

def fetch_bulk_events(person_id, event_count=None):
    """Fetch multiple events and combine them into a single dataset (only events with 160+ properties)"""
    try:
        # Ensure output directories exist
        os.makedirs("csv_outputs", exist_ok=True)
        os.makedirs("histogram_outputs", exist_ok=True)
        
        # First get the list of events
        cmd = [sys.executable, "-W", "ignore", "scripts/GetPostHog.py", "-p", person_id, "-s", "", "-l"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".", timeout=120)
        
        if result.returncode != 0:
            return False, f"Failed to fetch event list: {result.stderr or 'Unknown error'}"
        
        # Parse events 
        events = parse_events_from_output(result.stdout)
        if not events:
            return False, "No events found"
        
        # Filter events to only include those with 160+ properties (quality control)
        quality_events = [event for event in events if event['properties_count'] >= 160]
        
        if not quality_events:
            return False, f"No high-quality events found (need 160+ properties). Found {len(events)} events but all had fewer than 160 properties."
        
        # Show filtering info
        if len(quality_events) < len(events):
            st.info(f"🔍 Quality filter: Using {len(quality_events)} events with 160+ properties (filtered out {len(events) - len(quality_events)} low-quality events)")
        
        if event_count:
            # Take only the requested number of recent quality events
            selected_events = quality_events[:event_count]
            action_text = f"last {event_count} quality"
        else:
            # Take all quality events
            selected_events = quality_events
            action_text = f"all {len(quality_events)} quality"
        
        # Download each event
        success_count = 0
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, event in enumerate(selected_events):
            progress = (i + 1) / len(selected_events)
            progress_bar.progress(progress)
            status_text.text(f"Downloading event {i+1}/{len(selected_events)}: {event['timestamp'][:16]} ({event['properties_count']} properties)...")
            
            # Download individual event
            event_cmd = [sys.executable, "-W", "ignore", "scripts/GetPostHog.py", "-p", person_id, "-t", event['timestamp'], "-s", ""]
            event_result = subprocess.run(event_cmd, capture_output=True, text=True, cwd=".", timeout=60)
            
            if event_result.returncode == 0:
                success_count += 1
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        if success_count > 0:
            st.success(f"✅ Successfully downloaded {success_count}/{len(selected_events)} quality events! Data has been combined in CSV files.")
            return True, f"Downloaded {action_text} events successfully ({success_count}/{len(selected_events)} succeeded)"
        else:
            return False, "Failed to download any events"
    
    except subprocess.TimeoutExpired:
        return False, "Bulk download timed out (operation exceeded 2 minutes)"
    except Exception as e:
        return False, f"Failed to fetch bulk events: {str(e)}"

def main():
    # Check authentication first
    if not check_authentication():
        show_login_page()
        return
    
    # Add clean dark theme CSS
    st.markdown("""
    <style>
    /* Clean dark theme */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    
    /* Sidebar */
    .stSidebar {
        background-color: #1e293b;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #3b82f6;
        color: white;
        border: none;
    }
    
    /* Tables */
    .stDataFrame {
        background-color: #1e293b;
    }
    
    /* Text inputs */
    .stSelectbox > div > div, .stTextInput > div > div > input {
        background-color: #334155;
        color: #f8fafc;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e293b;
    }
    
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #334155;
        color: #cbd5e1;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #0f172a;
        color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)

    # Load data
    csv_data = load_available_data()
    histogram_data = load_histogram_data()

    # Header with user info
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏎️ Motor Data Analysis Dashboard")
    with col2:
        username = st.session_state.get('username', 'Unknown')
        st.markdown(f"**👤 Logged in as: {username}**")
        if st.button("🚪 Logout"):
            logout()
            st.rerun()

    # Sidebar
    with st.sidebar:
        st.header("🔧 Control Panel")
        
        st.markdown(f"**👤 Logged in as: {username}**")
        
        st.header("📊 Data Collection")
        
        with st.expander("Fetch New Data", expanded=False):
            st.text("Person ID")
            person_id = st.text_input("", value="0197a976-e0dd-707e-8eef-104d3d3a24a5", label_visibility="collapsed")
            
            if st.button("🔍 Browse Events"):
                # Show loading state
                with st.spinner("🔍 Searching for recent motor data events..."):
                    # Store the person ID in session state and trigger event browsing
                    st.session_state.person_id = person_id
                    st.session_state.show_event_browser = True
                    # Small delay to show the spinner
                    import time
                    time.sleep(0.5)
                st.rerun()
        
        if st.button("📊 Generate Charts", use_container_width=True):
            success, output = run_histogram_generation()
            if success:
                st.rerun()
    
    # Clear Data Section
    with st.sidebar.expander("🗑️ Clear Data", expanded=False):
        st.markdown("**⚠️ Warning**: This will delete all downloaded data and charts.")
        
        # Show what would be cleared
        csv_files = glob.glob("csv_outputs/*.csv")
        histogram_files = glob.glob("histogram_outputs/*")
        total_files = len(csv_files) + len([f for f in histogram_files if os.path.isfile(f)])
        
        if total_files > 0:
            st.info(f"📁 {total_files} files will be deleted")
            
            if st.button("🗑️ Clear All Data", use_container_width=True, type="primary"):
                cleared_files = []
                
                # Clear CSV files
                for file in csv_files:
                    try:
                        os.remove(file)
                        cleared_files.append(os.path.basename(file))
                    except Exception as e:
                        st.error(f"Could not delete {file}: {e}")
                
                # Clear histogram files
                for file in histogram_files:
                    if os.path.isfile(file):
                        try:
                            os.remove(file)
                            cleared_files.append(os.path.basename(file))
                        except Exception as e:
                            st.error(f"Could not delete {file}: {e}")
                
                if cleared_files:
                    st.success(f"✅ Cleared {len(cleared_files)} files")
                    st.rerun()
        else:
            st.info("ℹ️ No data files to clear")
    
    # Event Browser Interface
    if hasattr(st.session_state, 'show_event_browser') and st.session_state.show_event_browser:
        # Modern header with custom styling
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0; background: linear-gradient(90deg, #1e40af, #3730a3); border-radius: 1rem; margin-bottom: 2rem;">
            <h1 style="color: white; margin: 0; font-size: 2.5rem;">🔍 Browse Motor Data Events</h1>
            <p style="color: #e5e7eb; margin: 0.5rem 0 0 0; font-size: 1.2rem;">Select an event from your recent motor data to download and analyze</p>
        </div>
        """, unsafe_allow_html=True)
        
        person_id = st.session_state.get('person_id', '0197a976-e0dd-707e-8eef-104d3d3a24a5')
        
        with st.spinner("🔍 Fetching recent events..."):
            success, events = fetch_events_list(person_id)
        
        if success and events:
            # Initialize pagination state
            if 'event_page' not in st.session_state:
                st.session_state.event_page = 0
            
            # Convert the parsed events to a more structured format
            formatted_events = []
            for i, event in enumerate(events, 1):
                formatted_events.append({
                    'number': str(i),
                    'timestamp': event['timestamp'],
                    'session_id': event['session_id'],
                    'properties_count': event['properties_count'],
                    'details': event.get('line', '')
                })
            
            # Pagination settings
            events_per_page = 10
            total_events = len(formatted_events)
            total_pages = (total_events + events_per_page - 1) // events_per_page  # Ceiling division
            current_page = st.session_state.event_page
            
            # Ensure current page is within bounds
            if current_page >= total_pages:
                st.session_state.event_page = 0
                current_page = 0
            
            # Calculate start and end indices for current page
            start_idx = current_page * events_per_page
            end_idx = min(start_idx + events_per_page, total_events)
            current_events = formatted_events[start_idx:end_idx]
            
            # Pagination controls at the top
            st.markdown("### 📄 Page Navigation")
            
            col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
            
            with col1:
                if st.button("⏮️ First", disabled=(current_page == 0), key="first_page_top"):
                    st.session_state.event_page = 0
                    st.rerun()
            
            with col2:
                if st.button("◀️ Previous", disabled=(current_page == 0), key="prev_page_top"):
                    st.session_state.event_page = max(0, current_page - 1)
                    st.rerun()
            
            with col3:
                st.markdown(f"**Page {current_page + 1} of {total_pages}** (Events {start_idx + 1}-{end_idx} of {total_events})")
            
            with col4:
                if st.button("Next ▶️", disabled=(current_page >= total_pages - 1), key="next_page_top"):
                    st.session_state.event_page = min(total_pages - 1, current_page + 1)
                    st.rerun()
            
            with col5:
                if st.button("Last ⏭️", disabled=(current_page >= total_pages - 1), key="last_page_top"):
                    st.session_state.event_page = total_pages - 1
                    st.rerun()
            
            # Modern section header
            st.markdown("""
            <div style="margin: 2rem 0 1rem 0;">
                <h2 style="color: #1f2937; border-bottom: 3px solid #3b82f6; padding-bottom: 0.5rem; margin: 0;">
                    📋 Select Event to Download
                </h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Create individual event cards instead of a table
            for i, event in enumerate(current_events):
                event_num = event['number']
                timestamp = event['timestamp']
                formatted_time = format_timestamp_readable(timestamp)
                properties_count = event['properties_count']
                
                # Create a unique key for each button
                button_key = f"download_event_{event_num}_page_{current_page}"
                
                # Event card with clickable download
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    # Main event button with all info displayed
                    if st.button(
                        f"📥 Event {event_num}: {formatted_time} • {properties_count} properties",
                        key=button_key,
                        use_container_width=True,
                        type="primary" if i == 0 else "secondary",
                        help=f"Click to download Event {event_num} motor data"
                    ):
                        with st.spinner(f"📥 Downloading Event {event_num}..."):
                            success, output = fetch_specific_event_data(person_id, timestamp)
                        
                        if success:
                            st.session_state.show_event_browser = False
                            if 'event_page' in st.session_state:
                                del st.session_state.event_page  # Reset pagination
                            st.rerun()
                        else:
                            st.error(f"❌ Download failed: {output}")
                            st.info("💡 Try refreshing the list or check your connection.")
                
                with col2:
                    # Show event number prominently
                    st.markdown(f"**Event {event_num}**")
            
            # Control buttons section
            st.markdown("---")
            st.markdown("### 🔧 Controls")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("🔙 Back to Dashboard", use_container_width=True, help="Return to main dashboard"):
                    st.session_state.show_event_browser = False
                    if 'event_page' in st.session_state:
                        del st.session_state.event_page  # Reset pagination
                    st.rerun()
            
            with col2:
                if st.button("🔄 Refresh", use_container_width=True, help="Refresh the event list"):
                    if 'event_page' in st.session_state:
                        del st.session_state.event_page  # Reset pagination
                    st.rerun()
            
            # Bulk download section
            st.markdown("---")
            st.markdown("### 📦 Bulk Downloads")
            st.markdown("*Download multiple events at once for comprehensive analysis (160+ properties only)*")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("📥 Get Last 5 Quality Events", use_container_width=True, type="secondary", 
                           help="Download and combine the 5 most recent events with 160+ properties"):
                    with st.spinner("📥 Downloading last 5 quality events..."):
                        success, output = fetch_bulk_events(person_id, event_count=5)
                    
                    if success:
                        st.session_state.show_event_browser = False
                        if 'event_page' in st.session_state:
                            del st.session_state.event_page  # Reset pagination
                        st.rerun()
                    else:
                        st.error(f"❌ Bulk download failed: {output}")
                        st.info("💡 Try refreshing the list or downloading individual events.")
            
            with col2:
                if st.button("📥 Get All Quality Events", use_container_width=True, type="secondary",
                           help="Download all available quality events with 160+ properties (may take several minutes)"):
                    # Show confirmation dialog
                    if 'confirm_all_events' not in st.session_state:
                        st.session_state.confirm_all_events = True
                        st.warning("⚠️ This will download ALL quality events (160+ properties) and may take several minutes. Click again to confirm.")
                    else:
                        del st.session_state.confirm_all_events
                        with st.spinner("📥 Downloading all quality events... This may take several minutes..."):
                            success, output = fetch_bulk_events(person_id, event_count=None)
                        
                        if success:
                            st.session_state.show_event_browser = False
                            if 'event_page' in st.session_state:
                                del st.session_state.event_page  # Reset pagination
                            st.rerun()
                        else:
                            st.error(f"❌ Bulk download failed: {output}")
                            st.info("💡 Try downloading fewer events or check your connection.")
            
            with col3:
                if len(formatted_events) > 5:
                    if st.button(f"📥 Get Current Page ({len(current_events)} events)", use_container_width=True, type="secondary",
                               help=f"Download all {len(current_events)} events from the current page"):
                        with st.spinner(f"📥 Downloading {len(current_events)} events from current page..."):
                            # Download events from current page
                            success_count = 0
                            for event in current_events:
                                event_success, _ = fetch_specific_event_data(person_id, event['timestamp'])
                                if event_success:
                                    success_count += 1
                        
                        if success_count > 0:
                            st.success(f"✅ Downloaded {success_count}/{len(current_events)} events from current page!")
                            st.session_state.show_event_browser = False
                            if 'event_page' in st.session_state:
                                del st.session_state.event_page  # Reset pagination
                            st.rerun()
                        else:
                            st.error("❌ Failed to download any events from current page")
                else:
                    st.button("📥 Current Page", disabled=True, use_container_width=True, 
                            help="Not enough events on current page for bulk download")

        else:
            st.error("❌ No events found in the output")
            if st.button("🔙 Back to Dashboard"):
                st.session_state.show_event_browser = False
                st.rerun()
        
        return  # Don't show the main dashboard when browsing events
    
    # Main dashboard tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Interactive Charts", "📋 Raw Data", "⚙️ Settings"])
    
    with tab1:
        st.header("📊 Data Overview")
        
        if csv_data:
            # Summary information as simple text
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("**📁 Data Categories**")
                st.markdown(f"**{len(csv_data)}**")
            
            with col2:
                total_properties = sum(len(df.columns) - 1 for df in csv_data.values())  # -1 for timestamp
                st.markdown("**🔧 Total Properties**")
                st.markdown(f"**{total_properties}**")
            
            with col3:
                if histogram_data:
                    st.markdown("**📊 Generated Charts**")
                    st.markdown(f"**{len(histogram_data)}**")
                else:
                    st.markdown("**📊 Generated Charts**")
                    st.markdown("**0**")
            
            with col4:
                # Show timestamp of latest data
                latest_timestamp = None
                for df in csv_data.values():
                    if 'timestamp' in df.columns and not df.empty:
                        latest_timestamp = df['timestamp'].iloc[0]
                        break
                
                if latest_timestamp:
                    st.markdown("**🕐 Latest Data**")
                    st.markdown(f"**{latest_timestamp[:16]}**")
                else:
                    st.markdown("**🕐 Latest Data**")
                    st.markdown("**Unknown**")
        
        # Show available data categories
        st.subheader("Available Data Categories")
        
        if csv_data:
            categories_df = pd.DataFrame([
                {
                    "Category": category.replace("_", " ").title(),
                    "Properties": len(df.columns) - 1,  # -1 for timestamp
                    "File Size": f"{os.path.getsize(f'csv_outputs/posthog_event_{category}.csv') / 1024:.1f} KB"
                }
                for category, df in csv_data.items()
            ])
            
            st.dataframe(categories_df, use_container_width=True, hide_index=True)
        else:
            st.info("No CSV data available")
    
    with tab2:
        st.header("📈 Interactive Data Visualization")
        
        if histogram_data:
            # Category selector
            selected_categories = st.multiselect(
                "Select categories to visualize:",
                options=list(histogram_data.keys()),
                default=list(histogram_data.keys())[:2] if len(histogram_data) >= 2 else list(histogram_data.keys()),
                format_func=lambda x: x.replace("_", " ").title()
            )
            
            if selected_categories:
                # Display charts
                for category in selected_categories:
                    st.subheader(f"{category.replace('_', ' ').title()} Analysis")
                    
                    df = histogram_data[category]
                    
                    # Create columns for chart and stats
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        fig = create_interactive_histogram(df, category)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.markdown("**📊 Statistics**")
                        st.markdown(f"**Min Value:** {df['Value'].min():.1f}")
                        st.markdown(f"**Max Value:** {df['Value'].max():.1f}")
                        st.markdown(f"**Average:** {df['Value'].mean():.1f}")
                        st.markdown(f"**Properties:** {len(df)}")
                        
                        # Show min/max properties
                        min_idx = df['Value'].idxmin()
                        max_idx = df['Value'].idxmax()
                        
                        st.markdown("**🔍 Extremes**")
                        st.markdown(f"**Min:** Index {df.loc[min_idx, 'Numeric_Label']}")
                        st.markdown(f"**Max:** Index {df.loc[max_idx, 'Numeric_Label']}")
                    
                    st.divider()
            else:
                st.info("Select categories to view their visualizations")
        else:
            st.warning("⚠️ No histogram data available. Generate charts using the sidebar.")
            
            # Show static images if available
            png_files = glob.glob("histogram_outputs/*.png")
            if png_files:
                st.info("📸 Static histogram images found:")
                for png_file in sorted(png_files):
                    category = os.path.basename(png_file).replace("_numeric_values.png", "")
                    st.subheader(f"{category.replace('_', ' ').title()}")
                    st.image(png_file)
    
    with tab3:
        st.header("📋 Raw Data Exploration")
        
        if csv_data:
            # Category selector for raw data
            selected_category = st.selectbox(
                "Select a category to explore:",
                options=list(csv_data.keys()),
                format_func=lambda x: x.replace("_", " ").title()
            )
            
            if selected_category:
                df = csv_data[selected_category]
                
                st.subheader(f"Raw Data: {selected_category.replace('_', ' ').title()}")
                
                # Show data info as simple text
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**Rows**")
                    st.markdown(f"**{len(df)}**")
                with col2:
                    st.markdown("**Columns**")
                    st.markdown(f"**{len(df.columns)}**")
                with col3:
                    st.markdown("**Timestamp**")
                    if 'timestamp' in df.columns:
                        timestamp_val = df['timestamp'].iloc[0] if not df.empty else "N/A"
                        st.markdown(f"**{timestamp_val}**")
                    else:
                        st.markdown("**N/A**")
                
                # Display data
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"📥 Download {selected_category}.csv",
                    data=csv,
                    file_name=f"{selected_category}_data.csv",
                    mime="text/csv"
                )
        else:
            st.info("No raw data available")
    
    with tab4:
        st.header("⚙️ Settings & Information")
        
        st.subheader("📁 File Information")
        
        # Show file structure
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**CSV Data Files:**")
            csv_files = glob.glob("csv_outputs/*.csv")
            if csv_files:
                for file in sorted(csv_files):
                    size = os.path.getsize(file) / 1024
                    st.text(f"📄 {os.path.basename(file)} ({size:.1f} KB)")
            else:
                st.text("No CSV files found")
        
        with col2:
            st.markdown("**Histogram Files:**")
            hist_files = glob.glob("histogram_outputs/*")
            if hist_files:
                for file in sorted(hist_files):
                    if os.path.isfile(file):
                        size = os.path.getsize(file) / 1024
                        st.text(f"📊 {os.path.basename(file)} ({size:.1f} KB)")
            else:
                st.text("No histogram files found")
        
        st.subheader("🔧 System Information")
        st.text(f"Python Version: {sys.version}")
        st.text(f"Working Directory: {os.getcwd()}")
        st.text(f"Streamlit Version: {st.__version__}")
        
        st.subheader("📖 About")
        st.markdown("""
        **Motor Data Analysis Dashboard**
        
        This dashboard provides an interactive interface for analyzing PostHog motor data:
        
        - **Data Collection**: Fetch motor data from PostHog API
        - **Visualization**: Interactive charts and histograms
        - **Analysis**: Statistical insights and data exploration
        - **Export**: Download processed data and visualizations
        
        Built with Streamlit, Pandas, Matplotlib, and Plotly.
        """)

if __name__ == "__main__":
    main() 