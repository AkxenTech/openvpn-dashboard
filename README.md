# OpenVPN Dashboard

Multi-server OpenVPN monitoring dashboard connecting to MongoDB Atlas.

## 🎯 **Overview**

A real-time web dashboard for monitoring multiple OpenVPN servers, displaying connection events, system statistics, and analytics from your centralized MongoDB database.

## ✨ **Features**

- **Real-time server monitoring** - Live status of all VPN servers
- **Connection tracking** - Active users and connection events
- **System health metrics** - CPU, memory, disk usage per server
- **Historical analytics** - Connection trends and patterns
- **Geographic visualization** - Server locations and user distribution
- **Live data updates** - WebSocket-powered real-time updates
- **Responsive design** - Works on desktop and mobile devices

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VPN Server 1  │    │   VPN Server 2  │    │   VPN Server N  │
│                 │    │                 │    │                 │
│ OpenVPN Logger  │    │ OpenVPN Logger  │    │ OpenVPN Logger  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │     MongoDB Atlas         │
                    │   (Central Database)      │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    Dashboard Backend      │
                    │     (Flask API)           │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   Dashboard Frontend      │
                    │   (HTML/CSS/JavaScript)   │
                    └───────────────────────────┘
```

## 🚀 **Quick Start**

### Prerequisites

- Python 3.7+
- MongoDB Atlas cluster (shared with VPN servers)
- Modern web browser

### Installation

```bash
# Clone the repository
git clone https://github.com/AkxenTech/openvpn-dashboard.git
cd openvpn-dashboard

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB connection details

# Run the dashboard
python app.py
```

### Configuration

Create a `.env` file in the backend directory:

```env
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/openvpn_logs
MONGODB_DATABASE=openvpn_logs
MONGODB_COLLECTION=connection_logs

# Dashboard Configuration
DASHBOARD_PORT=5000
DASHBOARD_HOST=0.0.0.0
REFRESH_INTERVAL=30

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here
```

## 📊 **Data Sources**

The dashboard connects to your existing MongoDB Atlas cluster and reads from the collections created by your OpenVPN Logger:

### Connection Events
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "event_type": "connect|disconnect|authenticated",
  "client_ip": "192.168.1.100",
  "client_port": 12345,
  "username": "user123",
  "server_name": "vpn-server-01",
  "server_location": "us-east-1"
}
```

### System Statistics
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "type": "system_stats",
  "stats": {
    "cpu_percent": 15.2,
    "memory_percent": 45.8,
    "disk_percent": 67.3
  },
  "server_name": "vpn-server-01",
  "server_location": "us-east-1"
}
```

## 🔌 **API Endpoints**

### Server Status
- `GET /api/health` - Dashboard health check
- `GET /api/servers` - List all servers
- `GET /api/servers/<server_name>/status` - Server status
- `GET /api/servers/<server_name>/connections` - Active connections

### Analytics
- `GET /api/analytics/connections` - Connection statistics
- `GET /api/analytics/trends` - Historical trends
- `GET /api/analytics/users` - User activity

### Real-time Data
- `GET /api/live/connections` - Live connection feed
- `GET /api/live/events` - Real-time events
- `WebSocket /ws` - WebSocket for live updates

## 🛠️ **Development**

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Frontend Development
```bash
cd frontend
# Edit HTML/CSS/JavaScript files
# Open index.html in browser
```

## 🐳 **Docker Deployment**

```bash
# Build and run with Docker
docker-compose up -d
```

## 📱 **Dashboard Features**

### Server Overview
- **Server status cards** with online/offline indicators
- **Active connection counts** per server
- **System resource usage** (CPU, memory, disk)
- **Geographic server locations**

### Real-time Monitoring
- **Live connection feed** with recent events
- **User activity tracking** with timestamps
- **Connection/disconnection events**
- **Server health indicators**

### Analytics & Reports
- **Connection trends** over time
- **Peak usage hours** analysis
- **Top users** and IP addresses
- **Server performance** metrics

## 🔧 **Troubleshooting**

### Common Issues

1. **MongoDB Connection Failed**
   - Verify your MongoDB Atlas connection string
   - Check network connectivity
   - Ensure IP whitelist includes dashboard server

2. **No Data Displayed**
   - Verify OpenVPN Logger is running on servers
   - Check MongoDB collections exist
   - Review server names in configuration

3. **WebSocket Connection Issues**
   - Check firewall settings
   - Verify WebSocket port is accessible
   - Review browser console for errors

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 **Support**

For issues and questions:
- Check the troubleshooting section
- Review the API documentation
- Open an issue on GitHub

## 🔗 **Related Projects**

- [OpenVPN Logger](https://github.com/AkxenTech/openvpn-logger) - The data collection service
- [MongoDB Atlas](https://cloud.mongodb.com) - Cloud database service
