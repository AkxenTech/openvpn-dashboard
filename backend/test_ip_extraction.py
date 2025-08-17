#!/usr/bin/env python3
"""
Test IP extraction function with actual MongoDB data
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

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

def test_ip_extraction():
    """Test IP extraction with actual MongoDB data"""
    try:
        # Connect to MongoDB
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client[os.getenv('MONGODB_DATABASE', 'openvpn_logs')]
        collection = db[os.getenv('MONGODB_COLLECTION', 'connection_logs')]
        
        # Get latest system stats for each server
        pipeline = [
            {
                '$match': {'type': 'system_stats'}
            },
            {
                '$group': {
                    '_id': {
                        'server_name': '$server_name',
                        'server_location': '$server_location'
                    },
                    'latest_stats': {'$last': '$$ROOT'}
                }
            },
            {'$sort': {'_id.server_name': 1}}
        ]
        
        results = list(collection.aggregate(pipeline))
        
        print("Testing IP extraction with actual data:")
        print("=" * 50)
        
        for result in results:
            server_name = result['_id']['server_name']
            server_location = result['_id']['server_location']
            stats_doc = result['latest_stats']
            
            print(f"\nServer: {server_name} ({server_location})")
            
            if 'interfaces' in stats_doc:
                interfaces = stats_doc['interfaces']
                public_ip = extract_public_ip_from_interfaces(interfaces)
                
                print(f"Interfaces found: {list(interfaces.keys())}")
                print(f"Extracted public IP: {public_ip}")
                
                # Show all interfaces for debugging
                for interface_name, interface_data in interfaces.items():
                    print(f"  {interface_name}: {interface_data.get('ip')}")
            else:
                print("No interfaces data found")
            
            print("-" * 30)
        
        client.close()
        
    except Exception as e:
        print(f"Error testing IP extraction: {e}")

if __name__ == '__main__':
    test_ip_extraction()
