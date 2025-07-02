import requests
import csv
import re
import json
import sys
import argparse

# === CONFIG ===
import os
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "your_api_key_here")
PROJECT_ID = os.getenv("POSTHOG_PROJECT_ID", "113002")
DEFAULT_PERSON_ID = "01977b53-4d47-73f1-bafc-b30395922351"  # Default person ID
DEFAULT_SESSION_ID = "0197a378-6343-73cc-af1e-873f9e6f8fb7"  # Default session ID
EVENT_NAME = "Motor Data"  # Event name - always Motor Data
INSTANCE_URL = "https://us.posthog.com"

# === PARSE COMMAND LINE ARGUMENTS ===
parser = argparse.ArgumentParser(description='Download Motor Data events from PostHog for a specific person')
parser.add_argument('--person-id', '-p', 
                   default=DEFAULT_PERSON_ID,
                   help=f'Person ID to fetch Motor Data for (default: {DEFAULT_PERSON_ID})')
parser.add_argument('--session-id', '-s',
                   default=DEFAULT_SESSION_ID, 
                   help=f'Session ID (optional, default: {DEFAULT_SESSION_ID})')
parser.add_argument('--timestamp', '-t',
                   help='Specific timestamp to fetch (ISO format, e.g., 2024-01-15T10:30:00Z)')
parser.add_argument('--interactive', '-i',
                   action='store_true',
                   help='Interactive mode - prompt for person ID and event selection')
parser.add_argument('--list-events', '-l',
                   action='store_true',
                   help='List all Motor Data events for the person with timestamps')

args = parser.parse_args()

# === DETERMINE PERSON ID ===
if args.interactive:
    print("🔧 Interactive mode - enter person details:")
    PERSON_ID = input(f"Enter Person ID (default: {DEFAULT_PERSON_ID}): ").strip()
    if not PERSON_ID:
        PERSON_ID = DEFAULT_PERSON_ID
    
    SESSION_ID = input(f"Enter Session ID (optional, default: {DEFAULT_SESSION_ID}): ").strip()
    if not SESSION_ID:
        SESSION_ID = DEFAULT_SESSION_ID
else:
    PERSON_ID = args.person_id
    SESSION_ID = args.session_id if args.session_id and args.session_id.strip() else None

TARGET_TIMESTAMP = args.timestamp

print(f"🎯 Fetching Motor Data events for Person ID: {PERSON_ID}")
print(f"📋 Session ID: {SESSION_ID}")
if TARGET_TIMESTAMP:
    print(f"🕒 Target Timestamp: {TARGET_TIMESTAMP}")
elif args.list_events:
    print("📋 Will list all available Motor Data events")
print()

# === DISCOVER PROJECTS FIRST ===
headers = {
    "Authorization": f"Bearer {POSTHOG_API_KEY}",
    "Content-Type": "application/json"
}

# Skip project discovery to avoid permission issues - we already know our project ID
print("🔍 Using configured project ID (skipping discovery to avoid permission issues)...")
print(f"✅ Using PROJECT_ID: {PROJECT_ID}")

# Commenting out project discovery as it requires additional permissions
# and we already have the correct project ID configured
"""
print("🔍 Discovering available projects...")
try:
    response = requests.get(f"{INSTANCE_URL}/api/projects/", headers=headers)
    if response.status_code == 200:
        projects = response.json()
        print(f"✅ Found {len(projects['results']) if isinstance(projects, dict) and 'results' in projects else len(projects)} projects:")
        
        project_list = projects['results'] if isinstance(projects, dict) and 'results' in projects else projects
        for i, project in enumerate(project_list[:5]):  # Show first 5 projects
            project_id = project.get('id', 'Unknown')
            project_name = project.get('name', 'Unnamed')
            print(f"   {i+1}. ID: {project_id} | Name: {project_name}")
            
        # Try to use the first project if current one doesn't work
        if project_list and PROJECT_ID not in [p.get('id', '') for p in project_list]:
            suggested_project = project_list[0]['id']
            print(f"⚠️  Current PROJECT_ID '{PROJECT_ID}' not found in available projects")
            print(f"💡 Trying with first available project: {suggested_project}")
            PROJECT_ID = suggested_project
        else:
            print(f"✅ Current PROJECT_ID '{PROJECT_ID}' found in available projects")
    else:
        print(f"❌ Failed to fetch projects: {response.status_code}")
        if response.status_code == 403:
            print("   API key may not have project read permissions")
except Exception as e:
    print(f"❌ Error fetching projects: {str(e)}")
"""

print()

# === FETCH EVENT DATA ===

def fetch_motor_data_events(person_id, session_id=None, limit=200):
    """Fetch all Motor Data events for a person"""
    base_params = f"event={EVENT_NAME}&limit={limit}&order_by=-timestamp"
    
    endpoints_to_try = [
        f"{INSTANCE_URL}/api/projects/{PROJECT_ID}/events/?person_id={person_id}&{base_params}",
        f"{INSTANCE_URL}/api/projects/{PROJECT_ID}/events/?distinct_id={person_id}&{base_params}",
    ]
    
    # Add session ID filter if provided
    if session_id:
        # Try different approaches for session filtering
        import urllib.parse
        
        # Method 1: Use properties filter
        session_filter = urllib.parse.quote('{"$session_id":"' + session_id + '"}')
        session_params1 = f"event={EVENT_NAME}&limit={limit}&order_by=-timestamp&properties={session_filter}"
        
        # Method 2: Use direct session_id parameter (if PostHog supports it)
        session_params2 = f"event={EVENT_NAME}&limit={limit}&order_by=-timestamp&session_id={session_id}"
        
        # Method 3: Use $session_id as a direct parameter
        session_params3 = f"event={EVENT_NAME}&limit={limit}&order_by=-timestamp&%24session_id={session_id}"
        
        session_endpoints = [
            f"{INSTANCE_URL}/api/projects/{PROJECT_ID}/events/?person_id={person_id}&{session_params1}",
            f"{INSTANCE_URL}/api/projects/{PROJECT_ID}/events/?distinct_id={person_id}&{session_params1}",
            f"{INSTANCE_URL}/api/projects/{PROJECT_ID}/events/?person_id={person_id}&{session_params2}",
            f"{INSTANCE_URL}/api/projects/{PROJECT_ID}/events/?distinct_id={person_id}&{session_params2}",
            f"{INSTANCE_URL}/api/projects/{PROJECT_ID}/events/?person_id={person_id}&{session_params3}",
            f"{INSTANCE_URL}/api/projects/{PROJECT_ID}/events/?distinct_id={person_id}&{session_params3}",
        ]
        
        endpoints_to_try = session_endpoints + endpoints_to_try  # Try session-filtered queries first
    
    for url in endpoints_to_try:
        print(f"🔍 Trying endpoint: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"   ✅ Success! Response type: {type(response_data)}")
                
                motor_data_events = []
                all_events = []
                
                # Handle different response formats and collect all events
                if isinstance(response_data, dict):
                    if 'results' in response_data:
                        all_events = response_data['results']
                        
                        # Check if there are more pages
                        next_url = response_data.get('next')
                        page_count = 1
                        
                        # Fetch additional pages if available (up to 5 pages to avoid infinite loops)
                        while next_url and page_count < 5:
                            print(f"   📄 Fetching page {page_count + 1}...")
                            try:
                                next_response = requests.get(next_url, headers=headers)
                                if next_response.status_code == 200:
                                    next_data = next_response.json()
                                    if 'results' in next_data:
                                        all_events.extend(next_data['results'])
                                        next_url = next_data.get('next')
                                        page_count += 1
                                    else:
                                        break
                                else:
                                    break
                            except:
                                break
                        
                        print(f"   📊 Total events across {page_count} pages: {len(all_events)}")
                        
                elif isinstance(response_data, list):
                    all_events = response_data
                
                # Filter for Motor Data events specifically
                for event in all_events:
                    if event.get('event') == EVENT_NAME:
                        motor_data_events.append(event)
                
                print(f"   🔍 Motor Data events found: {len(motor_data_events)}")
                
                # Post-filter by session ID if provided
                if session_id and motor_data_events:
                    original_count = len(motor_data_events)
                    motor_data_events = [
                        event for event in motor_data_events 
                        if event.get('properties', {}).get('$session_id') == session_id
                    ]
                    filtered_count = len(motor_data_events)
                    print(f"   🔍 Session filtering: {original_count} → {filtered_count} events (session: {session_id})")
                
                if motor_data_events:
                    print(f"   🎯 Found {len(motor_data_events)} {EVENT_NAME} events!")
                    return motor_data_events, url
                else:
                    print(f"   ⚠️  No {EVENT_NAME} events found")
            else:
                print(f"   ❌ Error: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error detail: {error_detail}")
                except:
                    print(f"   Error text: {response.text[:200]}")
                    
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
        
        print()
    
    return [], None

# Fetch all Motor Data events for the person
motor_events, successful_url = fetch_motor_data_events(PERSON_ID, SESSION_ID)

# === SELECT AND PROCESS ALL EVENTS ===
if not motor_events:
    print("❌ Failed to fetch Motor Data events. Please check:")
    print("1. API key permissions (needs 'query:read' scope)")
    print("2. Project ID")
    print("3. Person ID") 
    print("4. Event name ('Motor Data')")
    print("5. Network connectivity")
    exit(1)

print(f"✅ Successfully fetched {len(motor_events)} Motor Data events from: {successful_url}")

# === FILTER BY SPECIFIC TIMESTAMP IF PROVIDED ===
if TARGET_TIMESTAMP:
    print(f"🔍 Filtering for specific timestamp: {TARGET_TIMESTAMP}")
    original_count = len(motor_events)
    
    # Filter events to find the one with matching timestamp
    filtered_events = []
    for event in motor_events:
        event_timestamp = event.get('timestamp', '')
        # Try exact match first
        if event_timestamp == TARGET_TIMESTAMP:
            filtered_events.append(event)
        # Also try partial match (in case of precision differences)
        elif TARGET_TIMESTAMP in event_timestamp or event_timestamp.startswith(TARGET_TIMESTAMP[:19]):
            filtered_events.append(event)
    
    if filtered_events:
        motor_events = filtered_events
        print(f"✅ Found {len(filtered_events)} event(s) matching timestamp {TARGET_TIMESTAMP}")
    else:
        print(f"❌ No event found with timestamp matching: {TARGET_TIMESTAMP}")
        print(f"📋 Available timestamps from {original_count} events:")
        for i, event in enumerate(motor_events[:10]):  # Show first 10
            print(f"   - {event.get('timestamp', 'Unknown')}")
        if len(motor_events) > 10:
            print(f"   ... and {len(motor_events) - 10} more")
        exit(1)

# === LIST EVENTS IF REQUESTED ===
if args.list_events:
    print(f"\n📋 Found {len(motor_events)} Motor Data events:")
    for i, event in enumerate(motor_events):
        timestamp = event.get('timestamp', 'Unknown')
        properties_count = len(event.get('properties', {}))
        session_id = event.get('properties', {}).get('$session_id', 'Unknown')
        print(f"   {i+1}. {timestamp} (Session: {session_id}, {properties_count} properties)")
    exit(0)

# === PROCESS ALL EVENTS ===
all_power_data = []
all_torque_data = []
all_motor_temp_data = []
all_mosfet_temp_data = []
all_mosfet_cooldown_data = []
all_motor_cooldown_data = []

for data in motor_events:
    event_properties = data.get("properties", {})
    timestamp = data.get("timestamp", "")
    if not event_properties:
        continue
    # Initialize categorized dictionaries for this event
    power_data = {"timestamp": timestamp}
    torque_data = {"timestamp": timestamp}
    motor_temp_data = {"timestamp": timestamp}
    mosfet_temp_data = {"timestamp": timestamp}
    mosfet_cooldown_data = {"timestamp": timestamp}
    motor_cooldown_data = {"timestamp": timestamp}
    # Categorize properties
    for key, value in event_properties.items():
        key_lower = key.lower()
        if key_lower.startswith('power'):
            power_data[key] = value
        elif key_lower.startswith('torque'):
            torque_data[key] = value
        elif 'motortemp' in key_lower:
            motor_temp_data[key] = value
        elif 'mosfettemp' in key_lower and 'cooldown' not in key_lower:
            mosfet_temp_data[key] = value
        elif 'mosfet' in key_lower and 'cooldown' in key_lower:
            mosfet_cooldown_data[key] = value
        elif 'cooldownmosfet' in key_lower:
            mosfet_cooldown_data[key] = value
        elif 'motor' in key_lower and 'cooldown' in key_lower:
            motor_cooldown_data[key] = value
        elif 'cooldownmotor' in key_lower:
            motor_cooldown_data[key] = value
    # Append to lists if there is data beyond timestamp
    if len(power_data) > 1:
        all_power_data.append(power_data)
    if len(torque_data) > 1:
        all_torque_data.append(torque_data)
    if len(motor_temp_data) > 1:
        all_motor_temp_data.append(motor_temp_data)
    if len(mosfet_temp_data) > 1:
        all_mosfet_temp_data.append(mosfet_temp_data)
    if len(mosfet_cooldown_data) > 1:
        all_mosfet_cooldown_data.append(mosfet_cooldown_data)
    if len(motor_cooldown_data) > 1:
        all_motor_cooldown_data.append(motor_cooldown_data)

# === WRITE ALL EVENTS TO CSV FILES ===
def write_all_events_to_csv(filename, data_list):
    if not data_list:
        print(f"⚠️  No data for {filename}")
        return
    # Collect all possible fieldnames
    fieldnames = set()
    for row in data_list:
        fieldnames.update(row.keys())
    fieldnames = sorted(fieldnames)
    with open(filename, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data_list:
            writer.writerow(row)
    print(f"✅ Saved {len(data_list)} events to {filename}")

write_all_events_to_csv("csv_outputs/posthog_event_power.csv", all_power_data)
write_all_events_to_csv("csv_outputs/posthog_event_torque.csv", all_torque_data)
write_all_events_to_csv("csv_outputs/posthog_event_motor_temp.csv", all_motor_temp_data)
write_all_events_to_csv("csv_outputs/posthog_event_mosfet_temp.csv", all_mosfet_temp_data)
write_all_events_to_csv("csv_outputs/posthog_event_mosfet_cooldown.csv", all_mosfet_cooldown_data)
write_all_events_to_csv("csv_outputs/posthog_event_motor_cooldown.csv", all_motor_cooldown_data)

# === SUMMARY ===
total_properties = sum(len(event.get('properties', {})) for event in motor_events)
categorized_properties = sum(len(row)-1 for row in all_power_data + all_torque_data + all_motor_temp_data + all_mosfet_temp_data + all_mosfet_cooldown_data + all_motor_cooldown_data)
print(f"\n📊 Summary: {categorized_properties}/{total_properties} properties categorized across all events")
