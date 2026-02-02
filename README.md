# TRIAS Flask API Server

A Flask REST API server for querying Austrian public transportation data via the TRIAS (Verbund Linie) API.

## Features

- 🔍 **Location Search**: Find stops by name
- 📍 **Nearby Search**: Find stops near coordinates
- 🚌 **Departures**: Get real-time and planned departure information
- ⏱️ **Realtime Data**: Support for realtime delays and estimates

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### 1. Search for Stops by Name

Find stops matching a search query.

**Endpoint:** `GET /api/search/location`

**Parameters:**
- `q` (required): Search query
- `limit` (optional): Maximum results (default: 10)

**Example:**
```bash
curl "http://localhost:5000/api/search/location?q=hauptplatz&limit=5"
```

**Response:**
```json
{
  "query": "hauptplatz",
  "count": 5,
  "results": [
    {
      "stop_id": "at:46:7960",
      "stop_name": "Graz Hauptplatz",
      "locality": "Graz",
      "longitude": 15.439504,
      "latitude": 47.070714
    }
  ]
}
```

### 2. Search for Nearby Stops

Find stops near a coordinate within a radius.

**Endpoint:** `GET /api/search/nearby`

**Parameters:**
- `lat` (required): Latitude
- `lon` (required): Longitude
- `radius` (optional): Search radius in meters (default: 500)
- `limit` (optional): Maximum results (default: 200)

**Example:**
```bash
curl "http://localhost:5000/api/search/nearby?lat=47.069250&lon=15.409852&radius=500&limit=20"
```

**Response:**
```json
{
  "latitude": 47.06925,
  "longitude": 15.409852,
  "radius": 500,
  "count": 15,
  "results": [
    {
      "stop_id": "at:46:1234",
      "stop_name": "Graz Jakominiplatz",
      "locality": "Graz",
      "longitude": 15.4104,
      "latitude": 47.0692
    }
  ]
}
```

### 3. Get Departures for a Stop

Get departure times for a specific stop.

**Endpoint:** `GET /api/departures`

**Parameters:**
- `stop_id` (required): Stop ID (e.g., "at:46:7960")
- `limit` (optional): Maximum departures (default: 12)
- `window` (optional): Time window in minutes (default: 60)
- `realtime` (optional): Include realtime data (default: true)

**Example:**
```bash
curl "http://localhost:5000/api/departures?stop_id=at:46:7960&limit=10&realtime=true"
```

**Response:**
```json
{
  "stop_id": "at:46:7960",
  "count": 10,
  "realtime_enabled": true,
  "departures": [
    {
      "line": "4",
      "destination": "Liebenau",
      "mode": "tram",
      "planned_time": "2026-02-02T18:30:00Z",
      "estimated_time": "2026-02-02T18:32:00Z",
      "actual_time": "2026-02-02T18:32:00Z",
      "delay_minutes": 2,
      "has_realtime": true
    },
    {
      "line": "6",
      "destination": "St. Peter",
      "mode": "tram",
      "planned_time": "2026-02-02T18:35:00Z",
      "estimated_time": null,
      "actual_time": "2026-02-02T18:35:00Z",
      "delay_minutes": null,
      "has_realtime": false
    }
  ]
}
```

### 4. Health Check

**Endpoint:** `GET /health`

**Example:**
```bash
curl "http://localhost:5000/health"
```

**Response:**
```json
{
  "status": "ok"
}
```

## Configuration

You can modify settings in `config.py`:

- `TRIAS_API_URL`: TRIAS API endpoint
- `DEFAULT_REQUESTOR_REF`: Your app identifier
- `DEFAULT_NUMBER_OF_RESULTS`: Default result limit
- `DEFAULT_DEPARTURE_WINDOW_MINUTES`: Default departure time window
- `DEFAULT_GEO_RADIUS_METERS`: Default search radius

## Understanding the Response

### Departure Times
- `planned_time`: Scheduled departure time (from timetable)
- `estimated_time`: Real-time estimate (null if not available)
- `actual_time`: The time to display (estimated if available, otherwise planned)
- `delay_minutes`: Delay in minutes (positive = late, negative = early)
- `has_realtime`: Whether real-time data is available for this departure

### Stop Search
- `stop_id`: Unique identifier (use this for departure queries)
- `stop_name`: Display name of the stop
- `locality`: City/area name
- `longitude`, `latitude`: Geographic coordinates

## Example Usage

### Find a stop and get its departures:

```bash
# 1. Search for "Hauptplatz"
curl "http://localhost:5000/api/search/location?q=hauptplatz&limit=1"

# 2. Use the stop_id from the response to get departures
curl "http://localhost:5000/api/departures?stop_id=at:46:7960&limit=5&realtime=true"
```

### Find nearby stops:

```bash
# Get stops within 1km of a coordinate
curl "http://localhost:5000/api/search/nearby?lat=47.069250&lon=15.409852&radius=1000&limit=10"
```

## Development

To run in debug mode (auto-reload on changes):
```bash
python app.py
```

The server runs on `http://localhost:5000` by default.

## API Notes

- All timestamps are in UTC with ISO-8601 format
- The TRIAS API requires XML POST requests, which this server handles internally
- Stop IDs are unique identifiers like "at:46:7960"
- Results are automatically deduplicated by stop_id
- Realtime data defaults to enabled but can be disabled

## Troubleshooting

**Connection errors:**
- Ensure you have internet access to reach the TRIAS API
- Check if the API endpoint is accessible

**Empty results:**
- Try different search terms
- Increase the search radius for nearby searches
- Check the stop_id format

**No realtime data:**
- Not all stops/lines have realtime data available
- Check the `has_realtime` field in responses
- Falls back to planned times when realtime is unavailable

## License

This is a client implementation for the public TRIAS API provided by Verbund Linie OGD.
