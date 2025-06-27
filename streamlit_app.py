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
                    if timestamp_match:
                        timestamp = timestamp_match.group()
                        events.append({
                            'timestamp': timestamp,
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
            # Debug: Show what we got from the script
            st.info(f"🔧 Debug - Script output length: {len(result.stdout)} characters")
            if len(result.stdout) > 0:
                # Show first few lines for debugging
                lines = result.stdout.split('\n')[:10]
                st.info(f"🔧 Debug - First 10 lines of output:")
                for i, line in enumerate(lines):
                    if line.strip():
                        st.code(f"Line {i+1}: {line}")
            
            # Parse the output to extract events
            events = parse_events_from_output(result.stdout)
            st.info(f"🔧 Debug - Parsed {len(events)} events from output")
            
            return True, events
        else:
            st.error(f"Failed to fetch events (exit code {result.returncode})")
            if result.stderr:
                st.error(f"Error details: {result.stderr}")
            if result.stdout:
                st.info(f"Script output: {result.stdout}")
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
        
        st.info(f"🔧 Debug - Downloading event: {timestamp}")
        st.info(f"🔧 Debug - Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".", timeout=60)
        
        st.info(f"🔧 Debug - Exit code: {result.returncode}")
        if result.stdout:
            st.info(f"🔧 Debug - Output length: {len(result.stdout)} characters")
        if result.stderr:
            st.info(f"🔧 Debug - Error output: {result.stderr[:200]}...")
        
        if result.returncode == 0:
            st.success("✅ Event data downloaded successfully!")
            return True, "Event data fetched successfully!"
        else:
            st.error(f"❌ Failed to download event data (exit code: {result.returncode})")
            if result.stderr:
                st.error(f"Error details: {result.stderr}")
            if result.stdout:
                st.info(f"Script output: {result.stdout}")
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
        # Debug: show the command being run (truncate long arguments)
        cmd_display = []
        for arg in cmd:
            if len(arg) > 50:
                cmd_display.append(arg[:50] + "...")
            else:
                cmd_display.append(arg)
        st.info(f"🔧 Running command: {' '.join(cmd_display)}")
        
        with st.spinner("Downloading data from PostHog..."):
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        st.success("✅ Data downloaded successfully!")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        # Show both stdout and stderr for debugging
        st.error(f"❌ Error downloading data:")
        st.code(f"Exit code: {e.returncode}")
        if e.stdout:
            st.code(f"STDOUT:\n{e.stdout}")
        if e.stderr:
            st.code(f"STDERR:\n{e.stderr}")
        
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

def main():
    # Check authentication first
    if not check_authentication():
        show_login_page()
        return
    
    # Header with user info and logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🚗 Motor Data Analysis Dashboard")
        st.markdown("### Interactive analysis of PostHog motor data with real-time visualization")
    
    with col2:
        st.markdown(f"**👤 Welcome, {st.session_state.username}**")
        if st.button("🚪 Logout", key="logout_button"):
            logout()
    
    # Sidebar
    st.sidebar.title("🔧 Control Panel")
    
    # User info in sidebar
    st.sidebar.markdown(f"""
    <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 0.5rem; padding: 1rem; margin-bottom: 1rem;">
        <p style="margin: 0; color: #0c4a6e; font-weight: 600;">
            👤 Logged in as: <strong>{st.session_state.username}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Data Collection Section
    st.sidebar.header("📥 Data Collection")
    
    with st.sidebar.expander("Fetch New Data", expanded=True):
        person_id = st.text_input(
            "Person ID", 
            value="0197a976-e0dd-707e-8eef-104d3d3a24a5",
            help="Enter the PostHog person ID to fetch data for"
        )
        
        if st.button("🔍 Browse Events", use_container_width=True):
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
            # Convert the parsed events to a more structured format
            formatted_events = []
            for i, event in enumerate(events, 1):
                formatted_events.append({
                    'number': str(i),
                    'timestamp': event['timestamp'],
                    'session_id': "Unknown",  # Will need to extract from event data if available
                    'properties_count': "Unknown",  # Will need to count properties if available
                    'details': event.get('line', '')
                })
            
            # Modern success card
            st.markdown(f"""
            <div style="background: #dcfce7; border: 1px solid #16a34a; border-radius: 0.75rem; padding: 1rem; margin: 1rem 0;">
                <p style="color: #15803d; margin: 0; font-weight: 600;">
                    ✅ Found {len(formatted_events)} recent motor data events
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Create a DataFrame for better display with formatted timestamps
            events_df = pd.DataFrame([
                {
                    "Event #": event['number'],
                    "Date & Time (PT)": format_timestamp_readable(event['timestamp']),
                    "Session ID": event['session_id'][:8] + "..." if len(event['session_id']) > 8 else event['session_id'],
                    "Properties": event['properties_count'],
                    "Full Session ID": event['session_id'],  # Hidden column for reference
                    "Original Timestamp": event['timestamp']  # Hidden column for reference
                }
                for event in formatted_events[:25]  # Show max 25 events
            ])
            
            # Modern section header
            st.markdown("""
            <div style="margin: 2rem 0 1rem 0;">
                <h2 style="color: #1f2937; border-bottom: 3px solid #3b82f6; padding-bottom: 0.5rem; margin: 0;">
                    📋 Available Events
                </h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Display events in a clean, simplified table with better styling
            display_df = events_df[["Event #", "Date & Time (PT)", "Properties"]]
            
            # Custom CSS for the dataframe
            st.markdown("""
            <style>
            .stDataFrame {
                border: 1px solid #e5e7eb;
                border-radius: 0.75rem;
                overflow: hidden;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.dataframe(display_df, use_container_width=True, height=350)
            
            # Modern section divider
            st.markdown("""
            <div style="margin: 2rem 0 1rem 0;">
                <h2 style="color: #1f2937; border-bottom: 3px solid #10b981; padding-bottom: 0.5rem; margin: 0;">
                    🎯 Select Event to Download
                </h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Enhanced dropdown with better styling
            event_options = [f"Event {event['number']}: {format_timestamp_readable(event['timestamp'])}" for event in formatted_events[:25]]
            
            # Create a nice container for the dropdown
            with st.container():
                selected_option = st.selectbox(
                    "Choose an event:",
                    options=event_options,
                    index=0,
                    help="Select the motor data event you want to analyze",
                    key="event_selector"
                )
            
            # Get the selected event index
            selected_idx = event_options.index(selected_option)
            selected_event = formatted_events[selected_idx]
            selected_timestamp = selected_event['timestamp']
            
            # Modern selected event card with gradient background
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 1rem;
                padding: 1.5rem;
                margin: 1.5rem 0;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            ">
                <h3 style="color: white; margin: 0 0 0.5rem 0; font-size: 1.25rem;">
                    📋 Selected Event
                </h3>
                <div style="
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 0.5rem;
                    padding: 1rem;
                    backdrop-filter: blur(10px);
                ">
                    <p style="color: white; margin: 0; font-size: 1.1rem; font-weight: 500;">
                        <span style="background: rgba(255, 255, 255, 0.3); padding: 0.25rem 0.5rem; border-radius: 0.25rem; margin-right: 0.5rem;">
                            Event {selected_event['number']}
                        </span>
                        {format_timestamp_readable(selected_timestamp)}
                    </p>
                    <p style="color: #e5e7eb; margin: 0.5rem 0 0 0; font-size: 0.95rem;">
                        📊 Contains {selected_event['properties_count']} motor data properties
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Modern action buttons with spacing
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if st.button("🔙 Back to Dashboard", use_container_width=True, help="Return to main dashboard"):
                    st.session_state.show_event_browser = False
                    st.rerun()
            
            with col2:
                if st.button("📥 Download & Analyze Event", use_container_width=True, type="primary", help="Download this event data and return to dashboard"):
                    with st.spinner("📥 Downloading motor data..."):
                        success, output = fetch_specific_event_data(person_id, selected_timestamp)
                    
                    if success:
                        st.session_state.show_event_browser = False
                        st.rerun()
                    else:
                        st.error(f"❌ Download failed: {output}")
                        st.info("💡 Try selecting a different event or refresh the list.")
            
            with col3:
                if st.button("🔄 Refresh", use_container_width=True, help="Refresh the event list"):
                    st.rerun()
        else:
            st.error("❌ No events found in the output")
            if st.button("🔙 Back to Dashboard"):
                st.session_state.show_event_browser = False
                st.rerun()
        
        return  # Don't show the main dashboard when browsing events
    
    # Load available data
    csv_data = load_available_data()
    histogram_data = load_histogram_data()
    
    # Show welcome screen when no data is available
    if not csv_data and not histogram_data:
        st.markdown("---")
        
        # Welcome message
        st.markdown("""
        ### 👋 Welcome to the Motor Data Analysis Dashboard!
        
        **Getting Started:**
        1. 🔍 Click **'Browse Events'** in the sidebar to see recent motor data events
        2. 📅 Select an event from the list (timestamps are shown in readable format)
        3. 📥 Click **'Fetch This Event'** to download the data
        4. 📊 Generate charts and explore your data!
        
        **Features:**
        - 📈 **Interactive Charts** - Dynamic visualizations with Plotly
        - 📋 **Raw Data Explorer** - Browse and download your data
        - ⚙️ **Settings** - File management and system information
        """)
        
        # Quick start section
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            #### 🚀 Quick Start
            
            Ready to analyze your motor data? Start by browsing available events using the sidebar controls.
            
            The system will automatically categorize your data into:
            - ⚡ **Power** measurements
            - 🔄 **Torque** readings  
            - 🌡️ **Temperature** data (Motor & MOSFET)
            - ❄️ **Cooldown** metrics
            """)
        
        with col2:
            st.markdown("""
            #### 📊 What You'll Get
            
            Once you've loaded data, you'll see:
            - **Overview** - Summary statistics and metrics
            - **Interactive Charts** - Zoomable, filterable visualizations
            - **Raw Data** - Full data tables with export options
            - **Settings** - File management and technical details
            """)
        
        # Center the browse events button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🎯 Ready to start?")
            st.info("Use the **'🔍 Browse Events'** button in the sidebar to get started!")
        
        return
    
    # Main dashboard tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Interactive Charts", "📋 Raw Data", "⚙️ Settings"])
    
    with tab1:
        st.header("📊 Data Overview")
        
        if csv_data:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📁 Data Categories", len(csv_data))
            
            with col2:
                total_properties = sum(len(df.columns) - 1 for df in csv_data.values())  # -1 for timestamp
                st.metric("🔧 Total Properties", total_properties)
            
            with col3:
                if histogram_data:
                    st.metric("📊 Generated Charts", len(histogram_data))
                else:
                    st.metric("📊 Generated Charts", 0)
            
            with col4:
                # Show timestamp of latest data
                latest_timestamp = None
                for df in csv_data.values():
                    if 'timestamp' in df.columns and not df.empty:
                        latest_timestamp = df['timestamp'].iloc[0]
                        break
                
                if latest_timestamp:
                    st.metric("🕐 Latest Data", latest_timestamp[:16])
                else:
                    st.metric("🕐 Latest Data", "Unknown")
        
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
            
            st.dataframe(categories_df, use_container_width=True)
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
                        st.metric("Min Value", f"{df['Value'].min():.1f}")
                        st.metric("Max Value", f"{df['Value'].max():.1f}")
                        st.metric("Average", f"{df['Value'].mean():.1f}")
                        st.metric("Properties", len(df))
                        
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
                
                # Show data info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Rows", len(df))
                with col2:
                    st.metric("Columns", len(df.columns))
                with col3:
                    if 'timestamp' in df.columns:
                        st.metric("Timestamp", df['timestamp'].iloc[0] if not df.empty else "N/A")
                
                # Display data
                st.dataframe(df, use_container_width=True)
                
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