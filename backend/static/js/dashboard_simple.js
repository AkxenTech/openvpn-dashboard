// OpenVPN Dashboard JavaScript (Simplified for Render)
class OpenVPNDashboard {
    constructor() {
        this.apiBase = '/api';
        this.autoRefresh = true;
        this.refreshInterval = null;
        this.connectionChart = null;
        
        this.init();
    }

    init() {
        this.loadDashboard();
        this.setupAutoRefresh();
        this.initializeCharts();
    }

    // Data Loading
    async loadDashboard() {
        try {
            await Promise.all([
                this.loadServers(),
                this.loadAnalytics(),
                this.loadConnectivityStatus()
            ]);
        } catch (error) {
            this.showError('Failed to load dashboard data: ' + error.message);
        }
    }

    async loadServers() {
        try {
            const response = await fetch(`${this.apiBase}/servers`);
            const data = await response.json();
            
            if (response.ok) {
                this.displayServers(data.servers || data);
                this.updateHeaderStats(data.servers || data);
            } else {
                throw new Error(data.error || 'Failed to load servers');
            }
        } catch (error) {
            throw error;
        }
    }

    displayServers(servers) {
        const container = document.getElementById('server-grid');
        
        if (!servers || servers.length === 0) {
            container.innerHTML = '<div class="loading">No servers found</div>';
            return;
        }

        container.innerHTML = '';
        
        servers.forEach(server => {
            const card = this.createServerCard(server);
            container.appendChild(card);
        });
    }

    createServerCard(server) {
        const card = document.createElement('div');
        card.className = `server-card ${server.status}`;
        
        const lastSeen = server.last_system_update ? new Date(server.last_system_update).toLocaleString() : 'Never';
        const uptime = server.uptime ? this.formatUptime(server.uptime) : 'Unknown';
        
        // Format disk usage with color coding
        let diskUsageHtml = '';
        if (server.disk_usage_percent !== null && server.disk_usage_percent !== undefined) {
            const diskPercent = server.disk_usage_percent;
            let diskColorClass = '';
            
            if (diskPercent <= 65) {
                diskColorClass = 'disk-usage-green';
            } else if (diskPercent > 65 && diskPercent <= 75) {
                diskColorClass = 'disk-usage-orange';
            } else if (diskPercent > 75) {
                diskColorClass = 'disk-usage-red';
            }
            
            diskUsageHtml = `
                <div class="detail">
                    <span class="label">Disk Usage:</span>
                    <span class="value ${diskColorClass}">${diskPercent.toFixed(1)}%</span>
                </div>
            `;
        }
        
        card.innerHTML = `
            <div class="server-header">
                <h3>${server.server_name}</h3>
                <span class="location">${server.server_location}</span>
            </div>
            <div class="server-status">
                <span class="status-indicator ${server.status}"></span>
                <span class="status-text">${server.status.toUpperCase()}</span>
            </div>
            <div class="server-details">
                <div class="detail">
                    <span class="label">IP:</span>
                    <span class="value">${server.public_ip || 'Unknown'}</span>
                </div>
                <div class="detail">
                    <span class="label">Uptime:</span>
                    <span class="value">${uptime}</span>
                </div>
                ${diskUsageHtml}
                <div class="detail">
                    <span class="label">Last Seen:</span>
                    <span class="value">${lastSeen}</span>
                </div>
            </div>
        `;
        
        return card;
    }

    updateHeaderStats(servers) {
        const totalServers = servers.length;
        const onlineServers = servers.filter(s => s.status === 'online').length;
        const offlineServers = servers.filter(s => s.status === 'offline').length;
        
        document.getElementById('total-servers').textContent = totalServers;
        document.getElementById('online-servers').textContent = onlineServers;
        document.getElementById('offline-servers').textContent = offlineServers;
    }

    async loadAnalytics() {
        try {
            const [connectionsResponse, usersResponse] = await Promise.all([
                fetch(`${this.apiBase}/analytics/connections?days=7`),
                fetch(`${this.apiBase}/analytics/users?days=30`)
            ]);
            
            if (connectionsResponse.ok) {
                const connectionsData = await connectionsResponse.json();
                this.updateConnectionChart(connectionsData);
            }
            
            if (usersResponse.ok) {
                const usersData = await usersResponse.json();
                this.updateUserAnalytics(usersData);
            }
        } catch (error) {
            console.error('Failed to load analytics:', error);
        }
    }

    updateConnectionChart(data) {
        const ctx = document.getElementById('connection-chart');
        if (!ctx) return;
        
        if (this.connectionChart) {
            this.connectionChart.destroy();
        }
        
        const analytics = data.analytics || [];
        const labels = analytics.map(item => item._id);
        const datasets = [];
        
        // Group by server
        const serverData = {};
        analytics.forEach(item => {
            item.servers.forEach(server => {
                const serverKey = `${server.server_name} - ${server.server_location}`;
                if (!serverData[serverKey]) {
                    serverData[serverKey] = new Array(labels.length).fill(0);
                }
                const index = labels.indexOf(item._id);
                if (index !== -1) {
                    serverData[serverKey][index] = server.connections;
                }
            });
        });
        
        // Create datasets for each server
        const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];
        let colorIndex = 0;
        
        Object.keys(serverData).forEach(serverName => {
            datasets.push({
                label: serverName,
                data: serverData[serverName],
                borderColor: colors[colorIndex % colors.length],
                backgroundColor: colors[colorIndex % colors.length] + '20',
                tension: 0.1
            });
            colorIndex++;
        });
        
        this.connectionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Connection Trends (Last 7 Days)'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    updateUserAnalytics(data) {
        const container = document.getElementById('user-analytics');
        if (!container) return;
        
        const users = data.users || [];
        
        if (users.length === 0) {
            container.innerHTML = '<p>No user data available</p>';
            return;
        }
        
        const html = users.slice(0, 10).map(user => {
            // Format server list
            const servers = user.servers || [];
            const serverList = servers.length > 0 ? servers.join(', ') : 'No servers';
            
            return `
                <div class="user-item">
                    <div class="user-info">
                        <span class="username">${user._id}</span>
                        <span class="connection-count">${user.connection_count} connections</span>
                    </div>
                    <div class="user-details">
                        <span class="last-connection">Last: ${new Date(user.last_connection).toLocaleDateString()}</span>
                        <span class="servers">Servers: ${serverList}</span>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = html;
    }

    async loadConnectivityStatus() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            const data = await response.json();
            
            if (response.ok) {
                this.updateConnectivityStatus(data);
            }
        } catch (error) {
            console.error('Failed to load connectivity status:', error);
        }
    }

    updateConnectivityStatus(data) {
        const statusElement = document.getElementById('connectivity-status');
        if (!statusElement) return;
        
        const isHealthy = data.status === 'healthy';
        statusElement.className = `status-indicator ${isHealthy ? 'online' : 'offline'}`;
        statusElement.textContent = isHealthy ? 'Connected' : 'Disconnected';
    }

    setupAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.autoRefresh) {
            this.refreshInterval = setInterval(() => {
                this.loadDashboard();
            }, 30000); // Refresh every 30 seconds
        }
    }

    initializeCharts() {
        // Charts are initialized when data is loaded
    }

    formatUptime(uptime) {
        if (!uptime) return 'Unknown';
        
        const seconds = parseInt(uptime);
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }

    showError(message) {
        const errorContainer = document.getElementById('error-container');
        if (errorContainer) {
            errorContainer.innerHTML = `<div class="error-message">${message}</div>`;
            errorContainer.style.display = 'block';
            
            setTimeout(() => {
                errorContainer.style.display = 'none';
            }, 5000);
        }
        console.error(message);
    }

    toggleAutoRefresh() {
        this.autoRefresh = !this.autoRefresh;
        this.setupAutoRefresh();
        
        const button = document.getElementById('auto-refresh-btn');
        if (button) {
            button.textContent = this.autoRefresh ? 'Disable Auto-Refresh' : 'Enable Auto-Refresh';
            button.className = this.autoRefresh ? 'btn btn-secondary' : 'btn btn-primary';
        }
    }

    clearFeed() {
        const feedContainer = document.getElementById('live-feed');
        if (feedContainer) {
            feedContainer.innerHTML = '<div class="feed-empty">Feed cleared</div>';
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new OpenVPNDashboard();
    
    // Setup event listeners
    const autoRefreshBtn = document.getElementById('auto-refresh-btn');
    if (autoRefreshBtn) {
        autoRefreshBtn.addEventListener('click', () => {
            window.dashboard.toggleAutoRefresh();
        });
    }
    
    const clearFeedBtn = document.getElementById('clear-feed-btn');
    if (clearFeedBtn) {
        clearFeedBtn.addEventListener('click', () => {
            window.dashboard.clearFeed();
        });
    }
});
