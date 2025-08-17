#!/usr/bin/env python3
"""
Test the dashboard function directly to see if it's working
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Add the current directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def test_dashboard_function():
    """Test the dashboard function directly"""
    try:
        # Import the function from app.py
        from app import get_server_status, extract_public_ip_from_interfaces
        
        print("Testing dashboard function directly:")
        print("=" * 50)
        
        # Test with each server
        test_servers = [
            ('openvpn-server-01', 'us-east-1'),
            ('openvpn-server-trustwindows02', 'woodbridge-ON'),
            ('openvpn-server-trustwindws01', 'woodbridge-ON')
        ]
        
        for server_name, server_location in test_servers:
            print(f"\nTesting server: {server_name} ({server_location})")
            print("-" * 40)
            
            # Call the dashboard function directly
            status = get_server_status(server_name, server_location)
            
            if status:
                print(f"✅ Status returned successfully")
                print(f"   Public IP: {status.get('public_ip')}")
                print(f"   Status: {status.get('status')}")
                print(f"   Last seen: {status.get('last_seen')}")
                print(f"   System stats: {status.get('system_stats')}")
            else:
                print(f"❌ Status returned None")
        
    except Exception as e:
        print(f"Error testing dashboard function: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_dashboard_function()
