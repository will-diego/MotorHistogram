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
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #1f2937; font-size: 3rem; margin-bottom: 0.5rem;">🚗 Motor Data Analysis</h1>
        <p style="color: #6b7280; font-size: 1.2rem; margin-bottom: 1rem;">Secure Dashboard Access</p>
        <div style="background: #f3f4f6; padding: 1rem; border-radius: 0.5rem; margin: 1rem auto; max-width: 600px;">
            <p style="color: #4b5563; margin: 0;">Welcome to the Motor Data Analysis Dashboard! This secure platform allows you to:</p>
            <ul style="text-align: left; color: #4b5563; margin: 1rem 0;">
                <li>📊 View real-time motor performance data</li>
                <li>📈 Analyze historical trends and patterns</li>
                <li>🔍 Generate detailed performance reports</li>
                <li>⚡ Monitor power and temperature metrics</li>
            </ul>
            <p style="color: #4b5563; margin: 0;">Please log in below to access these features.</p>
        </div>
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
    """Load available CSV data from master file"""
    master_csv_file = "csv_outputs/motor_data_master.csv"
    
    # Check if master CSV exists and has content
    if not os.path.exists(master_csv_file) or os.path.getsize(master_csv_file) < 100:
        return {}
    
    try:
        df = pd.read_csv(master_csv_file)
        if df.empty:
            return {}
        
        # Categorize the data by property types
        categorized_data = {}
        
        # Get all columns except timestamp
        all_columns = [col for col in df.columns if col != 'timestamp']
        
        # Create category dataframes
        power_cols = [col for col in all_columns if col.lower().startswith('power')]
        torque_cols = [col for col in all_columns if col.lower().startswith('torque')]
        motor_temp_cols = [col for col in all_columns if 'motortemp' in col.lower()]
        mosfet_temp_cols = [col for col in all_columns if 'mosfettemp' in col.lower() and 'cooldown' not in col.lower()]
        mosfet_cooldown_cols = [col for col in all_columns if ('mosfet' in col.lower() and 'cooldown' in col.lower()) or 'cooldownmosfet' in col.lower()]
        motor_cooldown_cols = [col for col in all_columns if ('motor' in col.lower() and 'cooldown' in col.lower()) or 'cooldownmotor' in col.lower()]
        
        # Create category dataframes with timestamp
        if power_cols:
            categorized_data['power'] = df[['timestamp'] + power_cols].dropna(how='all', subset=power_cols)
        if torque_cols:
            categorized_data['torque'] = df[['timestamp'] + torque_cols].dropna(how='all', subset=torque_cols)
        if motor_temp_cols:
            categorized_data['motor_temp'] = df[['timestamp'] + motor_temp_cols].dropna(how='all', subset=motor_temp_cols)
        if mosfet_temp_cols:
            categorized_data['mosfet_temp'] = df[['timestamp'] + mosfet_temp_cols].dropna(how='all', subset=mosfet_temp_cols)
        if mosfet_cooldown_cols:
            categorized_data['mosfet_cooldown'] = df[['timestamp'] + mosfet_cooldown_cols].dropna(how='all', subset=mosfet_cooldown_cols)
        if motor_cooldown_cols:
            categorized_data['motor_cooldown'] = df[['timestamp'] + motor_cooldown_cols].dropna(how='all', subset=motor_cooldown_cols)
        
        return categorized_data
        
    except Exception as e:
        st.warning(f"Could not load master CSV: {e}")
        return {}

def load_histogram_data():
    """Load histogram data files"""
    data = {}
    
    # Try multiple patterns to find histogram CSV files
    patterns = [
        "histogram_outputs/*_numeric_values.csv",
        "./histogram_outputs/*_numeric_values.csv",
        os.path.join(os.getcwd(), "histogram_outputs", "*_numeric_values.csv")
    ]
    
    csv_files = []
    for pattern in patterns:
        files = glob.glob(pattern)
        if files:
            csv_files = files
            break
    
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
            # Only show warning if we're in debug mode (remove for production)
            pass
    
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

def generate_charts_from_master_csv():
    """Generate charts directly from master CSV as backup method"""
    try:
        master_csv = "csv_outputs/motor_data_master.csv"
        if not os.path.exists(master_csv):
            return False, "Master CSV not found"
        
        df = pd.read_csv(master_csv)
        if df.empty:
            return False, "Master CSV is empty"
        
        # Use latest row
        latest_row = df.iloc[-1]
        
        # Define categories
        categories = {
            'power': ['power'],
            'torque': ['torque'], 
            'motor_temp': ['motortemperature'],
            'mosfet_temp': ['mosfettemperature']
        }
        
        charts_created = 0
        
        # Create output directory
        os.makedirs("histogram_outputs", exist_ok=True)
        
        for category, keywords in categories.items():
            # Find matching columns
            category_cols = [col for col in df.columns 
                           if any(keyword.lower() in col.lower() for keyword in keywords)
                           and col != 'timestamp']
            
            if not category_cols:
                continue
                
            # Extract numeric data
            import re
            property_data = []
            for col in category_cols:
                try:
                    value = float(latest_row[col])
                    if not pd.isna(value):
                        if 'torque' in col.lower():
                            match = re.search(r'(\d{2})$', col)
                            if match:
                                numeric_label = int(match.group(1))
                                property_data.append((numeric_label, value, col))
                        else:
                            match = re.search(r'(\d{3})$', col) 
                            if match:
                                numeric_label = int(match.group(1))
                                property_data.append((numeric_label, value, col))
                except (ValueError, TypeError):
                    continue
            
            if property_data:
                # Sort and create CSV
                property_data.sort(key=lambda x: x[0])
                
                # Create CSV file
                csv_file = f"histogram_outputs/{category}_numeric_values.csv"
                chart_df = pd.DataFrame(property_data, columns=['Numeric_Label', 'Value', 'Original_Property'])
                chart_df.to_csv(csv_file, index=False)
                charts_created += 1
        
        return True, f"Generated {charts_created} chart datasets directly from master CSV"
        
    except Exception as e:
        return False, f"Error generating charts from master CSV: {str(e)}"

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
                    properties_count = int(properties_match.group(1)) if properties_match else 0
                    
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
                    'properties_count': 0,
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
    """Fetch data for a specific event timestamp and append to master CSV"""
    try:
        import pandas as pd
        
        # Ensure output directories exist
        os.makedirs("csv_outputs", exist_ok=True)
        os.makedirs("histogram_outputs", exist_ok=True)
        
        # Use sys.executable to ensure same Python environment
        cmd = [sys.executable, "-W", "ignore", "scripts/GetPostHog.py", "-p", person_id, "-t", timestamp, "-s", ""]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".", timeout=60)
        
        if result.returncode == 0:
            # Read the generated CSV files and combine into one row for master CSV
            master_csv_file = "csv_outputs/motor_data_master.csv"
            event_data = {"timestamp": timestamp}
            
            # Read all category files and combine properties
            for category in ['power', 'torque', 'motor_temp', 'mosfet_temp', 'mosfet_cooldown', 'motor_cooldown']:
                csv_file = f"csv_outputs/posthog_event_{category}.csv"
                if os.path.exists(csv_file):
                    try:
                        df = pd.read_csv(csv_file)
                        if not df.empty and len(df) > 0:
                            # Add all properties from this category to the event data
                            row_data = df.iloc[0].to_dict()
                            for key, value in row_data.items():
                                if key != 'timestamp' and pd.notna(value):
                                    event_data[key] = value
                        # Clean up the category file
                        os.remove(csv_file)
                    except Exception as e:
                        st.warning(f"Warning: Could not read {csv_file}: {str(e)}")
            
            # Append to master CSV
            if len(event_data) > 1:  # More than just timestamp
                new_df = pd.DataFrame([event_data])
                
                if os.path.exists(master_csv_file):
                    try:
                        existing_df = pd.read_csv(master_csv_file)
                        # Combine and remove duplicates
                        combined_df = pd.concat([existing_df, new_df], ignore_index=True, sort=False)
                        combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
                        combined_df.to_csv(master_csv_file, index=False)
                    except Exception as e:
                        st.warning(f"Error updating master CSV, creating new one: {str(e)}")
                        new_df.to_csv(master_csv_file, index=False)
                else:
                    new_df.to_csv(master_csv_file, index=False)
                
                st.success("✅ Event data downloaded and added to master dataset!")
                return True, "Event data fetched successfully!"
            else:
                st.warning("⚠️ No event data found to add")
                return False, "No data found"
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
        
        # Check if master CSV exists
        master_csv = "csv_outputs/motor_data_master.csv"
        if not os.path.exists(master_csv):
            st.error("❌ Master CSV file not found. Please download some data first.")
            return False, "Master CSV not found"
        
        with st.spinner("Generating histograms..."):
            # Use sys.executable to ensure same Python environment
            result = subprocess.run(
                [sys.executable, "-W", "ignore", "scripts/create_histograms.py"], 
                capture_output=True, text=True, check=True
            )
            
            # Show debug output
            if result.stdout:
                st.text("Script output:")
                st.code(result.stdout, language="text")
            
            # Check if files were actually created
            hist_files = glob.glob("histogram_outputs/*.png")
            csv_files = glob.glob("histogram_outputs/*.csv")
            
            if hist_files or csv_files:
                st.success(f"✅ Generated {len(hist_files)} images and {len(csv_files)} data files!")
            else:
                st.warning("⚠️ Script completed but no output files found.")
                
        return True, result.stdout
        
    except subprocess.CalledProcessError as e:
        st.error(f"❌ Error generating histograms (exit code {e.returncode}):")
        if e.stdout:
            st.text("Script output:")
            st.code(e.stdout, language="text")
        if e.stderr:
            st.text("Error details:")
            st.code(e.stderr, language="text")
        return False, e.stderr
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return False, str(e)

def fetch_bulk_events(person_id, event_count=None):
    """Fetch multiple events and combine them into a single dataset (only events with 160+ properties)"""
    try:
        import pandas as pd
        import requests
        import os
        
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
        
        # Filter events to only include those with 160-170 properties (quality control)
        quality_events = [event for event in events if 160 <= event['properties_count'] <= 170]
        
        if not quality_events:
            return False, f"No high-quality events found (need 160-170 properties). Found {len(events)} events but none were in the optimal range."
        
        if event_count:
            # Take only the requested number of recent quality events
            selected_events = quality_events[:event_count]
            action_text = f"last {event_count} quality"
            # Show filtering info specific to the requested count
            st.info(f"🔍 Quality filter: Selected {len(selected_events)} quality events from {len(quality_events)} available events with 160-170 properties")
        else:
            # Take all quality events
            selected_events = quality_events
            action_text = f"all {len(quality_events)} quality"
            # Show filtering info for all events
            if len(quality_events) < len(events):
                st.info(f"🔍 Quality filter: Using {len(quality_events)} events with 160-170 properties (filtered out {len(events) - len(quality_events)} events outside optimal range)")
        
        # Initialize combined data structures with timestamps
        all_events_data = []
        
        # Download each event and collect data immediately
        success_count = 0
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, event in enumerate(selected_events):
            progress = (i + 1) / len(selected_events)
            progress_bar.progress(progress)
            status_text.text(f"Downloading event {i+1}/{len(selected_events)}: {event['timestamp'][:16]} ({event['properties_count']} properties)...")
            
            # Download individual event using the working GetPostHog.py script
            event_cmd = [sys.executable, "-W", "ignore", "scripts/GetPostHog.py", "-p", person_id, "-t", event['timestamp'], "-s", ""]
            event_result = subprocess.run(event_cmd, capture_output=True, text=True, cwd=".", timeout=60)
            
            if event_result.returncode == 0:
                # Immediately read and backup the generated CSV files before the next download overwrites them
                event_data = {'timestamp': event['timestamp'], 'properties': {}}
                
                for category in ['power', 'torque', 'motor_temp', 'mosfet_temp', 'mosfet_cooldown', 'motor_cooldown']:
                    csv_file = f"csv_outputs/posthog_event_{category}.csv"
                    if os.path.exists(csv_file):
                        try:
                            df = pd.read_csv(csv_file)
                            if not df.empty and len(df) > 0:
                                # Convert the row data back to properties format
                                row_data = df.iloc[0].to_dict()
                                for key, value in row_data.items():
                                    if key != 'timestamp' and pd.notna(value):
                                        event_data['properties'][key] = value
                        except Exception as e:
                            st.warning(f"Warning: Could not read {csv_file} for event {i+1}: {str(e)}")
                
                if event_data['properties']:
                    all_events_data.append(event_data)
                    success_count += 1
                else:
                    st.warning(f"No data found for event {i+1}")
            else:
                st.warning(f"Failed to download event {i+1}: {event_result.stderr}")
                continue
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        if success_count > 0:
            # Process and append all event data to master CSV
            status_text.text("Processing and appending data to master CSV...")
            
            master_csv_file = "csv_outputs/motor_data_master.csv"
            new_rows = []
            
            # Process each event's properties into a single row
            for event_info in all_events_data:
                timestamp = event_info['timestamp']
                properties = event_info['properties']
                
                # Create a single row with timestamp and all properties
                row = {"timestamp": timestamp}
                row.update(properties)  # Add all properties to the row
                new_rows.append(row)
            
            if new_rows:
                new_df = pd.DataFrame(new_rows)
                
                # Check if master CSV exists and append, otherwise create new
                if os.path.exists(master_csv_file):
                    try:
                        existing_df = pd.read_csv(master_csv_file)
                        # Combine existing and new data
                        combined_df = pd.concat([existing_df, new_df], ignore_index=True, sort=False)
                        # Remove duplicates based on timestamp
                        combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
                        combined_df.to_csv(master_csv_file, index=False)
                        st.info(f"📊 Appended {len(new_rows)} new events to master CSV (total: {len(combined_df)} events)")
                    except Exception as e:
                        st.warning(f"Error reading existing CSV, creating new one: {str(e)}")
                        new_df.to_csv(master_csv_file, index=False)
                        st.info(f"📊 Created new master CSV with {len(new_rows)} events")
                else:
                    # Create new master CSV
                    new_df.to_csv(master_csv_file, index=False)
                    st.info(f"📊 Created new master CSV with {len(new_rows)} events")
                
                # Clean up old category-specific CSV files
                for category in ['power', 'torque', 'motor_temp', 'mosfet_temp', 'mosfet_cooldown', 'motor_cooldown']:
                    old_csv = f"csv_outputs/posthog_event_{category}.csv"
                    if os.path.exists(old_csv):
                        try:
                            os.remove(old_csv)
                        except:
                            pass  # Ignore errors when cleaning up
                
                # Show total properties info
                total_properties = sum(len(row) - 1 for row in new_rows)  # -1 for timestamp
                st.info(f"📈 Added {total_properties} total properties from {success_count} events to master dataset")
            
            status_text.empty()
            st.success(f"✅ Successfully added {success_count}/{len(selected_events)} quality events to master CSV!")
            return True, f"Downloaded and added {action_text} events successfully ({success_count}/{len(selected_events)} succeeded)"
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
    
    # Add adaptive theme CSS that works in both light and dark modes
    st.markdown("""
    <style>
    /* Improve readability and accessibility */
    .stButton button {
        border: 1px solid #e0e0e0;
    }
    
    /* Ensure good contrast for metrics */
    .stMetric {
        background-color: var(--background-color);
        border: 1px solid var(--border-color);
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    /* Ensure tables are readable */
    .stDataFrame {
        border: 1px solid var(--border-color);
    }
    
    /* Make sure text is always readable */
    .stMarkdown, .stText {
        color: var(--text-color);
    }
    
    /* Ensure selectboxes and inputs are visible */
    .stSelectbox > div > div, .stTextInput > div > div > input {
        border: 1px solid #ccc;
    }
    
    /* Improve tab visibility */
    .stTabs [data-baseweb="tab-list"] button {
        border: 1px solid #ddd;
        margin-right: 2px;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        border-bottom: 2px solid #1f77b4;
        font-weight: bold;
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
            person_id = st.text_input("Person ID", value="0197a976-e0dd-707e-8eef-104d3d3a24a5", label_visibility="collapsed")
            
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
            # Try the main histogram generation script first
            success, output = run_histogram_generation()
            
            # If that fails, try the backup method
            if not success:
                st.info("🔄 Trying backup chart generation method...")
                backup_success, backup_output = generate_charts_from_master_csv()
                if backup_success:
                    st.success(f"✅ {backup_output}")
                    success = True
                else:
                    st.error(f"❌ Backup method also failed: {backup_output}")
            
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
            
            # Convert the parsed events to a more structured format (show all events)
            formatted_events = []
            all_events = events  # Show all events, not just those with specific property counts
            
            for i, event in enumerate(all_events, 1):
                formatted_events.append({
                    'number': str(i),
                    'timestamp': event['timestamp'],
                    'session_id': event['session_id'],
                    'properties_count': event['properties_count'],
                    'details': event.get('line', '')
                })
            
            # Show event count info
            st.info(f"📋 Showing all {len(all_events)} available Motor Data events")
            
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
            st.markdown("*Download multiple events at once for comprehensive analysis*")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("📥 Get Last 5 Events", use_container_width=True, type="secondary", 
                           help="Download and combine the 5 most recent events"):
                    with st.spinner("📥 Downloading last 5 events..."):
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
                if st.button("📥 Get All Events", use_container_width=True, type="secondary",
                           help="Download all available events (may take several minutes)"):
                    # Show confirmation dialog
                    if 'confirm_all_events' not in st.session_state:
                        st.session_state.confirm_all_events = True
                        st.warning("⚠️ This will download ALL events and may take several minutes. Click again to confirm.")
                    else:
                        del st.session_state.confirm_all_events
                        with st.spinner("📥 Downloading all events... This may take several minutes..."):
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
                # Get current page events
                current_page_timestamps = [event['timestamp'] for event in current_events]
                events_on_page = len(current_page_timestamps)
                
                if events_on_page > 0:
                    if st.button(f"📥 Get Current Page ({events_on_page} events)", use_container_width=True, type="secondary",
                               help=f"Download all {events_on_page} events from the current page"):
                        with st.spinner(f"📥 Downloading {events_on_page} events from current page..."):
                            # Use bulk download approach for consistency
                            success_count = 0
                            for event in current_events:
                                event_success, _ = fetch_specific_event_data(person_id, event['timestamp'])
                                if event_success:
                                    success_count += 1
                        
                        if success_count > 0:
                            st.success(f"✅ Downloaded {success_count}/{events_on_page} events from current page!")
                            st.session_state.show_event_browser = False
                            if 'event_page' in st.session_state:
                                del st.session_state.event_page  # Reset pagination
                            st.rerun()
                        else:
                            st.error("❌ Failed to download any events from current page")
                else:
                    st.button("📥 Current Page", disabled=True, use_container_width=True, 
                            help="No events on current page")

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
            # Get master CSV file size
            master_csv_file = "csv_outputs/motor_data_master.csv"
            master_size = 0
            try:
                if os.path.exists(master_csv_file):
                    master_size = os.path.getsize(master_csv_file) / 1024
            except (FileNotFoundError, OSError):
                master_size = 0
            
            categories_df = pd.DataFrame([
                {
                    "Category": category.replace("_", " ").title(),
                    "Properties": len(df.columns) - 1,  # -1 for timestamp
                    "Rows": len(df),
                    "Master CSV Size": f"{master_size:.1f} KB" if master_size > 0 else "N/A"
                }
                for category, df in csv_data.items()
            ])
            
            st.dataframe(categories_df, use_container_width=True, hide_index=True)
        else:
            st.info("No CSV data available")
    
    with tab2:
        st.header("📈 Interactive Data Visualization")
        
        if histogram_data:
            # Display all charts automatically
            for category in histogram_data.keys():
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
            st.warning("⚠️ No interactive histogram data available. Generate charts using the sidebar.")
            
            # Show static images if available as fallback
            png_patterns = [
                "histogram_outputs/*.png",
                "./histogram_outputs/*.png",
                os.path.join(os.getcwd(), "histogram_outputs", "*.png")
            ]
            
            png_files = []
            for pattern in png_patterns:
                files = glob.glob(pattern)
                if files:
                    png_files = files
                    break
            
            if png_files:
                st.info("📸 Static histogram images found:")
                for png_file in sorted(png_files):
                    category = os.path.basename(png_file).replace("_numeric_values.png", "")
                    st.subheader(f"{category.replace('_', ' ').title()}")
                    try:
                        st.image(png_file)
                    except Exception as e:
                        st.error(f"Could not load image: {png_file}")
            else:
                st.info("🔧 No charts found. Click 'Generate Charts' in the sidebar to create visualizations.")
    
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