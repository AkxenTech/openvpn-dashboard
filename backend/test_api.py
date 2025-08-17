#!/usr/bin/env python3
"""
Test script to verify Flask app functionality
"""

import requests
import json

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get('http://localhost:5001/api/health')
        print(f"Health endpoint status: {response.status_code}")
        print(f"Health response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Health test failed: {e}")
        return None

def test_servers():
    """Test servers endpoint"""
    try:
        response = requests.get('http://localhost:5001/api/servers')
        print(f"Servers endpoint status: {response.status_code}")
        print(f"Servers response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Servers test failed: {e}")
        return None

if __name__ == '__main__':
    print("Testing Flask app endpoints...")
    health = test_health()
    servers = test_servers()
    
    print(f"\nSummary:")
    print(f"Health servers_count: {health.get('servers_count', 'N/A') if health else 'N/A'}")
    print(f"Servers endpoint count: {len(servers) if servers else 'N/A'}")
