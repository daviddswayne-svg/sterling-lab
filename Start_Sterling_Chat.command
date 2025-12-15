#!/bin/bash
# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to that directory
cd "$DIR"

# Activate Virtual Environment
source venv/bin/activate

# Launch App
echo "Starting Sterling Lab Chat..."
echo "Press Ctrl+C to stop."
streamlit run chat_app.py
