#!/usr/bin/env python3
"""
Debug script to check system_stats documents in MongoDB
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def debug_system_stats():
    """Debug system_stats documents"""
    try:
        # Connect to MongoDB
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client[os.getenv('MONGODB_DATABASE', 'openvpn_logs')]
        collection = db[os.getenv('MONGODB_COLLECTION', 'connection_logs')]
        
        print("Checking system_stats documents:")
        print("=" * 60)
        
        # Get all servers
        servers = collection.distinct('server_name')
        
        for server_name in servers:
            print(f"\nServer: {server_name}")
            print("-" * 40)
            
            # Get all system_stats for this server, sorted by timestamp
            stats_docs = list(collection.find({
                'server_name': server_name,
                'type': 'system_stats'
            }).sort('timestamp', -1).limit(3))
            
            print(f"Found {len(stats_docs)} system_stats documents")
            
            if stats_docs:
                for i, doc in enumerate(stats_docs):
                    timestamp = doc.get('timestamp')
                    print(f"  Doc {i+1}: {timestamp}")
                    
                    # Check if this is the document we're looking for
                    if timestamp:
                        print(f"    This should be used for last_seen")
                    else:
                        print(f"    ⚠️  No timestamp found!")
            else:
                print("  No system_stats documents found")
                
                # Check what types of documents exist for this server
                doc_types = collection.distinct('type', {'server_name': server_name})
                print(f"  Available document types: {doc_types}")
        
        client.close()
        
    except Exception as e:
        print(f"Error debugging system_stats: {e}")

if __name__ == '__main__':
    debug_system_stats()
