"""Gunicorn configuration file for TRIAS API server"""

import multiprocessing
import os

# Server socket
# Port 80 requires root or CAP_NET_BIND_SERVICE capability
# Use 8080 for non-root users or set USE_PORT_80=true in environment
use_port_80 = os.environ.get('USE_PORT_80', 'false').lower() == 'true'
port = 80 if use_port_80 else 8080
bind = f"0.0.0.0:{port}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/trias/access.log"
errorlog = "/var/log/trias/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "trias-api"

# Server mechanics
daemon = False
pidfile = "/var/run/trias/gunicorn.pid"
user = None
group = None
umask = 0
tmp_upload_dir = None

# SSL (uncomment if using HTTPS)
# keyfile = "/etc/ssl/private/trias.key"
# certfile = "/etc/ssl/certs/trias.crt"
