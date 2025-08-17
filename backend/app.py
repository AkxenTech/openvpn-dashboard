#!/usr/bin/env python3
"""
OpenVPN Dashboard Backend
Multi-server monitoring dashboard API with multi-tenancy support
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
socketio = SocketIO(app, cors_allowed_origins="*")

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

# Multi-tenancy helper functions
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

def check_server_connectivity():
    """Check connectivity status of all servers via heartbeats"""
    try:
        collection = get_collection()
        if collection is None:
            return []
        
        # Get latest heartbeat from each server
        pipeline = [
            {
                '$match': {
                    'type': 'heartbeat',
                    'timestamp': {'$gte': datetime.utcnow() - timedelta(minutes=10)}
                }
            },
            {
                '$group': {
                    '_id': {
                        'server_name': '$server_name',
                        'server_location': '$server_location'
                    },
                    'last_heartbeat': {'$max': '$timestamp'},
                    'public_ip': {'$last': '$public_ip'},
                    'mongodb_status': {'$last': '$mongodb_status'},
                    'uptime': {'$last': '$uptime'}
                }
            }
        ]
        
        heartbeats = list(collection.aggregate(pipeline))
        
        connectivity_status = []
        for heartbeat in heartbeats:
            time_diff = datetime.utcnow() - heartbeat['last_heartbeat']
            is_connected = time_diff.total_seconds() < 600  # 10 minutes
            
            connectivity_status.append({
                'server_name': heartbeat['_id']['server_name'],
                'server_location': heartbeat['_id']['server_location'],
                'last_heartbeat': heartbeat['last_heartbeat'],
                'public_ip': heartbeat['public_ip'],
                'mongodb_status': heartbeat['mongodb_status'],
                'uptime_seconds': heartbeat.get('uptime', 0),
                'is_connected': is_connected,
                'time_since_last_heartbeat': time_diff.total_seconds()
            })
        
        return connectivity_status
    except Exception as e:
        logger.error(f"Error checking connectivity: {e}")
        return []

def get_server_status(server_name, server_location):
    """Get detailed status for a specific server"""
    try:
        collection = get_collection()
        if collection is None:
            return None
        
        # Get latest system stats
        logger.info(f"Server {server_name}: Querying for system_stats with server_name={server_name}, server_location={server_location}")
        latest_stats = collection.find_one(
            {
                'server_name': server_name,
                'server_location': server_location,
                'type': 'system_stats'
            },
            sort=[('timestamp', -1)]
        )
        
        # Debug: Log what we found for system stats
        if latest_stats:
            logger.info(f"Server {server_name}: Found system_stats with timestamp {latest_stats.get('timestamp')}")
        else:
            logger.info(f"Server {server_name}: No system_stats found")
            
            # Try a broader search to see what's available
            all_stats = list(collection.find({'type': 'system_stats'}).limit(5))
            logger.info(f"Server {server_name}: Found {len(all_stats)} total system_stats documents")
            for doc in all_stats:
                logger.info(f"Server {server_name}: Found stats doc with server_name={doc.get('server_name')}, server_location={doc.get('server_location')}, timestamp={doc.get('timestamp')}")
        
        # Get latest connection event (for active connections count only)
        latest_connection = collection.find_one(
            {
                'server_name': server_name,
                'server_location': server_location,
                'event_type': {'$in': ['connect', 'authenticated', 'disconnect']}
            },
            sort=[('timestamp', -1)]
        )
        
        # Extract public IP and last update time from system stats
        public_ip_from_stats = None
        last_system_update = None
        if latest_stats:
            # Extract public IP from interfaces
            interfaces = latest_stats.get('interfaces', {})
            public_ip_from_stats = extract_public_ip_from_interfaces(interfaces)
            logger.info(f"Server {server_name}: interfaces={list(interfaces.keys()) if interfaces else 'None'}, extracted_public_ip={public_ip_from_stats}")
            
            # Extract last update time
            if latest_stats.get('timestamp'):
                last_system_update = latest_stats['timestamp']
        
        # Get latest heartbeat
        latest_heartbeat = collection.find_one(
            {
                'server_name': server_name,
                'server_location': server_location,
                'type': 'heartbeat'
            },
            sort=[('timestamp', -1)]
        )
        
        # Count active connections (last 5 minutes)
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        active_connections = collection.count_documents({
            'server_name': server_name,
            'server_location': server_location,
            'event_type': 'authenticated',
            'timestamp': {'$gte': five_minutes_ago}
        })
        
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
        
        # Debug: Check what latest_stats contains
        logger.info(f"Server {server_name}: latest_stats timestamp = {latest_stats.get('timestamp') if latest_stats else 'None'}")
        logger.info(f"Server {server_name}: last_system_update = {last_system_update}")
        logger.info(f"Server {server_name}: CODE UPDATED - Using system_stats for last_seen")
        
        status = {
            'server_name': server_name,
            'server_location': server_location,
            'status': 'online' if is_online else 'offline',
            'last_seen': last_system_update,  # Use last_system_update directly
            'last_seen_toronto': convert_to_toronto_time(last_system_update) if last_system_update else None,
            'last_heartbeat': latest_heartbeat.get('timestamp') if latest_heartbeat else None,
            'last_heartbeat_toronto': convert_to_toronto_time(latest_heartbeat.get('timestamp')) if latest_heartbeat else None,
            'last_system_update': last_system_update,
            'last_system_update_toronto': convert_to_toronto_time(last_system_update) if last_system_update else None,
            'public_ip': latest_heartbeat.get('public_ip') if latest_heartbeat else public_ip_from_stats,
            'uptime_seconds': latest_heartbeat.get('uptime') if latest_heartbeat else None,
            'active_connections': active_connections,
            'system_stats': latest_stats.get('stats', {}) if latest_stats else {}
        }
        
        # Debug print to see what's being returned
        print(f"DEBUG: Server {server_name} - public_ip_from_stats: {public_ip_from_stats}, final_public_ip: {status['public_ip']}")
        
        return status
    except Exception as e:
        logger.error(f"Error getting server status for {server_name}: {e}")
        return None

# API Routes
@app.route('/')
def index():
    """Serve the dashboard frontend"""
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        client = get_mongodb_client()
        if client:
            client.admin.command('ping')
            servers = get_all_servers()
            logger.info(f"Health check: Found {len(servers)} servers")
            return jsonify({
                'status': 'healthy',
                'mongodb': 'connected',
                'timestamp': datetime.utcnow().isoformat(),
                'servers_count': len(servers)
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'mongodb': 'disconnected',
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/test')
def test_endpoint():
    """Test endpoint to verify code is updated"""
    try:
        servers = get_all_servers()
        return jsonify({
            'message': 'Test endpoint working',
            'servers_found': len(servers),
            'servers': servers
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/servers')
def get_servers():
    """Get list of all servers with their status"""
    try:
        logger.info("API /api/servers called")
        servers = get_all_servers()
        logger.info(f"get_all_servers() returned {len(servers)} servers")
        server_statuses = []
        
        for server in servers:
            logger.info(f"Processing server: {server}")
            status = get_server_status(server['server_name'], server['server_location'])
            logger.info(f"get_server_status returned: {status}")
            if status:
                server_statuses.append(status)
                logger.info(f"Added status for {server['server_name']} with public_ip: {status.get('public_ip')}")
            else:
                # Include server even if no recent status data
                server_statuses.append({
                    'server_name': server['server_name'],
                    'server_location': server['server_location'],
                    'status': 'unknown',
                    'last_seen': None,
                    'last_heartbeat': None,
                    'public_ip': None,
                    'uptime_seconds': None,
                    'active_connections': 0,
                    'system_stats': {}
                })
                logger.info(f"Added unknown status for {server['server_name']}")
        
        logger.info(f"Returning {len(server_statuses)} server statuses")
        return jsonify(server_statuses)
    except Exception as e:
        logger.error(f"Error getting servers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servers/<server_name>/status')
def get_server_status_endpoint(server_name):
    """Get detailed status for a specific server"""
    try:
        # Get server location from query parameter or find it
        server_location = request.args.get('location')
        
        if not server_location:
            # Find the server location from database
            collection = get_collection()
            if collection is not None:
                server_doc = collection.find_one({'server_name': server_name})
                if server_doc:
                    server_location = server_doc.get('server_location')
        
        if not server_location:
            return jsonify({'error': 'Server location not found'}), 404
        
        status = get_server_status(server_name, server_location)
        if status:
            return jsonify(status)
        else:
            return jsonify({'error': 'Server not found'}), 404
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servers/<server_name>/connections')
def get_server_connections(server_name):
    """Get active connections for a specific server"""
    try:
        server_location = request.args.get('location')
        if not server_location:
            return jsonify({'error': 'Server location required'}), 400
        
        collection = get_collection()
        if collection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Get recent authenticated connections
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        connections = list(collection.find({
            'server_name': server_name,
            'server_location': server_location,
            'event_type': 'authenticated',
            'timestamp': {'$gte': five_minutes_ago}
        }).sort('timestamp', -1))
        
        # Convert ObjectId to string for JSON serialization
        for conn in connections:
            conn['_id'] = str(conn['_id'])
            if 'timestamp' in conn:
                conn['timestamp'] = conn['timestamp'].isoformat()
        
        return jsonify(connections)
    except Exception as e:
        logger.error(f"Error getting server connections: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/connections')
def get_connection_analytics():
    """Get connection analytics across all servers"""
    try:
        collection = get_collection()
        if collection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Get last 24 hours of data
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        # Total connections in last 24 hours
        total_connections = collection.count_documents({
            'event_type': 'authenticated',
            'timestamp': {'$gte': yesterday}
        })
        
        # Connections by server
        pipeline = [
            {'$match': {'event_type': 'authenticated', 'timestamp': {'$gte': yesterday}}},
            {'$group': {
                '_id': {
                    'server_name': '$server_name',
                    'server_location': '$server_location'
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]
        connections_by_server = list(collection.aggregate(pipeline))
        
        # Hourly connection trends
        pipeline = [
            {'$match': {'event_type': 'authenticated', 'timestamp': {'$gte': yesterday}}},
            {'$group': {
                '_id': {
                    'hour': {'$hour': '$timestamp'},
                    'server_name': '$server_name',
                    'server_location': '$server_location'
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.hour': 1}}
        ]
        hourly_trends = list(collection.aggregate(pipeline))
        
        analytics = {
            'total_connections_24h': total_connections,
            'connections_by_server': connections_by_server,
            'hourly_trends': hourly_trends,
            'period': '24h',
            'servers_count': len(get_all_servers())
        }
        
        return jsonify(analytics)
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/live/connections')
def get_live_connections():
    """Get live connection feed from all servers"""
    try:
        collection = get_collection()
        if collection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Get recent events (last 10 minutes)
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        events = list(collection.find({
            'timestamp': {'$gte': ten_minutes_ago}
        }).sort('timestamp', -1).limit(50))
        
        # Convert ObjectId to string for JSON serialization
        for event in events:
            event['_id'] = str(event['_id'])
            if 'timestamp' in event:
                event['timestamp'] = event['timestamp'].isoformat()
        
        return jsonify(events)
    except Exception as e:
        logger.error(f"Error getting live connections: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/users')
def get_user_analytics():
    """Get user activity analytics"""
    try:
        collection = get_collection()
        if collection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Get last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        # Top users by connection count
        pipeline = [
            {'$match': {'event_type': 'authenticated', 'timestamp': {'$gte': yesterday}}},
            {'$group': {'_id': '$username', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        top_users = list(collection.aggregate(pipeline))
        
        # Users by server
        pipeline = [
            {'$match': {'event_type': 'authenticated', 'timestamp': {'$gte': yesterday}}},
            {'$group': {
                '_id': {
                    'username': '$username',
                    'server_name': '$server_name',
                    'server_location': '$server_location'
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]
        users_by_server = list(collection.aggregate(pipeline))
        
        return jsonify({
            'top_users': top_users,
            'users_by_server': users_by_server,
            'period': '24h'
        })
    except Exception as e:
        logger.error(f"Error getting user analytics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/connectivity/status')
def get_connectivity_status():
    """Get connectivity status of all servers"""
    try:
        status = check_server_connectivity()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting connectivity status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/connectivity/alerts')
def get_connectivity_alerts():
    """Get connectivity alerts for servers with issues"""
    try:
        connectivity_status = check_server_connectivity()
        alerts = []
        
        for server in connectivity_status:
            if not server['is_connected']:
                alerts.append({
                    'type': 'connectivity_lost',
                    'server_name': server['server_name'],
                    'server_location': server['server_location'],
                    'message': f"Server {server['server_name']} lost connectivity",
                    'time_since_last_heartbeat': server['time_since_last_heartbeat'],
                    'severity': 'high' if server['time_since_last_heartbeat'] > 1800 else 'medium'
                })
        
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Error getting connectivity alerts: {e}")
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info('Client connected')
    emit('status', {'data': 'Connected to OpenVPN Dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info('Client disconnected')

@socketio.on('request_live_data')
def handle_live_data_request():
    """Handle live data requests"""
    try:
        collection = get_collection()
        if collection is not None:
            # Get recent events
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            events = list(collection.find({
                'timestamp': {'$gte': five_minutes_ago}
            }).sort('timestamp', -1).limit(20))
            
            # Convert ObjectId to string
            for event in events:
                event['_id'] = str(event['_id'])
                if 'timestamp' in event:
                    event['timestamp'] = event['timestamp'].isoformat()
            
            emit('live_data', {'events': events})
    except Exception as e:
        logger.error(f"Error handling live data request: {e}")
        emit('error', {'error': str(e)})

if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5000))
    host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting OpenVPN Dashboard on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"MongoDB URI: {os.getenv('MONGODB_URI', 'NOT_SET')}")
    logger.info(f"MongoDB Database: {os.getenv('MONGODB_DATABASE', 'NOT_SET')}")
    logger.info(f"MongoDB Collection: {os.getenv('MONGODB_COLLECTION', 'NOT_SET')}")
    
    # Test server detection at startup
    try:
        servers = get_all_servers()
        logger.info(f"Startup test: Found {len(servers)} servers")
    except Exception as e:
        logger.error(f"Startup test failed: {e}")
    
    socketio.run(app, host=host, port=port, debug=debug, use_reloader=False)
