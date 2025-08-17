#!/usr/bin/env python3
"""
Debug the get_server_status function to see why public IP is not being extracted
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

def extract_public_ip_from_interfaces(interfaces):
    """Extract public IP from system interfaces"""
    if not interfaces:
        return None
    
    # Priority order for public IP detection
    # 1. ens4 (usually external interface)
    # 2. enp1s0 (alternative external interface)
    # 3. ens3 (internal interface)
    # 4. Any interface that's not loopback or tunnel
    
    if 'ens4' in interfaces:
        return interfaces['ens4'].get('ip')
    elif 'enp1s0' in interfaces:
        return interfaces['enp1s0'].get('ip')
    elif 'ens3' in interfaces:
        return interfaces['ens3'].get('ip')
    else:
        # Find any interface that's not loopback or tunnel
        for interface_name, interface_data in interfaces.items():
            if interface_name not in ['lo', 'tun0', 'tun1']:
                return interface_data.get('ip')
        return None

def debug_server_status():
    """Debug the get_server_status function"""
    try:
        # Connect to MongoDB
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client[os.getenv('MONGODB_DATABASE', 'openvpn_logs')]
        collection = db[os.getenv('MONGODB_COLLECTION', 'connection_logs')]
        
        print("Debugging get_server_status function:")
        print("=" * 60)
        
        # Test with each server
        test_servers = [
            ('openvpn-server-01', 'us-east-1'),
            ('openvpn-server-trustwindows02', 'woodbridge-ON'),
            ('openvpn-server-trustwindws01', 'woodbridge-ON')
        ]
        
        for server_name, server_location in test_servers:
            print(f"\nTesting server: {server_name} ({server_location})")
            print("-" * 50)
            
            # Get latest system stats (same query as dashboard)
            latest_stats = collection.find_one(
                {
                    'server_name': server_name,
                    'server_location': server_location,
                    'type': 'system_stats'
                },
                sort=[('timestamp', -1)]
            )
            
            if latest_stats:
                print(f"✅ Found latest system stats")
                print(f"   Timestamp: {latest_stats.get('timestamp')}")
                print(f"   Has interfaces: {'interfaces' in latest_stats}")
                
                if 'interfaces' in latest_stats:
                    interfaces = latest_stats.get('interfaces', {})
                    print(f"   Interface count: {len(interfaces)}")
                    print(f"   Interfaces: {list(interfaces.keys())}")
                    
                    # Extract public IP
                    public_ip = extract_public_ip_from_interfaces(interfaces)
                    print(f"   Extracted public IP: {public_ip}")
                    
                    # Show all interfaces
                    for interface_name, interface_data in interfaces.items():
                        print(f"     {interface_name}: {interface_data.get('ip')}")
                else:
                    print(f"   ❌ No interfaces data found")
            else:
                print(f"❌ No system stats found for {server_name} ({server_location})")
                
                # Check what documents exist for this server
                all_docs = list(collection.find({
                    'server_name': server_name
                }).limit(3))
                
                print(f"   Found {len(all_docs)} total documents for this server:")
                for doc in all_docs:
                    print(f"     Type: {doc.get('type')}, Location: {doc.get('server_location')}, Timestamp: {doc.get('timestamp')}")
        
        client.close()
        
    except Exception as e:
        print(f"Error debugging server status: {e}")

if __name__ == '__main__':
    debug_server_status()
