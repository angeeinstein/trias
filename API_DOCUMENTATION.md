# TRIAS API Documentation

## Getting Departure Information for a Stop

### Step 1: Finding a Stop and Getting its Stop ID

You need to obtain a **Stop ID** before you can query departure information. There are two ways to find stops:

#### Option A: Search by Name

**Endpoint:** `GET /api/search`

**Parameters:**
- `query` (required): Search term (e.g., "Jakominiplatz", "Hauptbahnhof")

**Example Request:**
```bash
curl "http://localhost:8080/api/search?query=Jakominiplatz"
```

**Example Response:**
```json
{
  "results": [
    {
      "stop_id": "AT:47:1234:1:1",
      "stop_name": "Graz Jakominiplatz",
      "locality": "Graz",
      "lat": 47.0707,
      "lon": 15.4395
    },
    {
      "stop_id": "AT:47:1234:1:2",
      "stop_name": "Graz Jakominiplatz/Ost",
      "locality": "Graz",
      "lat": 47.0710,
      "lon": 15.4400
    }
  ]
}
```

#### Option B: Search by Coordinates (Nearby Stops)

**Endpoint:** `GET /api/nearby`

**Parameters:**
- `lat` (required): Latitude (e.g., 47.0707)
- `lon` (required): Longitude (e.g., 15.4395)
- `radius` (optional): Search radius in meters (default: 500)

**Example Request:**
```bash
curl "http://localhost:8080/api/nearby?lat=47.0707&lon=15.4395&radius=500"
```

**Example Response:**
```json
{
  "results": [
    {
      "stop_id": "AT:47:1234:1:1",
      "stop_name": "Graz Jakominiplatz",
      "locality": "Graz",
      "lat": 47.0707,
      "lon": 15.4395,
      "distance": 45.2
    }
  ]
}
```

### Step 2: Getting Departure Information

Once you have a **stop_id**, you can query real-time departure information.

**Endpoint:** `GET /api/departures`

**Parameters:**
- `stop_id` (required): The stop ID obtained from search (e.g., "AT:47:1234:1:1")
- `limit` (optional): Number of departures to return (default: 10, max: 50)
- `window` (optional): Time window in minutes (default: 60)
- `realtime` (optional): Include real-time data (default: true)

**Example Request:**
```bash
curl "http://localhost:8080/api/departures?stop_id=AT:47:1234:1:1&limit=10&window=60&realtime=true"
```

**Example Response:**
```json
{
  "stop_name": "Graz Jakominiplatz",
  "departures": [
    {
      "line": "1",
      "direction": "Mariatrost",
      "planned_time": "2026-02-06T14:30:00",
      "estimated_time": "2026-02-06T14:32:00",
      "countdown_minutes": 12,
      "is_realtime": true,
      "platform": "Gleis 2"
    },
    {
      "line": "7",
      "direction": "LKH/Med Uni",
      "planned_time": "2026-02-06T14:25:00",
      "estimated_time": "2026-02-06T14:25:00",
      "countdown_minutes": 5,
      "is_realtime": true,
      "platform": "Gleis 1"
    }
  ]
}
```

**Response Fields Explained:**
- `line`: Line number/name (e.g., "1", "7", "S1")
- `direction`: Final destination
- `planned_time`: Scheduled departure time (ISO 8601 format)
- `estimated_time`: Real-time estimated departure (if available)
- `countdown_minutes`: Minutes until departure
- `is_realtime`: `true` if real-time data is available, `false` if scheduled only
- `platform`: Platform/track information (if available)

## Complete Workflow Example

### Using cURL:

```bash
# 1. Search for a stop
curl "http://localhost:8080/api/search?query=Hauptbahnhof"

# 2. Copy the stop_id from results (e.g., "AT:47:9999:1:1")

# 3. Get departures for that stop
curl "http://localhost:8080/api/departures?stop_id=AT:47:9999:1:1&limit=15&realtime=true"
```

### Using Python:

```python
import requests

# 1. Search for a stop
response = requests.get('http://localhost:8080/api/search', params={'query': 'Hauptbahnhof'})
results = response.json()['results']

# 2. Get the first stop's ID
stop_id = results[0]['stop_id']
print(f"Found stop: {results[0]['stop_name']} (ID: {stop_id})")

# 3. Get departures
response = requests.get('http://localhost:8080/api/departures', params={
    'stop_id': stop_id,
    'limit': 10,
    'realtime': True
})

departures = response.json()['departures']
for dep in departures:
    realtime_indicator = "🔴 Live" if dep['is_realtime'] else "📅 Fahrplan"
    print(f"{dep['line']} → {dep['direction']}: {dep['estimated_time']} ({realtime_indicator})")
```

### Using JavaScript:

```javascript
// 1. Search for a stop
const searchResponse = await fetch('/api/search?query=Hauptbahnhof');
const searchData = await searchResponse.json();

// 2. Get the first stop's ID
const stopId = searchData.results[0].stop_id;
console.log(`Found stop: ${searchData.results[0].stop_name} (ID: ${stopId})`);

// 3. Get departures
const deptResponse = await fetch(`/api/departures?stop_id=${encodeURIComponent(stopId)}&limit=10&realtime=true`);
const deptData = await deptResponse.json();

deptData.departures.forEach(dep => {
    const indicator = dep.is_realtime ? '🔴 Live' : '📅 Fahrplan';
    console.log(`${dep.line} → ${dep.direction}: ${dep.estimated_time} (${indicator})`);
});
```

## Additional API Endpoints

### Route Planning

**Endpoint:** `POST /api/trip`

**Request Body:**
```json
{
  "origin": "Jakominiplatz",
  "destination": "Hauptbahnhof",
  "limit": 3,
  "include_realtime": true
}
```

### Cache Management

**Get Cache Statistics:**
```bash
curl "http://localhost:8080/api/cache/stats"
```

**Build Cache in Background:**
```bash
curl -X POST "http://localhost:8080/api/cache/build" \
  -H "Content-Type: application/json" \
  -d '{"stops_per_city": 100}'
```

**Check Build Progress:**
```bash
curl "http://localhost:8080/api/cache/progress"
```

**Stop Cache Building:**
```bash
curl -X POST "http://localhost:8080/api/cache/stop"
```

## Notes

- **Stop IDs** follow the format: `AT:{region}:{stop}:{platform}:{variant}` (e.g., `AT:47:1234:1:1`)
- **Real-time data** may not be available for all lines/stops (check `is_realtime` field)
- **Cache** improves search performance - it automatically grows as you search, or you can pre-build it
- **Rate Limiting**: The API uses a 0.5s delay between requests when building cache to avoid overloading the upstream TRIAS service
- All timestamps are in **ISO 8601 format** with Central European Time (CET/CEST)

## Error Handling

All endpoints return standard HTTP status codes:
- `200 OK`: Successful request
- `400 Bad Request`: Missing or invalid parameters
- `500 Internal Server Error`: Server or upstream API error

Error responses include a `message` field:
```json
{
  "error": "Missing required parameter: stop_id",
  "message": "Please provide a valid stop_id"
}
```
