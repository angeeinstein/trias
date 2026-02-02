# Port 80 Permission Issue - Quick Fix

## The Problem
Gunicorn cannot bind to port 80 because it's a privileged port (requires root access), but the service runs as the `trias` user for security.

## Solution 1: Use Port 8080 (Recommended - Already Applied)

The service is now configured to use port 8080 by default. Simply restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart trias
```

Access at: **http://your-server:8080**

## Solution 2: Enable Port 80 with Capabilities

If you need port 80, edit the service file:

```bash
sudo nano /etc/systemd/system/trias.service
```

Change these two lines:
```ini
# FROM:
Environment="USE_PORT_80=false"
# AmbientCapabilities=CAP_NET_BIND_SERVICE

# TO:
Environment="USE_PORT_80=true"
AmbientCapabilities=CAP_NET_BIND_SERVICE
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart trias
sudo systemctl status trias
```

Update firewall:
```bash
# UFW
sudo ufw allow 80/tcp

# OR firewalld
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload
```

Access at: **http://your-server**

## Solution 3: Use Nginx Reverse Proxy (Production Recommended)

Keep the app on port 8080 and use nginx on port 80:

```bash
sudo apt install nginx  # Ubuntu/Debian
# OR
sudo yum install nginx  # CentOS/RHEL
```

Create nginx config:
```bash
sudo nano /etc/nginx/sites-available/trias
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # or your server IP

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and start:
```bash
sudo ln -s /etc/nginx/sites-available/trias /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Access at: **http://your-server**

## Verify It's Working

```bash
# Check service status
sudo systemctl status trias

# Check which port is listening
sudo netstat -tlnp | grep gunicorn
# OR
sudo ss -tlnp | grep gunicorn

# Test the connection
curl http://localhost:8080  # or :80 if using port 80
```

## Current Configuration

- **Default Port**: 8080 (non-privileged)
- **Service runs as**: `trias` user (non-root)
- **Configuration**: `/opt/trias/gunicorn_config.py`
- **Service file**: `/etc/systemd/system/trias.service`
