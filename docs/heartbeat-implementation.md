# Heartbeat Implementation for OpenVPN Logger

## Overview
Add heartbeat monitoring to track MongoDB connectivity and detect public IP changes.

## Implementation Steps

### 1. Add Heartbeat Function to OpenVPN Logger

Add this to your `openvpn_logger.py`:

```python
import requests
import socket

def get_public_ip():
    """Get current public IP address"""
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text
    except:
        try:
            # Fallback method
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"

def log_heartbeat():
    """Log a heartbeat to track MongoDB connectivity"""
    try:
        heartbeat_data = {
            'timestamp': datetime.utcnow(),
            'type': 'heartbeat',
            'server_name': os.getenv('SERVER_NAME'),
            'server_location': os.getenv('SERVER_LOCATION'),
            'mongodb_status': 'connected',
            'public_ip': get_public_ip(),
            'version': '1.0.0',
            'uptime': time.time() - start_time
        }
        
        collection.insert_one(heartbeat_data)
        logger.info(f"Heartbeat logged - IP: {heartbeat_data['public_ip']}")
        return True
    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")
        return False

# Add to main monitoring loop
def main():
    last_heartbeat = 0
    heartbeat_interval = 300  # 5 minutes
    
    while True:
        try:
            # Existing monitoring code...
            
            # Send heartbeat every 5 minutes
            current_time = time.time()
            if current_time - last_heartbeat >= heartbeat_interval:
                if log_heartbeat():
                    last_heartbeat = current_time
                
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            time.sleep(60)
```

### 2. Add Dependencies

Add to `requirements.txt`:
```
requests==2.31.0
```

### 3. Dashboard Backend Monitoring

Add connectivity monitoring to dashboard backend:

```python
def check_server_connectivity():
    """Check connectivity status of all servers"""
    try:
        collection = get_collection()
        if not collection:
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

@app.route('/api/connectivity/status')
def get_connectivity_status():
    """Get connectivity status of all servers"""
    try:
        status = check_server_connectivity()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Benefits

1. **Real-time connectivity monitoring** - Know immediately if a server loses MongoDB connection
2. **Public IP tracking** - Detect when server IPs change
3. **Uptime monitoring** - Track how long servers have been running
4. **Early warning system** - Alert before connection issues become critical

## Dashboard Integration

Add connectivity status to dashboard:

```javascript
// Add to dashboard.js
async function loadConnectivityStatus() {
    try {
        const response = await fetch('/api/connectivity/status');
        const status = await response.json();
        
        // Update connectivity indicators
        status.forEach(server => {
            if (!server.is_connected) {
                showAlert(`Server ${server.server_name} lost connectivity`);
            }
        });
    } catch (error) {
        console.error('Error loading connectivity status:', error);
    }
}
```

## Alerting

Set up alerts for:
- Server not sending heartbeats for >10 minutes
- Public IP changes
- MongoDB connection failures
- Server uptime resets
