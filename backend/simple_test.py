#!/usr/bin/env python3
"""
Simple test to verify Flask app MongoDB access
"""

from app import get_collection, get_all_servers

print("=== Testing Flask app MongoDB access ===")

# Test collection access
collection = get_collection()
if collection is not None:
    print("✅ Collection access successful")
    
    # Test document count
    count = collection.count_documents({})
    print(f"✅ Document count: {count}")
    
    # Test server detection
    servers = get_all_servers()
    print(f"✅ Servers found: {len(servers)}")
    for server in servers:
        print(f"  - {server['server_name']} ({server['server_location']})")
else:
    print("❌ Collection access failed")
