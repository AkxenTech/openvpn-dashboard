#!/usr/bin/env python3
"""
Check the actual structure of system stats documents in MongoDB
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def check_system_stats_structure():
    """Check the structure of system stats documents"""
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
        
        print(f"Found {len(results)} servers with system stats:")
        print("=" * 80)
        
        for result in results:
            server_name = result['_id']['server_name']
            server_location = result['_id']['server_location']
            stats_doc = result['latest_stats']
            
            print(f"\nServer: {server_name} ({server_location})")
            print(f"Timestamp: {stats_doc.get('timestamp')}")
            print(f"Has interfaces: {'interfaces' in stats_doc}")
            
            if 'interfaces' in stats_doc:
                interfaces = stats_doc['interfaces']
                print(f"Interface count: {len(interfaces)}")
                print("Interfaces:")
                for interface_name, interface_data in interfaces.items():
                    print(f"  {interface_name}: {interface_data.get('ip')}/{interface_data.get('netmask')}")
            else:
                print("No interfaces data found")
            
            print(f"Stats keys: {list(stats_doc.get('stats', {}).keys())}")
            print("-" * 40)
        
        # Also check for any documents with interfaces
        interface_docs = list(collection.find({'interfaces': {'$exists': True}}).limit(5))
        print(f"\nFound {len(interface_docs)} documents with interfaces field:")
        for doc in interface_docs:
            print(f"  Type: {doc.get('type')}, Server: {doc.get('server_name')}, Interfaces: {list(doc.get('interfaces', {}).keys())}")
        
        client.close()
        
    except Exception as e:
        print(f"Error checking system stats: {e}")

if __name__ == '__main__':
    check_system_stats_structure()
