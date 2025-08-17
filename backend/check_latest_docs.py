#!/usr/bin/env python3
"""
Check that we're getting the latest system stats documents from MongoDB
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def check_latest_documents():
    """Check that we're getting the latest system stats documents"""
    try:
        # Connect to MongoDB
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client[os.getenv('MONGODB_DATABASE', 'openvpn_logs')]
        collection = db[os.getenv('MONGODB_COLLECTION', 'connection_logs')]
        
        print("Checking latest system stats documents:")
        print("=" * 60)
        
        # Get all servers
        servers = collection.distinct('server_name')
        
        for server_name in servers:
            print(f"\nServer: {server_name}")
            print("-" * 40)
            
            # Get all system stats for this server, sorted by timestamp
            stats_docs = list(collection.find({
                'server_name': server_name,
                'type': 'system_stats'
            }).sort('timestamp', -1).limit(5))
            
            print(f"Found {len(stats_docs)} system stats documents")
            
            if stats_docs:
                # Show the latest 3 documents
                for i, doc in enumerate(stats_docs[:3]):
                    timestamp = doc.get('timestamp')
                    has_interfaces = 'interfaces' in doc
                    interface_count = len(doc.get('interfaces', {}))
                    
                    print(f"  Doc {i+1}: {timestamp} | Interfaces: {has_interfaces} ({interface_count} interfaces)")
                    
                    if has_interfaces:
                        interfaces = doc.get('interfaces', {})
                        for interface_name, interface_data in interfaces.items():
                            print(f"    {interface_name}: {interface_data.get('ip')}")
                
                # Check if the latest document has interfaces
                latest_doc = stats_docs[0]
                if 'interfaces' in latest_doc:
                    print(f"\n✅ Latest document has interfaces data")
                else:
                    print(f"\n❌ Latest document missing interfaces data")
            else:
                print("  No system stats documents found")
        
        # Also check the aggregation pipeline we're using in the dashboard
        print(f"\n\nTesting dashboard aggregation pipeline:")
        print("=" * 60)
        
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
        
        for result in results:
            server_name = result['_id']['server_name']
            server_location = result['_id']['server_location']
            stats_doc = result['latest_stats']
            
            timestamp = stats_doc.get('timestamp')
            has_interfaces = 'interfaces' in stats_doc
            interface_count = len(stats_doc.get('interfaces', {}))
            
            print(f"\n{server_name} ({server_location}):")
            print(f"  Timestamp: {timestamp}")
            print(f"  Has interfaces: {has_interfaces} ({interface_count} interfaces)")
            
            if has_interfaces:
                interfaces = stats_doc.get('interfaces', {})
                for interface_name, interface_data in interfaces.items():
                    print(f"    {interface_name}: {interface_data.get('ip')}")
        
        client.close()
        
    except Exception as e:
        print(f"Error checking latest documents: {e}")

if __name__ == '__main__':
    check_latest_documents()
