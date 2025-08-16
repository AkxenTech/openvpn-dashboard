// OpenVPN Dashboard JavaScript
class OpenVPNDashboard {
    constructor() {
        this.apiBase = '/api';
        this.wsUrl = window.location.origin;
        this.socket = null;
        this.autoRefresh = true;
        this.refreshInterval = null;
        this.connectionChart = null;
        
        this.init();
    }

    init() {
        this.initializeWebSocket();
        this.loadDashboard();
        this.setupAutoRefresh();
        this.initializeCharts();
    }

    // WebSocket Management
    initializeWebSocket() {
        try {
            this.socket = io(this.wsUrl);
            
            this.socket.on('connect', () => {
                this.updateConnectionStatus(true);
                console.log('Connected to WebSocket');
                this.socket.emit('request_live_data');
            });

            this.socket.on('disconnect', () => {
                this.updateConnectionStatus(false);
                console.log('Disconnected from WebSocket');
            });

            this.socket.on('live_data', (data) => {
                this.updateLiveFeed(data.events);
            });

            this.socket.on('error', (data) => {
                this.showError('WebSocket error: ' + data.error);
            });
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.updateConnectionStatus(false);
        }
    }

    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('connection-status');
        const statusText = document.getElementById('connection-text');
        
        if (connected) {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.remove('connected');
            statusText.textContent = 'Disconnected';
        }
    }

    // Data Loading
    async loadDashboard() {
        try {
            await Promise.all([
                this.loadServers(),
                this.loadAnalytics(),
                this.loadLiveFeed(),
                this.loadConnectivityStatus()
            ]);
        } catch (error) {
            this.showError('Failed to load dashboard data: ' + error.message);
        }
    }

    async loadServers() {
        try {
            const response = await fetch(`${this.apiBase}/servers`);
            const servers = await response.json();
            
            if (response.ok) {
                this.displayServers(servers);
                this.updateHeaderStats(servers);
            } else {
                throw new Error(servers.error || 'Failed to load servers');
            }
        } catch (error) {
            throw error;
        }
    }

    displayServers(servers) {
        const container = document.getElementById('server-grid');
        
        if (servers.length === 0) {
            container.innerHTML = '<div class="loading">No servers found</div>';
            return;
        }

        const serversHtml = servers.map(server => this.createServerCard(server)).join('');
        container.innerHTML = serversHtml;
    }

    createServerCard(server) {
        const statusClass = server.status === 'online' ? 'online' : 'offline';
        const uptime = server.uptime_seconds ? this.formatUptime(server.uptime_seconds) : 'Unknown';
        const lastSeen = server.last_seen ? new Date(server.last_seen).toLocaleString() : 'Never';
        
        return `
            <div class="server-card ${statusClass}">
                <div class="server-header">
                    <div class="server-name">${server.server_name}</div>
                    <span class="server-status ${statusClass}">${server.status}</span>
                </div>
                <div class="server-location">${server.server_location}</div>
                <div class="server-stats">
                    <div class="stat-mini">
                        <div class="stat-mini-value">${server.active_connections}</div>
                        <div class="stat-mini-label">Active</div>
                    </div>
                    <div class="stat-mini">
                        <div class="stat-mini-value">${uptime}</div>
                        <div class="stat-mini-label">Uptime</div>
                    </div>
                    <div class="stat-mini">
                        <div class="stat-mini-value">${server.public_ip || 'N/A'}</div>
                        <div class="stat-mini-label">IP</div>
                    </div>
                </div>
                <div style="font-size: 0.8rem; color: #666; margin-top: 10px;">
                    Last seen: ${lastSeen}
                </div>
            </div>
        `;
    }

    updateHeaderStats(servers) {
        const totalServers = servers.length;
        const onlineServers = servers.filter(s => s.status === 'online').length;
        
        document.getElementById('total-servers').textContent = totalServers;
        document.getElementById('online-servers').textContent = onlineServers;
    }

    async loadAnalytics() {
        try {
            const response = await fetch(`${this.apiBase}/analytics/connections`);
            const analytics = await response.json();
            
            if (response.ok) {
                this.displayAnalytics(analytics);
                document.getElementById('total-connections').textContent = analytics.total_connections_24h || 0;
            } else {
                throw new Error(analytics.error || 'Failed to load analytics');
            }
        } catch (error) {
            throw error;
        }
    }

    displayAnalytics(analytics) {
        this.updateConnectionChart(analytics);
        this.updateServerPerformance(analytics);
    }

    updateConnectionChart(analytics) {
        if (!this.connectionChart) return;

        const ctx = document.getElementById('connection-chart').getContext('2d');
        
        // Prepare data for chart
        const labels = [];
        const data = [];
        
        // Group by hour
        const hourlyData = {};
        analytics.hourly_trends.forEach(item => {
            const hour = item._id.hour;
            if (!hourlyData[hour]) {
                hourlyData[hour] = 0;
            }
            hourlyData[hour] += item.count;
        });

        // Fill in all 24 hours
        for (let i = 0; i < 24; i++) {
            labels.push(`${i}:00`);
            data.push(hourlyData[i] || 0);
        }

        this.connectionChart.data.labels = labels;
        this.connectionChart.data.datasets[0].data = data;
        this.connectionChart.update();
    }

    updateServerPerformance(analytics) {
        const container = document.getElementById('server-performance');
        
        if (!analytics.connections_by_server || analytics.connections_by_server.length === 0) {
            container.innerHTML = '<div class="loading">No performance data available</div>';
            return;
        }

        const performanceHtml = analytics.connections_by_server.map(server => `
            <div style="margin-bottom: 10px; padding: 8px; background: #f8f9fa; border-radius: 5px;">
                <div style="font-weight: bold;">${server._id.server_name}</div>
                <div style="color: #666; font-size: 0.9rem;">${server._id.server_location}</div>
                <div style="color: #667eea; font-weight: bold;">${server.count} connections</div>
            </div>
        `).join('');

        container.innerHTML = performanceHtml;
    }

    async loadLiveFeed() {
        try {
            const response = await fetch(`${this.apiBase}/live/connections`);
            const events = await response.json();
            
            if (response.ok) {
                this.updateLiveFeed(events);
            } else {
                throw new Error(events.error || 'Failed to load live feed');
            }
        } catch (error) {
            throw error;
        }
    }

    updateLiveFeed(events) {
        const container = document.getElementById('event-list');
        
        if (!events || events.length === 0) {
            container.innerHTML = '<div class="loading">No recent events</div>';
            return;
        }

        const eventsHtml = events.map(event => this.createEventItem(event)).join('');
        container.innerHTML = eventsHtml;
    }

    createEventItem(event) {
        const eventType = event.event_type || event.type || 'unknown';
        const username = event.username || 'Unknown';
        const clientIp = event.client_ip || 'N/A';
        const serverName = event.server_name || 'Unknown';
        const timestamp = event.timestamp ? new Date(event.timestamp).toLocaleString() : 'Unknown';
        
        return `
            <div class="event-item">
                <div class="event-info">
                    <div class="event-user">${username}</div>
                    <div class="event-details">
                        ${clientIp} • ${serverName} • ${timestamp}
                    </div>
                </div>
                <span class="event-type event-${eventType}">${eventType}</span>
            </div>
        `;
    }

    async loadConnectivityStatus() {
        try {
            const response = await fetch(`${this.apiBase}/connectivity/status`);
            const status = await response.json();
            
            if (response.ok) {
                this.checkConnectivityAlerts(status);
            }
        } catch (error) {
            console.error('Error loading connectivity status:', error);
        }
    }

    checkConnectivityAlerts(connectivityStatus) {
        connectivityStatus.forEach(server => {
            if (!server.is_connected) {
                this.showAlert(`Server ${server.server_name} lost connectivity`, 'warning');
            }
        });
    }

    // Chart Initialization
    initializeCharts() {
        const ctx = document.getElementById('connection-chart');
        if (ctx) {
            this.connectionChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Connections',
                        data: [],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0,0,0,0.1)'
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(0,0,0,0.1)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
    }

    // Utility Functions
    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }

    setupAutoRefresh() {
        if (this.autoRefresh) {
            this.refreshInterval = setInterval(() => {
                this.loadDashboard();
            }, 30000); // Refresh every 30 seconds
        }
    }

    toggleAutoRefresh() {
        this.autoRefresh = !this.autoRefresh;
        const button = document.getElementById('auto-refresh-text');
        
        if (this.autoRefresh) {
            button.textContent = 'Auto Refresh: ON';
            this.setupAutoRefresh();
        } else {
            button.textContent = 'Auto Refresh: OFF';
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
                this.refreshInterval = null;
            }
        }
    }

    refreshData() {
        this.loadDashboard();
    }

    clearFeed() {
        const container = document.getElementById('event-list');
        container.innerHTML = '<div class="loading">Feed cleared</div>';
    }

    // Error and Alert Handling
    showError(message) {
        const container = document.getElementById('error-container');
        container.innerHTML = `<div class="alert alert-danger">❌ ${message}</div>`;
        container.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            container.style.display = 'none';
        }, 5000);
    }

    showAlert(message, type = 'info') {
        const container = document.getElementById('error-container');
        const alertClass = `alert alert-${type}`;
        const icon = type === 'success' ? '✅' : type === 'warning' ? '⚠️' : type === 'danger' ? '❌' : 'ℹ️';
        
        container.innerHTML = `<div class="${alertClass}">${icon} ${message}</div>`;
        container.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            container.style.display = 'none';
        }, 5000);
    }
}

// Global functions for HTML onclick handlers
function refreshData() {
    if (window.dashboard) {
        window.dashboard.refreshData();
    }
}

function toggleAutoRefresh() {
    if (window.dashboard) {
        window.dashboard.toggleAutoRefresh();
    }
}

function clearFeed() {
    if (window.dashboard) {
        window.dashboard.clearFeed();
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new OpenVPNDashboard();
});
