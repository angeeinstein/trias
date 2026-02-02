"""Flask server for TRIAS API"""

from flask import Flask, request, jsonify, render_template
from trias_client import TriasClient
from config import DEFAULT_NUMBER_OF_RESULTS, DEFAULT_DEPARTURE_WINDOW_MINUTES, DEFAULT_GEO_RADIUS_METERS

app = Flask(__name__)
trias = TriasClient()


@app.route('/')
def index():
    """Serve the web interface"""
    return render_template('index.html')


@app.route('/api')
def api_info():
    """API information"""
    return jsonify({
        'name': 'TRIAS Flask API Server',
        'version': '1.0',
        'endpoints': {
            '/api/search/location': 'Search for stops by name',
            '/api/search/nearby': 'Search for stops near coordinates',
            '/api/departures': 'Get departures for a stop'
        }
    })


@app.route('/api/search/location', methods=['GET'])
def search_location():
    """
    Search for stops by name
    
    Query parameters:
    - q: Search query (required)
    - limit: Maximum number of results (optional, default: 10)
    
    Example: /api/search/location?q=hauptplatz&limit=5
    """
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    limit = request.args.get('limit', DEFAULT_NUMBER_OF_RESULTS, type=int)
    
    try:
        results = trias.search_location_by_name(query, limit)
        return jsonify({
            'query': query,
            'count': len(results),
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search/nearby', methods=['GET'])
def search_nearby():
    """
    Search for stops near coordinates
    
    Query parameters:
    - lat: Latitude (required)
    - lon: Longitude (required)
    - radius: Search radius in meters (optional, default: 500)
    - limit: Maximum number of results (optional, default: 200)
    
    Example: /api/search/nearby?lat=47.069250&lon=15.409852&radius=500&limit=20
    """
    try:
        latitude = request.args.get('lat', type=float)
        longitude = request.args.get('lon', type=float)
        
        if latitude is None or longitude is None:
            return jsonify({'error': 'Parameters "lat" and "lon" are required'}), 400
        
        radius = request.args.get('radius', DEFAULT_GEO_RADIUS_METERS, type=int)
        limit = request.args.get('limit', 200, type=int)
        
        results = trias.search_location_by_coordinates(longitude, latitude, radius, limit)
        return jsonify({
            'latitude': latitude,
            'longitude': longitude,
            'radius': radius,
            'count': len(results),
            'results': results
        })
    except TypeError:
        return jsonify({'error': 'Invalid parameter types'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/departures', methods=['GET'])
def get_departures():
    """
    Get departure information for a stop
    
    Query parameters:
    - stop_id: Stop ID (required, e.g., "at:46:7960")
    - limit: Maximum number of departures (optional, default: 12)
    - window: Time window in minutes (optional, default: 60)
    - realtime: Include realtime data (optional, default: true)
    
    Example: /api/departures?stop_id=at:46:7960&limit=10&window=120&realtime=true
    """
    stop_id = request.args.get('stop_id')
    if not stop_id:
        return jsonify({'error': 'Query parameter "stop_id" is required'}), 400
    
    limit = request.args.get('limit', 12, type=int)
    window = request.args.get('window', DEFAULT_DEPARTURE_WINDOW_MINUTES, type=int)
    realtime = request.args.get('realtime', 'true').lower() in ('true', '1', 'yes')
    
    try:
        results = trias.get_departures(stop_id, limit, window, realtime)
        return jsonify({
            'stop_id': stop_id,
            'count': len(results),
            'realtime_enabled': realtime,
            'departures': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    # Run the Flask development server (for local testing only)
    # In production, use gunicorn: gunicorn --config gunicorn_config.py app:app
    app.run(debug=True, host='0.0.0.0', port=5000)
