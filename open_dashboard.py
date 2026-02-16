#!/usr/bin/env python3
"""
Open SignalEngine Dashboard in default browser
"""
import webbrowser
import os
import sys

def main():
    dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard.html')

    if not os.path.exists(dashboard_path):
        print("❌ dashboard.html not found!")
        print("Make sure you're running this from the SignalEngine directory.")
        sys.exit(1)

    # Convert to file:// URL
    file_url = f'file://{os.path.abspath(dashboard_path)}'

    print("🚀 Opening SignalEngine Dashboard...")
    print(f"📁 File: {dashboard_path}")
    print("🌐 Make sure the API server is running on http://localhost:8000")

    # Open in default browser
    webbrowser.open(file_url)

if __name__ == "__main__":
    main()