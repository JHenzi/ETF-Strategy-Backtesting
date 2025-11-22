#!/usr/bin/env python3
"""
Simple script to run the Flask webapp.
"""
import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp.app import app

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Stock/ETF Backtesting Engine web server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on (default: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print("Starting Backtesting Engine...")
    print(f"Open http://localhost:{args.port} in your browser")
    print(f"Running on port {args.port} (use --port to change)")
    
    app.run(debug=args.debug, host=args.host, port=args.port)

