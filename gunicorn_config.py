"""Gunicorn configuration file for TRIAS API server"""

import multiprocessing

# Server socket
bind = "0.0.0.0:80"
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
