#!/usr/bin/env python3
"""
Simple script to run the Flask webapp.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp.app import app

if __name__ == '__main__':
    print("Starting Backtesting Engine...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)

