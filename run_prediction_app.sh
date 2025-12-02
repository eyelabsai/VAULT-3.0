#!/bin/bash
#
# ICL Vault Predictor - Launch Web Application
#
# This starts the Streamlit web interface for clinical decision support.
# The app provides lens size recommendations with confidence scores and vault predictions.
#
# Usage: ./run_prediction_app.sh
#

echo ""
echo "========================================================================"
echo "  🎯 ICL VAULT PREDICTOR - WEB APPLICATION"
echo "========================================================================"
echo ""
echo "Starting Streamlit application..."
echo ""
echo "Once started:"
echo "  → The app will open in your browser automatically"
echo "  → URL: http://localhost:8501"
echo "  → Press Ctrl+C to stop the server"
echo ""
echo "========================================================================"
echo ""

# Activate virtual environment
source venv/bin/activate

# Launch Streamlit
streamlit run app.py

