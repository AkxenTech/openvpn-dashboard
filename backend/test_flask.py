#!/usr/bin/env python3
"""
Simple Flask test to isolate the issue
"""

from flask import Flask, jsonify
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

@app.route('/')
def index():
    return jsonify({'message': 'Flask is working!'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5001))
    host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    
    print(f"Starting test Flask app on {host}:{port}")
    app.run(host=host, port=port, debug=True)
