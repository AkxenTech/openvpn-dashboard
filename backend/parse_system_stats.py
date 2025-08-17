#!/usr/bin/env python3
"""
Parse system stats documents to extract timestamp and public IP
"""

import json
from datetime import datetime
import pytz

def parse_system_stats_document(doc_str):
    """Parse a system stats document and extract key information"""
    
    # Parse the JSON document
    doc = json.loads(doc_str)
    
    # Extract timestamp
    timestamp_str = doc.get('timestamp', {}).get('$date')
    if timestamp_str:
        # Parse ISO format timestamp
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    else:
        timestamp = None
    
    # Extract public IP from interfaces
    public_ip = None
    interfaces = doc.get('interfaces', {})
    
    # Priority order for public IP detection
    # 1. ens4 (usually external interface)
    # 2. enp1s0 (alternative external interface)
    # 3. ens3 (internal interface)
    # 4. Any interface that's not loopback or tunnel
    
    if 'ens4' in interfaces:
        public_ip = interfaces['ens4'].get('ip')
    elif 'enp1s0' in interfaces:
        public_ip = interfaces['enp1s0'].get('ip')
    elif 'ens3' in interfaces:
        public_ip = interfaces['ens3'].get('ip')
    else:
        # Find any interface that's not loopback or tunnel
        for interface_name, interface_data in interfaces.items():
            if interface_name not in ['lo', 'tun0', 'tun1']:
                public_ip = interface_data.get('ip')
                break
    
    # Extract system stats
    stats = doc.get('stats', {})
    
    # Extract server info
    server_name = doc.get('server_name')
    server_location = doc.get('server_location')
    
    return {
        'timestamp': timestamp,
        'timestamp_iso': timestamp.isoformat() if timestamp else None,
        'public_ip': public_ip,
        'server_name': server_name,
        'server_location': server_location,
        'cpu_percent': stats.get('cpu_percent', 0),
        'memory_percent': stats.get('memory_percent', 0),
        'disk_percent': stats.get('disk_percent', 0),
        'memory_available': stats.get('memory_available', {}).get('$numberLong', 0),
        'disk_free': stats.get('disk_free', {}).get('$numberLong', 0),
        'interfaces': interfaces
    }

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
        print(f"Error converting timezone: {e}")
        return utc_time

def test_parsing():
    """Test parsing the provided document"""
    
    # Your provided document
    doc_str = '''{
  "_id": {
    "$oid": "68a0f5b2e2b6182bc00da9fe"
  },
  "timestamp": {
    "$date": "2025-08-16T21:18:42.773Z"
  },
  "type": "system_stats",
  "stats": {
    "cpu_percent": 0,
    "memory_percent": 3.3,
    "memory_available": {
      "$numberLong": "19799859200"
    },
    "disk_percent": 32.3,
    "disk_free": {
      "$numberLong": "33578090496"
    }
  },
  "interfaces": {
    "lo": {
      "ip": "127.0.0.1",
      "netmask": "255.0.0.0"
    },
    "ens3": {
      "ip": "10.8.1.1",
      "netmask": "255.255.255.0"
    },
    "ens4": {
      "ip": "172.16.180.12",
      "netmask": "255.255.255.0"
    },
    "tun0": {
      "ip": "10.8.0.1",
      "netmask": "255.255.255.0"
    }
  },
  "server_name": "openvpn-server-01",
  "server_location": "us-east-1"
}'''
    
    # Parse the document
    result = parse_system_stats_document(doc_str)
    
    print("Parsed System Stats Document:")
    print("=" * 50)
    print(f"Server: {result['server_name']} ({result['server_location']})")
    print(f"Timestamp (UTC): {result['timestamp']}")
    print(f"Timestamp (Toronto): {convert_to_toronto_time(result['timestamp'])}")
    print(f"Public IP: {result['public_ip']}")
    print(f"CPU: {result['cpu_percent']}%")
    print(f"Memory: {result['memory_percent']}%")
    print(f"Disk: {result['disk_percent']}%")
    print(f"Memory Available: {result['memory_available']} bytes")
    print(f"Disk Free: {result['disk_free']} bytes")
    
    print("\nAll Interfaces:")
    for interface_name, interface_data in result['interfaces'].items():
        print(f"  {interface_name}: {interface_data['ip']}/{interface_data['netmask']}")

if __name__ == '__main__':
    test_parsing()
