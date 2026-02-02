# Test Commands for Proxmox LXC Container

## Check if service is running
```bash
systemctl status trias
```

## Restart the service
```bash
sudo systemctl restart trias
```

## View logs
```bash
sudo journalctl -u trias -f
```

## Check if port is listening
```bash
sudo netstat -tlnp | grep 8080
```

## Test the API directly
```bash
# Test departures endpoint
curl -s "http://localhost:8080/api/departures?stop_id=at:49:4902:0:1&limit=5" | python3 -m json.tool

# Test nearby search (Vienna coordinates)
curl -s "http://localhost:8080/api/search/nearby?lat=48.2082&lon=16.3738&radius=500&limit=10" | python3 -m json.tool
```

## If you need to test directly without service (development mode)
```bash
cd /opt/trias
source .venv/bin/activate
python app.py
```
