#!/bin/bash

# Start Streamlit in the background
# We set baseUrlPath to /lab so Streamlit knows it's serving from a subdirectory
streamlit run chat_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --server.baseUrlPath=/lab &

# Start Nginx in the foreground
nginx -g 'daemon off;'
