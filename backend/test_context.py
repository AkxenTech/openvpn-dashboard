#!/usr/bin/env python3
"""
Test to check Flask request context issues
"""

import requests
import time

def test_endpoints():
    """Test all endpoints"""
    base_url = "http://localhost:5001"
    
    print("=== Testing Flask App Endpoints ===")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"Health endpoint: {response.status_code}")
        data = response.json()
        print(f"  - servers_count: {data.get('servers_count', 'N/A')}")
        print(f"  - mongodb: {data.get('mongodb', 'N/A')}")
    except Exception as e:
        print(f"Health endpoint failed: {e}")
    
    # Test servers endpoint
    try:
        response = requests.get(f"{base_url}/api/servers")
        print(f"Servers endpoint: {response.status_code}")
        data = response.json()
        print(f"  - servers returned: {len(data) if isinstance(data, list) else 'N/A'}")
        if isinstance(data, list) and len(data) > 0:
            for server in data:
                print(f"    - {server.get('server_name', 'N/A')} ({server.get('server_location', 'N/A')})")
    except Exception as e:
        print(f"Servers endpoint failed: {e}")
    
    # Test test endpoint (if it exists)
    try:
        response = requests.get(f"{base_url}/api/test")
        print(f"Test endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  - servers_found: {data.get('servers_found', 'N/A')}")
    except Exception as e:
        print(f"Test endpoint failed: {e}")

if __name__ == '__main__':
    test_endpoints()
