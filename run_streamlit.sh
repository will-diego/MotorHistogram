#!/bin/bash

# Motor Data Analysis - Streamlit Dashboard Launcher

echo "🚗 Starting Motor Data Analysis Dashboard..."
echo "📊 Streamlit Web Application"
echo ""

# Add Python user bin directory to PATH
export PATH="/Users/willdiego/Library/Python/3.9/bin:$PATH"

# Check if streamlit is available
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found in PATH"
    echo "💡 Try running: pip3 install -r requirements.txt"
    exit 1
fi

# Check if requirements are installed
echo "🔍 Checking dependencies..."
python3 -c "import streamlit, plotly, pandas, matplotlib, numpy" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ All dependencies found"
else
    echo "⚠️  Some dependencies missing, installing..."
    pip3 install -r requirements.txt
fi

echo ""
echo "🌐 Starting Streamlit dashboard..."
echo "📱 Your browser should open automatically"
echo "🔗 If not, go to: http://localhost:8501"
echo ""
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

# Start Streamlit
streamlit run streamlit_app.py 