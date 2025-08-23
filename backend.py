import os
import time
from datetime import timedelta
from flask import Flask, request, jsonify, session, redirect
from flask_cors import CORS, cross_origin
from spotipy.oauth2 import SpotifyPKCE
import spotipy
from shared_constants import *
import logging
from spotipy.exceptions import SpotifyException

logging.basicConfig(
    filename='backend.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)

print("DEBUG: backend.py - Starting Flask backend initialization")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# --- CORS and Session Cookie Config for Cross-Origin Auth ---
# For development, we need to handle both HTTP and HTTPS
is_development = os.environ.get('FLASK_ENV') == 'development'

if is_development:
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # More permissive for local development
    app.config['SESSION_COOKIE_SECURE'] = False    # Allow HTTP for local development
    app.config['SESSION_COOKIE_DOMAIN'] = None     # No domain restriction for local development
else:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Allow cross-site cookies
    app.config['SESSION_COOKIE_SECURE'] = True      # Required for SameSite=None (must use HTTPS)
    app.config['SESSION_COOKIE_DOMAIN'] = None      # No domain restriction for now

# Set session lifetime to 24 hours to prevent premature expiration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Add session debugging
logging.debug(f"DEBUG: backend.py - Session config - SameSite: {app.config['SESSION_COOKIE_SAMESITE']}")
logging.debug(f"DEBUG: backend.py - Session config - Secure: {app.config['SESSION_COOKIE_SECURE']}")
logging.debug(f"DEBUG: backend.py - Session config - Domain: {app.config['SESSION_COOKIE_DOMAIN']}")
logging.debug(f"DEBUG: backend.py - Environment: {'development' if is_development else 'production'}")

# More permissive CORS configuration
CORS(app, supports_credentials=True, 
     origins=[
         # Allow all localhost variants (including IPv6)
         "http://localhost:8000",
         "http://127.0.0.1:8000", 
         "http://[::1]:8000",
         "http://[::]:8000",
         "http://localhost:3000",
         "http://localhost:8080",
         "http://localhost:9000",
         "https://localhost:8000",
         "https://127.0.0.1:8000", 
         "https://[::1]:8000",
         "https://[::]:8000",
         "https://localhost:3000",
         "https://localhost:8080",
         "https://localhost:9000",
         # Production domains
         "https://spotisnake.onrender.com",
         "https://danielllesk.itch.io",
         "https://danielllesk.itch.io/spotisnake",
         "https://html-classic.itch.zone",
         # Allow any itch.io subdomain
         "https://*.itch.io",
         "https://*.itch.zone"
     ],
     allow_headers=["Content-Type", "Authorization", "Origin", "Accept", "X-Requested-With"],
     expose_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     credentials=True
     )

# Add CORS debugging middleware
@app.before_request
def log_request_info():
    logging.debug(f"DEBUG: backend.py - Request: {request.method} {request.path}")
    logging.debug(f"DEBUG: backend.py - Origin: {request.headers.get('Origin', 'No Origin')}")
    logging.debug(f"DEBUG: backend.py - User-Agent: {request.headers.get('User-Agent', 'No User-Agent')}")
    logging.debug(f"DEBUG: backend.py - All headers: {dict(request.headers)}")

# Add comprehensive CORS handler
def add_cors_headers(response):
    """Add CORS headers to response"""
    # Handle tuple responses (status code, response)
    if isinstance(response, tuple):
        response_obj, status_code = response
    else:
        response_obj = response
        status_code = None
    
    origin = request.headers.get('Origin', 'No Origin')
    logging.debug(f"DEBUG: backend.py - Processing CORS for Origin: {origin}")
    
    allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://[::1]:8000",
        "http://[::]:8000",  # Explicitly include IPv6 loopback
        "https://localhost:8000",
        "https://127.0.0.1:8000",
        "https://[::1]:8000",
        "https://[::]:8000",
        "http://localhost:3000",
        "https://localhost:3000",
        "http://localhost:8080",
        "https://localhost:8080",
        "http://localhost:9000",
        "https://localhost:9000",
        "https://spotisnake.onrender.com",
        "https://danielllesk.itch.io",
        "https://danielllesk.itch.io/spotisnake",
        "https://html-classic.itch.zone",
    ]
    
    if origin in allowed_origins or any(origin.endswith(domain) for domain in ['.itch.io', '.itch.zone']):
        response_obj.headers['Access-Control-Allow-Origin'] = origin
        logging.debug(f"DEBUG: backend.py - Setting Access-Control-Allow-Origin to {origin}")
    else:
        logging.warning(f"DEBUG: backend.py - Origin {origin} not allowed")
    
    response_obj.headers['Access-Control-Allow-Credentials'] = 'true'
    response_obj.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response_obj.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept, X-Requested-With'
    logging.debug(f"DEBUG: backend.py - Response headers: {dict(response_obj.headers)}")
    
    if status_code:
        return response_obj, status_code
    return response_obj

# Catch-all OPTIONS handler for CORS preflight
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    logging.debug(f"DEBUG: backend.py - OPTIONS request for path: {path}")
    logging.debug(f"DEBUG: backend.py - Origin: {request.headers.get('Origin', 'No Origin')}")
    logging.debug(f"DEBUG: backend.py - All headers: {dict(request.headers)}")
    
    # Create response with CORS headers
    response = jsonify({'status': 'ok'})
    response = add_cors_headers(response)
    
    # Add additional CORS headers for preflight
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept, X-Requested-With'
    
    logging.debug(f"DEBUG: backend.py - OPTIONS response headers: {dict(response.headers)}")
    return response

print("DEBUG: backend.py - Setting up Spotify PKCE authentication")
sp_oauth = SpotifyPKCE(
    client_id=SPOTIFY_CLIENT_ID,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SPOTIFY_AUTH_SCOPE,
    open_browser=False,  # handles redirect
    cache_path=None
)

# Global token storage (in production, use a proper database)
# global_token_info = None

def get_spotify():
    logging.debug("DEBUG: backend.py - get_spotify() called")
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info available (session)")
        return None
    
    logging.debug(f"DEBUG: backend.py - Token info type: {type(token_info)}")
    logging.debug(f"DEBUG: backend.py - Token info: {token_info}")
    
    try:
        if isinstance(token_info, dict) and 'access_token' in token_info:
            access_token = token_info['access_token']
        else:
            logging.debug("DEBUG: backend.py - Invalid token_info structure")
            return None
            
        logging.debug("DEBUG: backend.py - Creating Spotify client with token")
        return spotipy.Spotify(auth=access_token)
    except Exception as e:
        logging.error(f"DEBUG: backend.py - Error creating Spotify client: {e}")
        return None

@app.route('/')
def index():
    logging.debug("DEBUG: backend.py - / endpoint called")
    return """
    <html>
        <head><title>SpotiSnake Backend</title></head>
        <body>
            <h1>SpotiSnake Backend Server</h1>
            <p>This is the backend server for SpotiSnake game.</p>
            <p><a href="/login">Login to Spotify</a></p>
            <p><a href="/me">Check Authentication Status</a></p>
        </body>
    </html>
    """

@app.route('/login')
def login():
    logging.debug("DEBUG: backend.py - /login endpoint called")
    auth_url = sp_oauth.get_authorize_url()
    logging.debug(f"DEBUG: backend.py - Redirecting to auth URL: {auth_url}")
    return redirect(auth_url)

@app.route('/callback')
def callback():
    logging.debug("DEBUG: backend.py - /callback endpoint called")
    code = request.args.get('code')
    logging.debug(f"DEBUG: backend.py - Received auth code: {code[:10]}...")
    try:
        token_info = sp_oauth.get_access_token(code)
        logging.debug(f"DEBUG: backend.py - Raw token_info: {token_info}")
        logging.debug(f"DEBUG: backend.py - Token_info type: {type(token_info)}")
        # If token_info is a string, wrap it in a dict
        if isinstance(token_info, str):
            token_info = {'access_token': token_info}
        session.permanent = True  # Make session permanent so it doesn't expire
        session['token_info'] = token_info
        logging.debug("DEBUG: backend.py - Token stored in session")
        logging.debug(f"DEBUG: backend.py - Session contents after storing token: {dict(session)}")
        logging.debug(f"DEBUG: backend.py - Session ID: {session.sid if hasattr(session, 'sid') else 'No SID'}")
        logging.debug(f"DEBUG: backend.py - Session permanent: {session.permanent}")
        # Test the token immediately
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_info = sp.current_user()
        logging.debug(f"DEBUG: backend.py - User authenticated: {user_info.get('id', 'unknown')}")
        # Show a visually appealing static login success page
        return f"""
        <html>
            <head>
                <title>Login Successful</title>
                <meta name='viewport' content='width=device-width, initial-scale=1'>
                <style>
                    body {{
                        background: linear-gradient(135deg, #1db954 0%, #191414 100%);
                        color: #fff;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }}
                    .card {{
                        background: rgba(0,0,0,0.7);
                        border-radius: 16px;
                        padding: 40px 30px 30px 30px;
                        box-shadow: 0 8px 32px 0 rgba(0,0,0,0.37);
                        text-align: center;
                        max-width: 400px;
                    }}
                    .checkmark {{
                        font-size: 60px;
                        color: #1db954;
                        margin-bottom: 10px;
                    }}
                    .user-info {{
                        margin: 20px 0 10px 0;
                        font-size: 1.1em;
                        color: #b3b3b3;
                    }}
                    .return-msg {{
                        margin-top: 20px;
                        font-size: 1.2em;
                        color: #fff;
                    }}
                    .close-msg {{
                        margin-top: 10px;
                        font-size: 1em;
                        color: #b3b3b3;
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="checkmark">✅</div>
                    <h1>Login Successful!</h1>
                    <div class="user-info">
                        <strong>User:</strong> {user_info.get('display_name', 'Unknown')}<br>
                        <strong>Email:</strong> {user_info.get('email', 'Unknown')}<br>
                        <strong>Product:</strong> {user_info.get('product', 'Unknown')}
                    </div>
                    <div class="return-msg">
                        You can now return to the game tab.<br>
                        <span style='font-size:0.9em;'>If the game doesn't detect your login, click 'Check Login' or refresh the game tab.</span>
                    </div>
                    <div class="close-msg">
                        This tab can be closed.
                    </div>
                </div>
            </body>
        </html>
        """
    except Exception as e:
        logging.error(f"DEBUG: backend.py - Error in callback: {e}")
        import traceback
        traceback.print_exc()
        return f"Login failed: {str(e)}", 400

@app.route('/me')
def me():
    logging.debug("DEBUG: backend.py - /me endpoint called")
    logging.debug(f"DEBUG: backend.py - Session ID: {session.sid if hasattr(session, 'sid') else 'No SID'}")
    logging.debug(f"DEBUG: backend.py - Session contents: {dict(session)}")
    logging.debug(f"DEBUG: backend.py - Request cookies: {dict(request.cookies)}")
    
    # Check session first
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info in session for /me")
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])

    logging.debug(f"DEBUG: backend.py - Token info found: {type(token_info)}")

    sp = get_spotify()
    if not sp:
        logging.debug("DEBUG: backend.py - Failed to create Spotify client for /me")
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
    try:
        user_info = sp.current_user()
        logging.debug(f"DEBUG: backend.py - User info retrieved: {user_info.get('id', 'unknown')}")
        response = jsonify(user_info)
        return add_cors_headers(response)
    except SpotifyException as e:
        logging.error(f"SpotifyException in /me: {e}")
        response = jsonify({'error': f'Spotify error: {str(e)}'}), 401
        return add_cors_headers(response[0])
    except Exception as e:
        logging.error(f"Unexpected error in /me: {e}")
        response = jsonify({'error': f'Unexpected error: {str(e)}'}), 500
        return add_cors_headers(response[0])

@app.route('/search', methods=['GET', 'OPTIONS'])
def search():
    if request.method == 'OPTIONS':
        logging.debug("DEBUG: backend.py - OPTIONS request for /search endpoint")
        response = jsonify({'status': 'ok'})
        response = add_cors_headers(response)
        # Add additional CORS headers for preflight
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept, X-Requested-With'
        return response
    
    logging.debug("DEBUG: backend.py - GET /search endpoint called")
    
    # Check session first
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info in session for /search")
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    logging.debug(f"DEBUG: backend.py - Token info found for /search: {type(token_info)}")
    
    sp = get_spotify()
    if not sp:
        logging.debug("DEBUG: backend.py - Failed to create Spotify client for /search")
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    q = request.args.get('q')
    logging.debug(f"DEBUG: backend.py - Searching for: {q}")
    logging.debug(f"DEBUG: backend.py - Query type: {type(q)}, length: {len(q) if q else 0}")
    
    if not q:
        logging.debug("DEBUG: backend.py - No query parameter provided")
        response = jsonify({'error': 'No search query provided'}), 400
        return add_cors_headers(response)
    
    try:
        logging.debug(f"DEBUG: backend.py - Calling Spotify API search with query: '{q}'")
        results = sp.search(q, type='album', limit=10)  # Increased from 5 to 10 for better selection
        albums_found = len(results.get('albums', {}).get('items', []))
        logging.debug(f"DEBUG: backend.py - Found {albums_found} albums")
        
        if albums_found > 0:
            # Log first album details for debugging
            first_album = results['albums']['items'][0]
            logging.debug(f"DEBUG: backend.py - First album: '{first_album.get('name', 'Unknown')}' by '{first_album.get('artists', [{}])[0].get('name', 'Unknown') if first_album.get('artists') else 'Unknown'}'")
        
        response = jsonify(results)
        logging.debug(f"DEBUG: backend.py - Search response created successfully")
        
        # Add performance optimization headers
        response.headers['Cache-Control'] = 'public, max-age=300'  # Cache for 5 minutes
        response.headers['X-Search-Results-Count'] = str(albums_found)
        
        cors_response = add_cors_headers(response)
        logging.debug(f"DEBUG: backend.py - CORS headers added, returning response")
        return cors_response
    except Exception as e:
        logging.error(f"DEBUG: backend.py - Error in search: {e}")
        import traceback
        traceback.print_exc()
        response = jsonify({'error': f'Search failed: {str(e)}'}), 500
        return add_cors_headers(response)



@app.route('/play', methods=['POST', 'OPTIONS'])
def play():
    if request.method == 'OPTIONS':
        logging.debug("DEBUG: backend.py - OPTIONS request for /play endpoint")
        response = jsonify({'status': 'ok'})
        response = add_cors_headers(response)
        # Add additional CORS headers for preflight
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept, X-Requested-With'
        logging.debug(f"DEBUG: backend.py - OPTIONS response headers for /play: {dict(response.headers)}")
        return response
    
    logging.debug("DEBUG: backend.py - POST /play endpoint called")
    
    # Check session first
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info in session for /play")
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    logging.debug(f"DEBUG: backend.py - Token info found for /play: {type(token_info)}")
    
    sp = get_spotify()
    if not sp:
        logging.debug("DEBUG: backend.py - Failed to create Spotify client for /play")
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
    uri = request.json.get('uri')
    device_id = request.json.get('device_id')
    position_ms = request.json.get('position_ms', 0)
    logging.debug(f"DEBUG: backend.py - Playing URI: {uri}, device: {device_id}, position: {position_ms}")
    
    try:
        # Try to start playback with the provided device_id
        sp.start_playback(device_id=device_id, uris=[uri] if uri else None, position_ms=position_ms)
        logging.debug("DEBUG: backend.py - Playback started successfully")
        response = jsonify({'status': 'playing'})
        return add_cors_headers(response)
    except Exception as e:
        logging.debug(f"DEBUG: backend.py - Playback failed with device_id {device_id}: {e}")
        
        # If that fails, try to find an available device
        try:
            devices_info = sp.devices()
            devices = devices_info.get('devices', [])
            logging.debug(f"DEBUG: backend.py - Found {len(devices)} devices")
            
            # Look for an active device first
            active_device = None
            for device in devices:
                if device.get('is_active'):
                    active_device = device
                    break
            
            # If no active device, use the first available device
            if not active_device and devices:
                active_device = devices[0]
            
            if active_device:
                device_id = active_device['id']
                logging.debug(f"DEBUG: backend.py - Using device: {active_device.get('name', 'Unknown')} (ID: {device_id})")
                sp.start_playback(device_id=device_id, uris=[uri] if uri else None, position_ms=position_ms)
                logging.debug("DEBUG: backend.py - Playback started successfully with found device")
                response = jsonify({'status': 'playing', 'device_id': device_id})
                return add_cors_headers(response)
            else:
                logging.debug("DEBUG: backend.py - No devices available")
                response = jsonify({'error': 'No active device found. Please open Spotify and start playing music.'}), 404
                return add_cors_headers(response)
                
        except Exception as e2:
            logging.debug(f"DEBUG: backend.py - Failed to find and use device: {e2}")
            response = jsonify({'error': 'No active device found. Please open Spotify and start playing music.'}), 404
            return add_cors_headers(response)

@app.route('/pause', methods=['POST', 'OPTIONS'])
def pause():
    if request.method == 'OPTIONS':
        logging.debug("DEBUG: backend.py - OPTIONS request for /pause endpoint")
        response = jsonify({'status': 'ok'})
        response = add_cors_headers(response)
        # Add additional CORS headers for preflight
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept, X-Requested-With'
        return response
    
    logging.debug("DEBUG: backend.py - POST /pause endpoint called")
    
    # Check session first
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info in session for /pause")
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    logging.debug(f"DEBUG: backend.py - Token info found for /pause: {type(token_info)}")
    
    sp = get_spotify()
    if not sp:
        logging.debug("DEBUG: backend.py - Failed to create Spotify client for /pause")
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
    device_id = request.json.get('device_id')
    logging.debug(f"DEBUG: backend.py - Pausing device: {device_id}")
    
    try:
        sp.pause_playback(device_id=device_id)
        logging.debug("DEBUG: backend.py - Playback paused successfully")
        response = jsonify({'status': 'paused'})
        return add_cors_headers(response)
    except spotipy.exceptions.SpotifyException as e:
        logging.error(f"DEBUG: backend.py - Spotify pause error: {e}")
        if e.http_status == 403:
            logging.debug("DEBUG: backend.py - 403 error - likely no active device or restriction")
            response = jsonify({'status': 'no_active_device', 'message': 'No active device to pause'})
            return add_cors_headers(response)
        else:
            response = jsonify({'error': f'Spotify API error: {e}'}), e.http_status
            return add_cors_headers(response[0])
    except Exception as e:
        logging.error(f"DEBUG: backend.py - Unexpected error in pause: {e}")
        response = jsonify({'error': f'Unexpected error: {e}'}), 500
        return add_cors_headers(response[0])

@app.route('/devices')
def devices():
    logging.debug("DEBUG: backend.py - /devices endpoint called")
    
    # Check session first
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info in session for /devices")
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    logging.debug(f"DEBUG: backend.py - Token info found for /devices: {type(token_info)}")
    
    sp = get_spotify()
    if not sp:
        logging.debug("DEBUG: backend.py - Failed to create Spotify client for /devices")
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    devices_info = sp.devices()
    logging.debug(f"DEBUG: backend.py - Found {len(devices_info.get('devices', []))} devices")
    response = jsonify(devices_info)
    return add_cors_headers(response)

@app.route('/currently_playing')
def currently_playing():
    logging.debug("DEBUG: backend.py - /currently_playing endpoint called")
    
    # Check session first
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info in session for /currently_playing")
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    logging.debug(f"DEBUG: backend.py - Token info found for /currently_playing: {type(token_info)}")
    
    sp = get_spotify()
    if not sp:
        logging.debug("DEBUG: backend.py - Failed to create Spotify client for /currently_playing")
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    current = sp.current_playback()
    logging.debug(f"DEBUG: backend.py - Current playback: {current.get('item', {}).get('name', 'none') if current else 'none'}")
    response = jsonify(current)
    return add_cors_headers(response)

@app.route('/debug')
def debug_page():
    logging.debug("DEBUG: backend.py - /debug page called")
    token_info = session.get('token_info')
    has_token = token_info is not None
    
    return f"""
    <html>
        <head><title>SpotiSnake Debug</title></head>
        <body style="background: #1a1a1a; color: #fff; font-family: monospace; padding: 20px;">
            <h1>🔧 SpotiSnake Debug Page</h1>
            
            <h2>Session Status:</h2>
            <div style="background: #333; padding: 10px; margin: 10px 0;">
                <strong>Has Token:</strong> {'✅ Yes' if has_token else '❌ No'}<br>
                <strong>Token Type:</strong> {type(token_info).__name__ if token_info else 'None'}<br>
                <strong>Has Access Token:</strong> {'✅ Yes' if has_token and isinstance(token_info, dict) and 'access_token' in token_info else '❌ No'}
            </div>
            
            <h2>Test Endpoints:</h2>
            <div style="background: #333; padding: 10px; margin: 10px 0;">
                <a href="/me" style="color: #1db954;">🔍 Test /me endpoint</a><br>
                <a href="/devices" style="color: #1db954;">🔍 Test /devices endpoint</a><br>
                <a href="/currently_playing" style="color: #1db954;">🔍 Test /currently_playing endpoint</a><br>
                <a href="/debug_session" style="color: #1db954;">🔍 Test /debug_session endpoint</a>
            </div>
            
            <h2>Actions:</h2>
            <div style="background: #333; padding: 10px; margin: 10px 0;">
                <a href="/login" style="color: #1db954;">🔑 Login to Spotify</a><br>
                <a href="http://localhost:8000#debug" style="color: #1db954;">🎮 Go to Game</a>
            </div>
            
            <h2>Backend Logs:</h2>
            <div style="background: #000; color: #0f0; padding: 10px; margin: 10px 0; height: 200px; overflow-y: scroll;">
                Check your backend console for debug output...
            </div>
        </body>
    </html>
    """

@app.route('/debug_session')
def debug_session():
    logging.debug("DEBUG: backend.py - /debug_session endpoint called")
    token_info = session.get('token_info')
    if token_info:
        logging.debug("DEBUG: backend.py - Session has token_info")
        response = jsonify({
            'has_token': True,
            'token_type': type(token_info).__name__,
            'has_access_token': 'access_token' in token_info if isinstance(token_info, dict) else False
        })
        return add_cors_headers(response)
    else:
        logging.debug("DEBUG: backend.py - Session has no token_info")
        response = jsonify({'has_token': False})
        return add_cors_headers(response)

@app.route('/album_tracks')
def album_tracks():
    logging.debug("DEBUG: backend.py - /album_tracks endpoint called")
    
    # Add detailed session debugging
    logging.debug(f"DEBUG: backend.py - Session ID: {session.get('_id', 'No session ID')}")
    logging.debug(f"DEBUG: backend.py - Session contents: {dict(session)}")
    logging.debug(f"DEBUG: backend.py - Session permanent: {session.get('_permanent', False)}")
    
    # Check session first
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info in session for /album_tracks")
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    logging.debug(f"DEBUG: backend.py - Token info found for /album_tracks: {type(token_info)}")
    
    sp = get_spotify()
    if not sp:
        logging.debug("DEBUG: backend.py - Failed to create Spotify client for /album_tracks")
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    album_id = request.args.get('album_id')
    logging.debug(f"DEBUG: backend.py - Getting tracks for album: {album_id}")
    try:
        logging.debug(f"DEBUG: backend.py - About to call sp.album_tracks with album_id: {album_id}")
        results = sp.album_tracks(album_id, limit=50)
        logging.debug(f"DEBUG: backend.py - Found {len(results.get('items', []))} tracks")
        logging.debug(f"DEBUG: backend.py - Album tracks response: {results}")
    except SpotifyException as e:
        logging.error(f"DEBUG: backend.py - SpotifyException getting album tracks: {e}")
        logging.error(f"DEBUG: backend.py - SpotifyException details: status={e.http_status}, msg={e.msg}")
        response = jsonify({'error': f'Spotify API error: {str(e)}', 'status': e.http_status, 'msg': e.msg}), 500
        return add_cors_headers(response)
    except Exception as e:
        logging.error(f"DEBUG: backend.py - General error getting album tracks: {e}")
        logging.error(f"DEBUG: backend.py - Error type: {type(e)}")
        response = jsonify({'error': f'Failed to get album tracks: {str(e)}'}), 500
        return add_cors_headers(response)
    response = jsonify(results)
    return add_cors_headers(response)

@app.route('/test_cors', methods=['GET', 'POST', 'OPTIONS'])
def test_cors():
    logging.debug("DEBUG: backend.py - /test_cors endpoint called")
    logging.debug(f"DEBUG: backend.py - Origin header: {request.headers.get('Origin', 'No Origin')}")
    logging.debug(f"DEBUG: backend.py - All headers: {dict(request.headers)}")
    response = jsonify({
        'message': 'CORS test successful', 
        'origin': request.headers.get('Origin', 'No Origin'),
        'method': request.method,
        'headers': dict(request.headers),
        'timestamp': time.time()
    })
    return add_cors_headers(response)

@app.route('/ping', methods=['GET', 'OPTIONS'])
def ping():
    """Simple ping endpoint for testing connectivity"""
    logging.debug("DEBUG: backend.py - /ping endpoint called")
    response = jsonify({
        'message': 'pong',
        'origin': request.headers.get('Origin', 'No Origin'),
        'timestamp': time.time()
    })
    return add_cors_headers(response)

@app.route('/test_session', methods=['GET', 'OPTIONS'])
def test_session():
    """Test session functionality"""
    logging.debug("DEBUG: backend.py - /test_session endpoint called")
    token_info = session.get('token_info')
    has_token = token_info is not None
    
    response = jsonify({
        'has_token': has_token,
        'token_type': type(token_info).__name__ if token_info else 'None',
        'has_access_token': 'access_token' in token_info if has_token and isinstance(token_info, dict) else False,
        'session_id': session.get('_id', 'No session ID'),
        'origin': request.headers.get('Origin', 'No Origin'),
        'timestamp': time.time()
    })
    return add_cors_headers(response)

@app.route('/force_auth', methods=['GET', 'OPTIONS'])
def force_auth():
    """Force authentication for testing - creates a dummy session"""
    logging.debug("DEBUG: backend.py - /force_auth endpoint called")
    
    # Create a dummy token for testing
    dummy_token = {
        'access_token': 'dummy_token_for_testing',
        'token_type': 'Bearer',
        'expires_in': 3600,
        'scope': SPOTIFY_AUTH_SCOPE
    }
    
    session['token_info'] = dummy_token
    logging.debug("DEBUG: backend.py - Created dummy token in session")
    
    response = jsonify({
        'message': 'Dummy authentication created for testing',
        'has_token': True,
        'timestamp': time.time()
    })
    return add_cors_headers(response)

@app.route('/test_play', methods=['GET', 'OPTIONS'])
def test_play():
    """Test endpoint to check if play would work"""
    logging.debug("DEBUG: backend.py - /test_play endpoint called")
    
    # Check session first
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info in session for /test_play")
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    logging.debug(f"DEBUG: backend.py - Token info found for /test_play: {type(token_info)}")
    
    sp = get_spotify()
    if not sp:
        logging.debug("DEBUG: backend.py - Failed to create Spotify client for /test_play")
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
    logging.debug("DEBUG: backend.py - Spotify client created successfully for /test_play")
    response = jsonify({
        'message': 'Authentication test successful',
        'has_token': True,
        'token_type': type(token_info).__name__,
        'timestamp': time.time()
    })
    return add_cors_headers(response)

@app.route('/test_search', methods=['GET', 'OPTIONS'])
def test_search():
    """Test endpoint to check if search would work"""
    logging.debug("DEBUG: backend.py - /test_search endpoint called")
    
    # Check session first
    token_info = session.get('token_info')
    if not token_info:
        logging.debug("DEBUG: backend.py - No token_info in session for /test_search")
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    logging.debug(f"DEBUG: backend.py - Token info found for /test_search: {type(token_info)}")
    
    sp = get_spotify()
    if not sp:
        logging.debug("DEBUG: backend.py - Failed to create Spotify client for /test_search")
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
    # Try a simple search
    try:
        results = sp.search('test', type='album', limit=1)
        logging.debug("DEBUG: backend.py - Search test successful")
        response = jsonify({
            'message': 'Search test successful',
            'has_token': True,
            'token_type': type(token_info).__name__,
            'search_results_count': len(results.get('albums', {}).get('items', [])),
            'timestamp': time.time()
        })
        return add_cors_headers(response)
    except Exception as e:
        logging.debug(f"DEBUG: backend.py - Search test failed: {e}")
        response = jsonify({
            'error': 'Search test failed',
            'exception': str(e),
            'has_token': True,
            'token_type': type(token_info).__name__,
            'timestamp': time.time()
        }), 500
        return add_cors_headers(response[0])

@app.route('/proxy_image', methods=['POST', 'OPTIONS'])
def proxy_image():
    """Proxy image downloads to avoid CORS issues"""
    if request.method == 'OPTIONS':
        logging.debug("DEBUG: backend.py - OPTIONS request for /proxy_image endpoint")
        response = jsonify({'status': 'ok'})
        response = add_cors_headers(response)
        # Add additional CORS headers for preflight
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept, X-Requested-With'
        logging.debug(f"DEBUG: backend.py - OPTIONS response headers for /proxy_image: {dict(response.headers)}")
        return response
    
    logging.debug("DEBUG: backend.py - POST /proxy_image endpoint called")
    
    try:
        data = request.get_json()
        image_url = data.get('image_url')
        
        if not image_url:
            logging.debug("DEBUG: backend.py - No image_url provided")
            response = jsonify({'error': 'No image_url provided'}), 400
            return add_cors_headers(response[0])
        
        logging.debug(f"DEBUG: backend.py - Proxying image from: {image_url}")
        
        # Download the image
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        img_response = requests.get(image_url, headers=headers, timeout=10)
        img_response.raise_for_status()
        
        # Return the image data
        from flask import Response
        response = Response(img_response.content, mimetype=img_response.headers.get('content-type', 'image/jpeg'))
        response = add_cors_headers(response)
        
        logging.debug(f"DEBUG: backend.py - Successfully proxied image, size: {len(img_response.content)} bytes")
        return response
        
    except Exception as e:
        logging.error(f"DEBUG: backend.py - Error proxying image: {e}")
        response = jsonify({'error': f'Failed to proxy image: {str(e)}'}), 500
        return add_cors_headers(response[0])

@app.route('/download_album_cover', methods=['POST', 'OPTIONS'])
def download_album_cover():
    """Download album cover and return as base64 data"""
    if request.method == 'OPTIONS':
        logging.debug("DEBUG: backend.py - OPTIONS request for /download_album_cover endpoint")
        response = jsonify({'status': 'ok'})
        response = add_cors_headers(response)
        # Add additional CORS headers for preflight
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept, X-Requested-With'
        logging.debug(f"DEBUG: backend.py - OPTIONS response headers for /download_album_cover: {dict(response.headers)}")
        return response
    
    logging.debug("DEBUG: backend.py - POST /download_album_cover endpoint called")
    
    try:
        data = request.get_json()
        image_url = data.get('image_url')
        
        if not image_url:
            logging.debug("DEBUG: backend.py - No image_url provided")
            response = jsonify({'error': 'No image_url provided'}), 400
            return add_cors_headers(response[0])
        
        logging.debug(f"DEBUG: backend.py - Downloading album cover from: {image_url}")
        
        # Download the image
        import requests
        import base64
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        img_response = requests.get(image_url, headers=headers, timeout=10)
        img_response.raise_for_status()
        
        # Convert to base64
        image_data = base64.b64encode(img_response.content).decode('utf-8')
        
        # Return the base64 data
        response = jsonify({
            'status': 200,
            'data': image_data,
            'content_type': img_response.headers.get('content-type', 'image/jpeg'),
            'size': len(img_response.content)
        })
        response = add_cors_headers(response)
        
        logging.debug(f"DEBUG: backend.py - Successfully downloaded album cover, size: {len(img_response.content)} bytes")
        return response
        
    except Exception as e:
        logging.error(f"DEBUG: backend.py - Error downloading album cover: {e}")
        response = jsonify({'error': f'Failed to download album cover: {str(e)}'}), 500
        return add_cors_headers(response[0])

if __name__ == '__main__':
    logging.debug("DEBUG: backend.py - Starting Flask server on port 5000")
    app.run(debug=True, port=5000, host='0.0.0.0') 