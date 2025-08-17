#!/usr/bin/env python3
"""
Debug version of OpenVPN Dashboard Backend
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

print("1. Starting debug app...")

# Load environment variables
load_dotenv()
print("2. Environment variables loaded")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
print("3. Logging configured")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
print("4. Flask app created")

CORS(app)
print("5. CORS configured")

socketio = SocketIO(app, cors_allowed_origins="*")
print("6. SocketIO configured")

# MongoDB connection
def get_mongodb_client():
    """Get MongoDB client connection"""
    print("7. Attempting MongoDB connection...")
    try:
        uri = os.getenv('MONGODB_URI')
        if not uri:
            raise ValueError("MONGODB_URI not set in environment variables")
        
        print("8. MongoDB URI found, creating client...")
        client = MongoClient(uri)
        # Test connection
        print("9. Testing MongoDB connection...")
        client.admin.command('ping')
        print("10. MongoDB connection successful")
        return client
    except Exception as e:
        print(f"11. MongoDB connection failed: {e}")
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None

@app.route('/')
def index():
    """Serve the dashboard frontend"""
    return jsonify({'message': 'Dashboard is working!'})

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    print("12. Starting main block...")
    port = int(os.getenv('DASHBOARD_PORT', 5001))
    host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"13. Starting OpenVPN Dashboard on {host}:{port}")
    print(f"14. Debug mode: {debug}")
    
    # Test MongoDB connection first
    client = get_mongodb_client()
    if client:
        print("15. MongoDB connection test successful")
    else:
        print("15. MongoDB connection test failed")
    
    print("16. Starting Flask app...")
    socketio.run(app, host=host, port=port, debug=debug, use_reloader=False)
