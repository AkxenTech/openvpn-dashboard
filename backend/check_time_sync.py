#!/usr/bin/env python3
"""
Check time synchronization between servers and local time
"""

import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_time_sync():
    """Check time synchronization between servers and local time"""
    try:
        # Connect to MongoDB
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client[os.getenv('MONGODB_DATABASE', 'openvpn_logs')]
        collection = db[os.getenv('MONGODB_COLLECTION', 'connection_logs')]
        
        # Get current UTC time
        current_time = datetime.utcnow()
        print(f"Current UTC time: {current_time}")
        
        # Get latest events from each server
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'server_name': '$server_name',
                        'server_location': '$server_location'
                    },
                    'latest_timestamp': {'$max': '$timestamp'},
                    'event_count': {'$sum': 1}
                }
            },
            {'$sort': {'latest_timestamp': -1}}
        ]
        
        results = list(collection.aggregate(pipeline))
        
        print(f"\nFound {len(results)} servers:")
        print("-" * 80)
        
        for result in results:
            server_name = result['_id']['server_name']
            server_location = result['_id']['server_location']
            latest_timestamp = result['latest_timestamp']
            event_count = result['event_count']
            
            if latest_timestamp:
                time_diff = current_time - latest_timestamp
                time_diff_minutes = time_diff.total_seconds() / 60
                
                print(f"Server: {server_name} ({server_location})")
                print(f"  Latest event: {latest_timestamp}")
                print(f"  Time difference: {time_diff_minutes:.1f} minutes")
                print(f"  Total events: {event_count}")
                
                if time_diff_minutes > 10:
                    print(f"  ⚠️  WARNING: Server time might be off by {time_diff_minutes:.1f} minutes")
                elif time_diff_minutes < -10:
                    print(f"  ⚠️  WARNING: Server time is ahead by {abs(time_diff_minutes):.1f} minutes")
                else:
                    print(f"  ✅ Time appears to be synchronized")
                print()
        
        # Check for heartbeat data specifically
        print("Checking for heartbeat data:")
        print("-" * 40)
        
        heartbeats = list(collection.find({'type': 'heartbeat'}).sort('timestamp', -1).limit(10))
        
        if heartbeats:
            print(f"Found {len(heartbeats)} heartbeat records:")
            for hb in heartbeats:
                hb_time = hb['timestamp']
                time_diff = current_time - hb_time
                time_diff_minutes = time_diff.total_seconds() / 60
                
                print(f"  {hb['server_name']} ({hb['server_location']}): {hb_time} ({time_diff_minutes:.1f} min ago)")
        else:
            print("No heartbeat data found. Servers may not be sending heartbeats yet.")
        
        client.close()
        
    except Exception as e:
        print(f"Error checking time sync: {e}")

if __name__ == '__main__':
    check_time_sync()
