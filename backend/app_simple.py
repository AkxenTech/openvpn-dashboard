#!/usr/bin/env python3
"""
OpenVPN Dashboard Backend (Simplified for Render)
Multi-server monitoring dashboard API with multi-tenancy support
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
import pytz

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Timezone handling
def convert_to_toronto_time(utc_time):
    """Convert UTC time to Toronto timezone"""
    if not utc_time:
        return None
    try:
        toronto_tz = pytz.timezone('America/Toronto')
        if utc_time.tzinfo is None:
            utc_time = pytz.utc.localize(utc_time)
        return utc_time.astimezone(toronto_tz)
    except Exception as e:
        logger.error(f"Error converting timezone: {e}")
        return utc_time

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

# MongoDB connection
def get_mongodb_client():
    """Get MongoDB client connection"""
    try:
        uri = os.getenv('MONGODB_URI')
        if not uri:
            raise ValueError("MONGODB_URI not set in environment variables")
        
        client = MongoClient(uri)
        # Test connection
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None

def get_database():
    """Get database instance"""
    client = get_mongodb_client()
    if client:
        database = os.getenv('MONGODB_DATABASE', 'openvpn_logs')
        return client[database]
    return None

def get_collection():
    """Get collection instance"""
    db = get_database()
    if db is not None:
        collection = os.getenv('MONGODB_COLLECTION', 'connection_logs')
        return db[collection]
    return None

def get_all_servers():
    """Get all unique server combinations"""
    collection = get_collection()
    if collection is None:
        return []
    
    try:
        # Use aggregation pipeline to get unique server combinations
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'server_name': '$server_name',
                        'server_location': '$server_location'
                    }
                }
            },
            {
                '$project': {
                    'server_name': '$_id.server_name',
                    'server_location': '$_id.server_location',
                    '_id': 0
                }
            }
        ]
        
        servers = list(collection.aggregate(pipeline))
        logger.info(f"Found {len(servers)} servers: {servers}")
        return servers
    except Exception as e:
        logger.error(f"Error getting servers: {e}")
        # Fallback to distinct method
        try:
            server_names = collection.distinct('server_name')
            server_locations = collection.distinct('server_location')
            
            # Create combinations
            servers = []
            for name in server_names:
                for location in server_locations:
                    servers.append({
                        'server_name': name,
                        'server_location': location
                    })
            return servers
        except Exception as e2:
            logger.error(f"Fallback method also failed: {e2}")
            return []

def check_server_connectivity(server_name, server_location):
    """Check if server is online based on recent activity"""
    collection = get_collection()
    if collection is None:
        return False
    
    try:
        # Check for recent system stats (within last 4 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=4)
        
        latest_stats = collection.find_one({
            'server_name': server_name,
            'server_location': server_location,
            'type': 'system_stats',
            'timestamp': {'$gte': cutoff_time}
        }, sort=[('timestamp', -1)])
        
        if latest_stats:
            return True
        
        # Check for recent heartbeat (within last 5 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        latest_heartbeat = collection.find_one({
            'server_name': server_name,
            'server_location': server_location,
            'type': 'heartbeat',
            'timestamp': {'$gte': cutoff_time}
        }, sort=[('timestamp', -1)])
        
        if latest_heartbeat:
            return True
        
        # Check for recent connections (within last 5 minutes)
        latest_connection = collection.find_one({
            'server_name': server_name,
            'server_location': server_location,
            'event_type': 'connect',
            'timestamp': {'$gte': cutoff_time}
        }, sort=[('timestamp', -1)])
        
        return latest_connection is not None
        
    except Exception as e:
        logger.error(f"Error checking connectivity for {server_name}: {e}")
        return False

def get_server_status(server_name, server_location):
    """Get detailed server status"""
    collection = get_collection()
    if collection is None:
        return None
    
    try:
        # Get latest system stats
        latest_stats = collection.find_one({
            'server_name': server_name,
            'server_location': server_location,
            'type': 'system_stats'
        }, sort=[('timestamp', -1)])
        
        # Get latest heartbeat
        latest_heartbeat = collection.find_one({
            'server_name': server_name,
            'server_location': server_location,
            'type': 'heartbeat'
        }, sort=[('timestamp', -1)])
        
        # Get latest connection
        latest_connection = collection.find_one({
            'server_name': server_name,
            'server_location': server_location,
            'event_type': 'connect'
        }, sort=[('timestamp', -1)])
        
        # Extract public IP and uptime from system stats
        public_ip_from_stats = None
        last_system_update = None
        uptime_from_stats = None
        if latest_stats and 'interfaces' in latest_stats:
            public_ip_from_stats = extract_public_ip_from_interfaces(latest_stats['interfaces'])
            last_system_update = latest_stats.get('timestamp')
            # Extract uptime from system stats
            if 'stats' in latest_stats and 'uptime' in latest_stats['stats']:
                uptime_from_stats = latest_stats['stats']['uptime']
            logger.info(f"Server {server_name}: public_ip_from_stats={public_ip_from_stats}, uptime_from_stats={uptime_from_stats}")
        
        # Determine final public IP (prioritize heartbeat, fallback to stats)
        final_public_ip = None
        if latest_heartbeat and latest_heartbeat.get('public_ip'):
            final_public_ip = latest_heartbeat.get('public_ip')
        elif public_ip_from_stats:
            final_public_ip = public_ip_from_stats
        
        # Determine server status (use system_stats as primary indicator)
        is_online = False
        if last_system_update:
            time_diff = datetime.utcnow() - last_system_update
            time_diff_seconds = abs(time_diff.total_seconds())  # Use absolute value to handle clock drift
            is_online = time_diff_seconds < 14400  # 4 hours to handle timezone differences (Toronto EDT = UTC-4)
            logger.info(f"Server {server_name}: last_system_update={last_system_update}, current_time={datetime.utcnow()}, time_diff_seconds={time_diff_seconds}, is_online={is_online}")
        elif latest_heartbeat and latest_heartbeat.get('timestamp'):
            time_diff = datetime.utcnow() - latest_heartbeat['timestamp']
            is_online = time_diff.total_seconds() < 300  # 5 minutes
        elif latest_connection and latest_connection.get('timestamp'):
            time_diff = datetime.utcnow() - latest_connection['timestamp']
            is_online = time_diff.total_seconds() < 300  # 5 minutes
        
        status = {
            'server_name': server_name,
            'server_location': server_location,
            'status': 'online' if is_online else 'offline',
            'public_ip': final_public_ip,
            'uptime': uptime_from_stats if uptime_from_stats else (latest_heartbeat.get('uptime') if latest_heartbeat else None),
            'last_seen': last_system_update,  # Use last_system_update directly
            'last_seen_toronto': convert_to_toronto_time(last_system_update) if last_system_update else None,
            'last_heartbeat': latest_heartbeat.get('timestamp') if latest_heartbeat else None,
            'last_heartbeat_toronto': convert_to_toronto_time(latest_heartbeat.get('timestamp')) if latest_heartbeat else None,
            'last_connection': latest_connection.get('timestamp') if latest_connection else None,
            'last_connection_toronto': convert_to_toronto_time(latest_connection.get('timestamp')) if latest_connection else None,
            'last_system_update': last_system_update,
            'last_system_update_toronto': convert_to_toronto_time(last_system_update) if last_system_update else None
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting status for {server_name}: {e}")
        return None

def get_server_connections(server_name, server_location, limit=50):
    """Get recent connections for a server"""
    collection = get_collection()
    if collection is None:
        return []
    
    try:
        connections = list(collection.find({
            'server_name': server_name,
            'server_location': server_location,
            'event_type': 'connect'
        }, sort=[('timestamp', -1)], limit=limit))
        
        # Convert ObjectId to string for JSON serialization
        for conn in connections:
            if '_id' in conn:
                conn['_id'] = str(conn['_id'])
        
        return connections
    except Exception as e:
        logger.error(f"Error getting connections for {server_name}: {e}")
        return []

def get_connection_analytics(days=7):
    """Get connection analytics for the last N days"""
    collection = get_collection()
    if collection is None:
        return {}
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {
                '$match': {
                    'event_type': 'connect',
                    'timestamp': {'$gte': cutoff_date}
                }
            },
            {
                '$group': {
                    '_id': {
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                        'server_name': '$server_name',
                        'server_location': '$server_location'
                    },
                    'connections': {'$sum': 1}
                }
            },
            {
                '$group': {
                    '_id': '$_id.date',
                    'servers': {
                        '$push': {
                            'server_name': '$_id.server_name',
                            'server_location': '$_id.server_location',
                            'connections': '$connections'
                        }
                    },
                    'total_connections': {'$sum': '$connections'}
                }
            },
            {'$sort': {'_id': 1}}
        ]
        
        analytics = list(collection.aggregate(pipeline))
        return {'analytics': analytics}
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return {}

def get_user_analytics(days=30):
    """Get user analytics for the last N days"""
    collection = get_collection()
    if collection is None:
        return {}
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {
                '$match': {
                    'event_type': 'connect',
                    'timestamp': {'$gte': cutoff_date}
                }
            },
            {
                '$group': {
                    '_id': '$username',
                    'connection_count': {'$sum': 1},
                    'last_connection': {'$max': '$timestamp'},
                    'servers': {'$addToSet': {'$concat': ['$server_name', ' - ', '$server_location']}}
                }
            },
            {'$sort': {'connection_count': -1}},
            {'$limit': 20}
        ]
        
        users = list(collection.aggregate(pipeline))
        return {'users': users}
    except Exception as e:
        logger.error(f"Error getting user analytics: {e}")
        return {}

# API Routes
@app.route('/')
def index():
    """Serve the dashboard frontend"""
    return render_template('index_simple.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        servers = get_all_servers()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'servers_count': len(servers),
            'mongodb_connected': get_collection() is not None
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/servers')
def list_servers():
    """List all servers with their status"""
    try:
        servers = get_all_servers()
        server_statuses = []
        
        for server in servers:
            status = get_server_status(server['server_name'], server['server_location'])
            if status:
                server_statuses.append(status)
            else:
                # Include server even if status is None (unknown status)
                server_statuses.append({
                    'server_name': server['server_name'],
                    'server_location': server['server_location'],
                    'status': 'unknown',
                    'public_ip': None,
                    'uptime': None,
                    'last_seen': None,
                    'last_seen_toronto': None
                })
        
        return jsonify({
            'servers': server_statuses,
            'count': len(server_statuses)
        })
    except Exception as e:
        logger.error(f"Error listing servers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servers/<server_name>/status')
def server_status(server_name):
    """Get detailed status for a specific server"""
    try:
        server_location = request.args.get('location', 'default')
        status = get_server_status(server_name, server_location)
        
        if status:
            return jsonify(status)
        else:
            return jsonify({'error': 'Server not found'}), 404
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servers/<server_name>/connections')
def server_connections(server_name):
    """Get recent connections for a specific server"""
    try:
        server_location = request.args.get('location', 'default')
        limit = int(request.args.get('limit', 50))
        
        connections = get_server_connections(server_name, server_location, limit)
        return jsonify({
            'server_name': server_name,
            'server_location': server_location,
            'connections': connections,
            'count': len(connections)
        })
    except Exception as e:
        logger.error(f"Error getting server connections: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/connections')
def connection_analytics():
    """Get connection analytics"""
    try:
        days = int(request.args.get('days', 7))
        analytics = get_connection_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        logger.error(f"Error getting connection analytics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/users')
def user_analytics():
    """Get user analytics"""
    try:
        days = int(request.args.get('days', 30))
        analytics = get_user_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        logger.error(f"Error getting user analytics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test')
def test_endpoint():
    """Test endpoint for debugging"""
    return jsonify({
        'message': 'Test endpoint working',
        'timestamp': datetime.utcnow().isoformat(),
        'environment': os.getenv('FLASK_ENV', 'development')
    })

if __name__ == '__main__':
    logger.info("Starting OpenVPN Dashboard (Simplified)")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    logger.info(f"Debug mode: {os.getenv('FLASK_DEBUG', 'False')}")
    
    # Set environment variables for production
    os.environ['FLASK_ENV'] = os.getenv('FLASK_ENV', 'production')
    os.environ['FLASK_DEBUG'] = os.getenv('FLASK_DEBUG', 'False')
    
    # Run the app
    port = int(os.getenv('DASHBOARD_PORT', 5000))
    host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    
    app.run(host=host, port=port, debug=False)
