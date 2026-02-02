"""Configuration for TRIAS API client"""

# TRIAS API endpoint
TRIAS_API_URL = "http://ogdtrias.verbundlinie.at:8183/stv/trias"

# Default requestor ref (you can change this to your app name)
DEFAULT_REQUESTOR_REF = "flask-trias-client"

# TRIAS namespaces
NAMESPACES = {
    'trias': 'http://www.vdv.de/trias',
    'siri': 'http://www.siri.org.uk/siri'
}

# Default values
DEFAULT_NUMBER_OF_RESULTS = 10
DEFAULT_DEPARTURE_WINDOW_MINUTES = 60
DEFAULT_GEO_RADIUS_METERS = 500

# Stop cache settings
STOP_CACHE_FILE = 'stop_cache.json'
STOP_CACHE_TTL_HOURS = 24  # Refresh cache every 24 hours
STOP_CACHE_ENABLED = True
