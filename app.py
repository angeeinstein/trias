"""Flask server for TRIAS API"""

from flask import Flask, request, jsonify, render_template
from trias_client import TriasClient
from config import DEFAULT_NUMBER_OF_RESULTS, DEFAULT_DEPARTURE_WINDOW_MINUTES, DEFAULT_GEO_RADIUS_METERS, STOP_CACHE_FILE
import threading
import time
from datetime import datetime
import os

app = Flask(__name__)
trias = TriasClient()

# Global variable for cache building progress
cache_build_progress = {
    'running': False,
    'total': 0,
    'current': 0,
    'current_city': '',
    'error': None
}


def build_cache_background(cities, stops_per_city):
    """Build cache in background thread"""
    global cache_build_progress
    
    cache_build_progress['running'] = True
    cache_build_progress['total'] = len(cities)
    cache_build_progress['current'] = 0
    cache_build_progress['error'] = None
    
    try:
        for i, city in enumerate(cities):
            if not cache_build_progress['running']:
                break
                
            cache_build_progress['current'] = i + 1
            cache_build_progress['current_city'] = city
            
            try:
                # Fetch stops for this city
                results = trias._fetch_location_by_name(city, stops_per_city)
                trias._add_to_cache(results)
                time.sleep(0.5)  # Small delay to avoid overwhelming API
            except Exception as e:
                print(f"[CACHE] Error building cache for {city}: {e}")
                
    except Exception as e:
        cache_build_progress['error'] = str(e)
    finally:
        cache_build_progress['running'] = False
        cache_build_progress['current_city'] = 'Abgeschlossen'


@app.after_request
def add_cache_headers(response):
    """Add cache control headers to prevent caching issues"""
    # Don't cache API responses and HTML pages
    if request.path.startswith('/api/') or request.path == '/':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, public, max-age=0'
        response.headers['Expires'] = '0'
        response.headers['Pragma'] = 'no-cache'
    # Allow caching for static files but validate
    elif request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=300, must-revalidate'
    return response


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


@app.route('/api/trip', methods=['GET'])
def get_trip():
    """
    Get trip/route from origin to destination
    
    Query parameters:
    - origin: Origin location name or address (required)
    - destination: Destination location name or address (required)
    - limit: Maximum number of trips (optional, default: 5)
    - realtime: Include realtime data (optional, default: true)
    
    Example: /api/trip?origin=Hauptplatz&destination=Jakominiplatz&limit=3
    """
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    
    if not origin or not destination:
        return jsonify({'error': 'Query parameters "origin" and "destination" are required'}), 400
    
    limit = request.args.get('limit', 5, type=int)
    realtime = request.args.get('realtime', 'true').lower() in ('true', '1', 'yes')
    
    try:
        result = trias.get_trip(origin, destination, limit, realtime)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    try:
        stats = {
            'enabled': trias.stop_cache is not None,
            'total_stops': len(trias.stop_cache) if trias.stop_cache else 0,
            'cache_age_hours': (datetime.utcnow() - trias.cache_timestamp).total_seconds() / 3600 if trias.cache_timestamp else None,
            'cache_file_exists': os.path.exists(STOP_CACHE_FILE)
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cache/build', methods=['POST'])
def build_cache():
    """Start building cache in background"""
    global cache_build_progress
    
    if cache_build_progress['running']:
        return jsonify({'error': 'Cache building already in progress'}), 400
    
    data = request.get_json() or {}
    cities = data.get('cities', ['Wien', 'Graz', 'Linz', 'Salzburg', 'Innsbruck', 
                                  'Klagenfurt', 'Villach', 'Wels', 'St. Pölten', 'Dornbirn',
                                  'Feldkirch', 'Bregenz', 'Steyr', 'Wolfsberg', 'Baden',
                                  'Leoben', 'Krems', 'Wiener Neustadt', 'Amstetten', 'Kapfenberg'])
    stops_per_city = data.get('stops_per_city', 100)
    
    # Start background thread
    thread = threading.Thread(target=build_cache_background, args=(cities, stops_per_city))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': 'Cache building started',
        'cities': len(cities),
        'stops_per_city': stops_per_city
    })


@app.route('/api/cache/progress', methods=['GET'])
def cache_progress():
    """Get cache building progress"""
    return jsonify(cache_build_progress)


@app.route('/api/cache/stop', methods=['POST'])
def stop_cache_build():
    """Stop cache building"""
    global cache_build_progress
    cache_build_progress['running'] = False
    return jsonify({'message': 'Cache building stopped'})


if __name__ == '__main__':
    # Run the Flask development server (for local testing only)
    # In production, use gunicorn: gunicorn --config gunicorn_config.py app:app
    app.run(debug=True, host='0.0.0.0', port=5000)
