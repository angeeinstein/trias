# TRIAS API Server - Production Deployment

Complete Flask server for the TRIAS public transit API with production-ready deployment.

## Quick Start (Linux Server)

### Automated Installation

Run the comprehensive installation script:

```bash
sudo bash install.sh
```

The script will automatically:
- ✅ Install all system dependencies (Python, pip, etc.)
- ✅ Create application user and directories
- ✅ Set up Python virtual environment
- ✅ Install all Python packages
- ✅ Configure gunicorn for production
- ✅ Set up systemd service for auto-start
- ✅ Configure firewall (port 80)
- ✅ Start the service
- ✅ Handle all permissions

**No manual configuration needed!**

### What the Script Handles

#### Installation Types
- **Fresh Install**: Complete new installation
- **Update**: Update existing installation (preserves data)
- **Reinstall**: Remove and install fresh
- **Uninstall**: Complete removal

#### OS Support
- Ubuntu/Debian
- CentOS/RHEL/Fedora
- Automatic package manager detection

#### Error Handling
- Missing packages → Automatic installation
- Permission issues → Automatic fixes
- Existing installation → Interactive menu
- Service failures → Detailed error logs

### Installation Menu

```
================================
TRIAS API Server Installation
================================

1) Update existing installation
2) Reinstall (remove and install fresh)
3) Uninstall
4) View service status
5) View logs
6) Restart service
7) Exit
```

## Post-Installation

### Access the Application

After installation, access the web interface at:
- **Local**: http://localhost
- **Network**: http://YOUR_SERVER_IP

The service runs on **port 80** (standard HTTP port).

### Service Management

```bash
# View status
sudo systemctl status trias

# Start service
sudo systemctl start trias

# Stop service
sudo systemctl stop trias

# Restart service
sudo systemctl restart trias

# View logs
sudo journalctl -u trias -f

# View error logs
sudo tail -f /var/log/trias/error.log

# View access logs
sudo tail -f /var/log/trias/access.log
```

### Configuration Files

All files are installed to `/opt/trias/`:
- Application code
- Virtual environment
- Configuration files

Configuration:
- **Gunicorn**: `/opt/trias/gunicorn_config.py`
- **Service**: `/etc/systemd/system/trias.service`
- **Logs**: `/var/log/trias/`

### Updating the Application

To update after pulling new code:

```bash
sudo bash install.sh
# Choose option 1: Update existing installation
```

The script will:
- Create automatic backup
- Update files
- Upgrade dependencies
- Restart service
- Keep backup in case of issues

## Development (Windows/Local)

For local development without production setup:

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
```

Access at: http://localhost:5000

## Production Configuration

### Gunicorn Settings

Edit [gunicorn_config.py](gunicorn_config.py):

```python
# Server binding
bind = "0.0.0.0:80"

# Workers (auto-calculated based on CPU cores)
workers = multiprocessing.cpu_count() * 2 + 1

# Logging
accesslog = "/var/log/trias/access.log"
errorlog = "/var/log/trias/error.log"
```

### Performance Tuning

The gunicorn configuration automatically scales workers based on CPU cores:
- **Formula**: (CPU cores × 2) + 1
- **Example**: 4-core server = 9 workers
- **Max connections per worker**: 1000
- **Request timeout**: 30 seconds

### Security

The installation:
- ✅ Runs as non-root user (`trias`)
- ✅ Restricted directory permissions
- ✅ Isolated virtual environment
- ✅ Systemd service isolation
- ✅ Automatic restart on failure

### HTTPS/SSL Setup

To enable HTTPS, edit `gunicorn_config.py` and uncomment:

```python
keyfile = "/etc/ssl/private/trias.key"
certfile = "/etc/ssl/certs/trias.crt"
```

Then restart the service:
```bash
sudo systemctl restart trias
```

## Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status trias

# View detailed logs
sudo journalctl -u trias -n 100 --no-pager

# Check error log
sudo cat /var/log/trias/error.log
```

### Port 80 Already in Use

```bash
# Check what's using port 80
sudo lsof -i :80

# Stop conflicting service (e.g., Apache)
sudo systemctl stop apache2
```

### Permission Issues

```bash
# Fix permissions
sudo chown -R trias:trias /opt/trias
sudo chown -R trias:trias /var/log/trias
sudo chmod -R 755 /opt/trias
```

### Python Dependency Issues

```bash
# Reinstall dependencies
cd /opt/trias
sudo -u trias ./venv/bin/pip install -r requirements.txt --force-reinstall
sudo systemctl restart trias
```

### Reinstall Everything

```bash
sudo bash install.sh
# Choose option 2: Reinstall
```

## Architecture

```
┌─────────────────────┐
│   Browser Client    │
└──────────┬──────────┘
           │ HTTP (Port 80)
┌──────────▼──────────┐
│   Gunicorn (WSGI)   │
│   Multiple Workers  │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   Flask App         │
│   (app.py)          │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   TRIAS Client      │
│   (trias_client.py) │
└──────────┬──────────┘
           │ HTTP POST (XML)
┌──────────▼──────────┐
│   TRIAS API         │
│   (Verbund Linie)   │
└─────────────────────┘
```

## API Endpoints

Same as before:
- `GET /` - Web interface
- `GET /api/search/location` - Search stops by name
- `GET /api/search/nearby` - Find nearby stops
- `GET /api/departures` - Get departures

## Files Created by Installation

```
/opt/trias/                     # Application directory
├── app.py
├── trias_client.py
├── config.py
├── gunicorn_config.py
├── requirements.txt
├── trias.service
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
└── venv/                       # Python virtual environment

/etc/systemd/system/
└── trias.service              # Systemd service file

/var/log/trias/                # Log files
├── access.log
└── error.log

/var/run/trias/                # Runtime files
└── gunicorn.pid
```

## Firewall Configuration

The script automatically configures:
- **UFW** (Ubuntu/Debian): `ufw allow 80/tcp`
- **Firewalld** (CentOS/RHEL): `firewall-cmd --add-port=80/tcp`

## System Requirements

- **OS**: Linux (Ubuntu 18.04+, Debian 9+, CentOS 7+, RHEL 7+, Fedora)
- **Python**: 3.6 or higher
- **RAM**: 512 MB minimum, 1 GB recommended
- **Disk**: 500 MB for application and dependencies
- **Network**: Internet access to reach TRIAS API

## Backup and Recovery

### Manual Backup

```bash
# Backup application
sudo tar -czf trias-backup-$(date +%Y%m%d).tar.gz /opt/trias

# Backup logs
sudo tar -czf trias-logs-$(date +%Y%m%d).tar.gz /var/log/trias
```

### Restore from Backup

```bash
# Stop service
sudo systemctl stop trias

# Restore files
sudo tar -xzf trias-backup-YYYYMMDD.tar.gz -C /

# Restart service
sudo systemctl start trias
```

## Contributing

This is a client implementation for the TRIAS (Verbund Linie) OGD API.

## License

Public transit data provided by Verbund Linie OGD.
