#!/usr/bin/env python3
"""
Test Flask app to verify server detection
"""

from flask import Flask, jsonify
from dotenv import load_dotenv
import os
from pymongo import MongoClient
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# MongoDB connection
def get_collection():
    """Get collection instance"""
    try:
        uri = os.getenv('MONGODB_URI')
        if not uri:
            return None
        
        client = MongoClient(uri)
        client.admin.command('ping')
        
        database = os.getenv('MONGODB_DATABASE', 'openvpn_logs')
        collection = os.getenv('MONGODB_COLLECTION', 'connection_logs')
        
        return client[database][collection]
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None

def get_all_servers():
    """Get all unique servers from the database"""
    try:
        collection = get_collection()
        if collection is None:
            return []
        
        # Simple approach: get all documents and extract unique server combinations
        all_docs = collection.find({}, {'server_name': 1, 'server_location': 1, '_id': 0})
        
        # Use a set to track unique combinations
        server_combinations = set()
        for doc in all_docs:
            if 'server_name' in doc and 'server_location' in doc:
                server_combinations.add((doc['server_name'], doc['server_location']))
        
        # Convert to list of dictionaries
        servers = []
        for name, location in sorted(server_combinations):
            servers.append({
                'server_name': name,
                'server_location': location
            })
        
        logger.info(f"Found {len(servers)} servers")
        return servers
    except Exception as e:
        logger.error(f"Error getting servers: {e}")
        return []

@app.route('/')
def index():
    return jsonify({'message': 'Test Flask app working'})

@app.route('/api/test')
def test():
    """Test endpoint"""
    try:
        servers = get_all_servers()
        return jsonify({
            'message': 'Test endpoint working',
            'servers_found': len(servers),
            'servers': servers
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5002))
    host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    
    logger.info(f"Starting test Flask app on {host}:{port}")
    app.run(host=host, port=port, debug=True)
