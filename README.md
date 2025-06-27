# Motor Data Analysis Tool

Download and visualize PostHog Motor Data events with automatic histogram generation.

## 🌐 NEW: Interactive Web Dashboard

**Launch the Streamlit web interface for interactive analysis:**

```bash
# Easy startup script
./run_streamlit.sh

# Or manually:
streamlit run streamlit_app.py
```

**Features:**
- 📊 Interactive charts and visualizations
- 📥 Download data directly from PostHog
- 📈 Real-time histogram generation
- 📋 Raw data exploration
- 💾 Export processed data
- 🔧 Settings and file management

**Access:** Open http://localhost:8501 in your browser

## 📦 Installation

1. **Install Python 3.7+** (if not already installed)
   - Download from [python.org](https://python.org) 
   - Or use package manager: `brew install python3` (Mac), `apt install python3` (Ubuntu)

2. **Install required packages:**
   ```bash
   # Most common
   pip install -r requirements.txt
   
   # If pip not found, try:
   pip3 install -r requirements.txt
   python3 -m pip install -r requirements.txt
   ```

3. **Update your PostHog credentials** in `scripts/GetPostHog.py`:
   - Line 7: Replace `POSTHOG_API_KEY` with your API key
   - Line 8: Replace `PROJECT_ID` with your project ID

## 🚀 Usage

### Step 1: Open Terminal/Command Prompt
- **Mac/Linux**: Open Terminal app
- **Windows**: Open Command Prompt or PowerShell  
- **VS Code**: Open integrated terminal (`View` → `Terminal`)

### Step 2: Navigate to Project Directory
```bash
cd path/to/Make\ Motor\ Histogram
```

### Step 3: Run the Analysis

**Try these Python commands (use whichever works on your system):**

```bash
# Most common (Mac/Linux)
python3 motor_data_analysis.py -t 2025-06-25T21:02:12.715Z

# Alternative (Windows/some Linux distributions)
python motor_data_analysis.py -t 2025-06-25T21:02:12.715Z

# If you get "command not found", try full path:
/usr/bin/python3 motor_data_analysis.py -t 2025-06-25T21:02:12.715Z
```

**In VS Code:** You can also right-click on `motor_data_analysis.py` → "Run Python File in Terminal"

### All Available Options

```bash
# Use default person ID
python3 motor_data_analysis.py

# Specific person ID  
python3 motor_data_analysis.py -p your-person-id-here

# Specific timestamp (copy from PostHog UI, Z suffix optional)
python3 motor_data_analysis.py -t 2025-06-25T21:02:12.715Z
python3 motor_data_analysis.py -t 2025-06-25T21:02:12.715

# Interactive mode - choose from available events
python3 motor_data_analysis.py -i

# List all available events for a person
python3 motor_data_analysis.py -l

# Download data only (skip histogram generation)
python3 motor_data_analysis.py --skip-histograms
```

### Individual Steps (Advanced)
If you need to run steps separately:

```bash
# Step 1: Download data
python3 scripts/GetPostHog.py -t 2025-06-25T21:02:12.715Z

# Step 2: Generate histograms  
python3 scripts/create_histograms.py
```

## 📊 Output

The tool generates:
- **CSV files**: Raw motor data organized by category (power, torque, temperatures)
- **PNG charts**: Histogram visualizations in the `histograms/` folder
- **Data files**: Processed numeric values for each category

## 🔧 Configuration

Edit these values in `GetPostHog.py` for your setup:
- `POSTHOG_API_KEY`: Your PostHog personal API key
- `PROJECT_ID`: Your PostHog project ID
- `DEFAULT_PERSON_ID`: Default person to analyze (optional)

## 📁 Files

- `motor_data_analysis.py` - Main script (complete analysis)
- `GetPostHog.py` - Downloads PostHog data
- `create_histograms.py` - Generates visualizations
- `requirements.txt` - Python dependencies

## 🆘 Troubleshooting

### Python Issues
- **"python3: command not found"**: 
  - Try `python` instead of `python3`
  - Use full path like `/usr/bin/python3` or `/usr/local/bin/python3`
  - On Windows, try `py` command
  - Install Python from python.org if needed

### PostHog API Issues  
- **403 Error**: Check your API key has `query:read` permissions
- **No events found**: Verify person ID and project ID are correct
- **Timestamp not found**: Use `-l` flag to see available timestamps

### Missing Dependencies
- **Module not found**: Run `pip install -r requirements.txt`
- **Permission denied**: Try `pip install --user -r requirements.txt`

## 📋 Requirements

- Python 3.7+
- PostHog account with API access
- Required packages (see requirements.txt) 
