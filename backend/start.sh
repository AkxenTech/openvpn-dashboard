#!/usr/bin/env bash
# Startup script for Render deployment

echo "Starting OpenVPN Dashboard..."

# Set environment variables for production
export FLASK_ENV=production
export FLASK_DEBUG=False

# Start the application with Gunicorn using the simplified app
exec gunicorn --config gunicorn.conf.py app_simple:app
