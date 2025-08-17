#!/usr/bin/env python3
"""
Debug script to check environment variables and MongoDB connection
"""

from dotenv import load_dotenv
import os
from pymongo import MongoClient

# Load environment variables
load_dotenv()

print("=== Environment Variables ===")
print(f"MONGODB_URI: {os.getenv('MONGODB_URI')}")
print(f"MONGODB_DATABASE: {os.getenv('MONGODB_DATABASE')}")
print(f"MONGODB_COLLECTION: {os.getenv('MONGODB_COLLECTION')}")

print("\n=== MongoDB Connection Test ===")
try:
    client = MongoClient(os.getenv('MONGODB_URI'))
    client.admin.command('ping')
    print("✅ MongoDB connection successful")
    
    db = client[os.getenv('MONGODB_DATABASE')]
    collection = db[os.getenv('MONGODB_COLLECTION')]
    print(f"✅ Database: {os.getenv('MONGODB_DATABASE')}")
    print(f"✅ Collection: {os.getenv('MONGODB_COLLECTION')}")
    
    # Test server detection
    all_docs = collection.find({}, {'server_name': 1, 'server_location': 1, '_id': 0})
    server_combinations = set()
    for doc in all_docs:
        if 'server_name' in doc and 'server_location' in doc:
            server_combinations.add((doc['server_name'], doc['server_location']))
    
    servers = []
    for name, location in sorted(server_combinations):
        servers.append({
            'server_name': name,
            'server_location': location
        })
    
    print(f"✅ Found {len(servers)} servers: {servers}")
    
except Exception as e:
    print(f"❌ Error: {e}")
