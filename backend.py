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

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

is_development = os.environ.get('FLASK_ENV') == 'development'

if is_development:
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_DOMAIN'] = None
else:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_DOMAIN'] = None

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

CORS(app, supports_credentials=True, 
     origins=[
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
         "https://spotisnake.onrender.com",
         "https://danielllesk.itch.io",
         "https://danielllesk.itch.io/spotisnake",
         "https://html-classic.itch.zone",
         "https://*.itch.io",
         "https://*.itch.zone"
     ],
     allow_headers=["Content-Type", "Authorization", "Origin", "Accept", "X-Requested-With"],
     expose_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     credentials=True
     )

@app.before_request
def log_request_info():
    pass

def add_cors_headers(response):
    """Add CORS headers to response"""
    if isinstance(response, tuple):
        response_obj, status_code = response
    else:
        response_obj = response
        status_code = None
    
    origin = request.headers.get('Origin', 'No Origin')
    
    allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://[::1]:8000",
        "http://[::]:8000",
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
    else:
        logging.warning(f"DEBUG: backend.py - Origin {origin} not allowed")
    
    response_obj.headers['Access-Control-Allow-Credentials'] = 'true'
    response_obj.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response_obj.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept, X-Requested-With'
    
    if status_code:
        return response_obj, status_code
    return response_obj

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    
    response = jsonify({'status': 'ok'})
    response = add_cors_headers(response)
    
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept, X-Requested-With'
    
    return response

sp_oauth = SpotifyPKCE(
    client_id=SPOTIFY_CLIENT_ID,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SPOTIFY_AUTH_SCOPE,
    open_browser=False,  # handles redirect
    cache_path=None
)

def get_spotify():
    token_info = session.get('token_info')
    if not token_info:
        return None
    
    
    try:
        if isinstance(token_info, dict) and 'access_token' in token_info:
            access_token = token_info['access_token']
        else:
            return None
            
        return spotipy.Spotify(auth=access_token)
    except Exception as e:
        logging.error(f"DEBUG: backend.py - Error creating Spotify client: {e}")
        return None

@app.route('/')
def index():
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
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    try:
        token_info = sp_oauth.get_access_token(code)
        # If token_info is a string, wrap it in a dict
        if isinstance(token_info, str):
            token_info = {'access_token': token_info}
        session.permanent = True  # Make session permanent so it doesn't expire
        session['token_info'] = token_info
        # Test the token immediately
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_info = sp.current_user()
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
    
    token_info = session.get('token_info')
    if not token_info:
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])


    sp = get_spotify()
    if not sp:
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
    try:
        user_info = sp.current_user()
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
    
    
    token_info = session.get('token_info')
    if not token_info:
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    
    sp = get_spotify()
    if not sp:
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    q = request.args.get('q')
    
    if not q:
        response = jsonify({'error': 'No search query provided'}), 400
        return add_cors_headers(response)
    
    try:
        results = sp.search(q, type='album', limit=10)  # Increased from 5 to 10 for better selection
        albums_found = len(results.get('albums', {}).get('items', []))
        
        if albums_found > 0:
            # Log first album details for debugging
            first_album = results['albums']['items'][0]
        
        response = jsonify(results)
        
        # Add performance optimization headers
        response.headers['Cache-Control'] = 'public, max-age=300'  # Cache for 5 minutes
        response.headers['X-Search-Results-Count'] = str(albums_found)
        
        cors_response = add_cors_headers(response)
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
    
    
    token_info = session.get('token_info')
    if not token_info:
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    
    sp = get_spotify()
    if not sp:
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
    uri = request.json.get('uri')
    device_id = request.json.get('device_id')
    position_ms = request.json.get('position_ms', 0)
    
    try:
        # Try to start playback with the provided device_id
        sp.start_playback(device_id=device_id, uris=[uri] if uri else None, position_ms=position_ms)
        response = jsonify({'status': 'playing'})
        return add_cors_headers(response)
    except Exception as e:
        
        # If that fails, try to find an available device
        try:
            devices_info = sp.devices()
            devices = devices_info.get('devices', [])
            
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
                sp.start_playback(device_id=device_id, uris=[uri] if uri else None, position_ms=position_ms)
                response = jsonify({'status': 'playing', 'device_id': device_id})
                return add_cors_headers(response)
            else:
                response = jsonify({'error': 'No active device found. Please open Spotify and start playing music.'}), 404
                return add_cors_headers(response)
                
        except Exception as e2:
            response = jsonify({'error': 'No active device found. Please open Spotify and start playing music.'}), 404
            return add_cors_headers(response)

@app.route('/pause', methods=['POST', 'OPTIONS'])
def pause():
    if request.method == 'OPTIONS':
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
    
    
    token_info = session.get('token_info')
    if not token_info:
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    
    sp = get_spotify()
    if not sp:
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
    device_id = request.json.get('device_id')
    
    try:
        sp.pause_playback(device_id=device_id)
        response = jsonify({'status': 'paused'})
        return add_cors_headers(response)
    except spotipy.exceptions.SpotifyException as e:
        logging.error(f"DEBUG: backend.py - Spotify pause error: {e}")
        if e.http_status == 403:
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
    
    token_info = session.get('token_info')
    if not token_info:
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    
    sp = get_spotify()
    if not sp:
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    devices_info = sp.devices()
    response = jsonify(devices_info)
    return add_cors_headers(response)

@app.route('/currently_playing')
def currently_playing():
    
    token_info = session.get('token_info')
    if not token_info:
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    
    sp = get_spotify()
    if not sp:
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    current = sp.current_playback()
    response = jsonify(current)
    return add_cors_headers(response)

@app.route('/debug')
def debug_page():
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
    token_info = session.get('token_info')
    if token_info:
        response = jsonify({
            'has_token': True,
            'token_type': type(token_info).__name__,
            'has_access_token': 'access_token' in token_info if isinstance(token_info, dict) else False
        })
        return add_cors_headers(response)
    else:
        response = jsonify({'has_token': False})
        return add_cors_headers(response)

@app.route('/album_tracks')
def album_tracks():
    
    token_info = session.get('token_info')
    if not token_info:
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    
    sp = get_spotify()
    if not sp:
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    album_id = request.args.get('album_id')
    try:
        results = sp.album_tracks(album_id, limit=50)
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
    response = jsonify({
        'message': 'pong',
        'origin': request.headers.get('Origin', 'No Origin'),
        'timestamp': time.time()
    })
    return add_cors_headers(response)

@app.route('/test_session', methods=['GET', 'OPTIONS'])
def test_session():
    """Test session functionality"""
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
    
    # Create a dummy token for testing
    dummy_token = {
        'access_token': 'dummy_token_for_testing',
        'token_type': 'Bearer',
        'expires_in': 3600,
        'scope': SPOTIFY_AUTH_SCOPE
    }
    
    session['token_info'] = dummy_token
    
    response = jsonify({
        'message': 'Dummy authentication created for testing',
        'has_token': True,
        'timestamp': time.time()
    })
    return add_cors_headers(response)

@app.route('/test_play', methods=['GET', 'OPTIONS'])
def test_play():
    """Test endpoint to check if play would work"""
    
    token_info = session.get('token_info')
    if not token_info:
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    
    sp = get_spotify()
    if not sp:
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
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
    
    token_info = session.get('token_info')
    if not token_info:
        response = jsonify({'error': 'Not authenticated - no token in session'}), 401
        return add_cors_headers(response[0])
    
    
    sp = get_spotify()
    if not sp:
        response = jsonify({'error': 'Not authenticated - invalid token'}), 401
        return add_cors_headers(response[0])
    
    # Try a simple search
    try:
        results = sp.search('test', type='album', limit=1)
        response = jsonify({
            'message': 'Search test successful',
            'has_token': True,
            'token_type': type(token_info).__name__,
            'search_results_count': len(results.get('albums', {}).get('items', [])),
            'timestamp': time.time()
        })
        return add_cors_headers(response)
    except Exception as e:
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
    
    
    try:
        data = request.get_json()
        image_url = data.get('image_url')
        
        if not image_url:
            response = jsonify({'error': 'No image_url provided'}), 400
            return add_cors_headers(response[0])
        
        
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
        
        return response
        
    except Exception as e:
        logging.error(f"DEBUG: backend.py - Error proxying image: {e}")
        response = jsonify({'error': f'Failed to proxy image: {str(e)}'}), 500
        return add_cors_headers(response[0])

@app.route('/download_album_cover', methods=['POST', 'OPTIONS'])
def download_album_cover():
    """Download album cover and return as base64 data"""
    if request.method == 'OPTIONS':
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
    
    
    try:
        data = request.get_json()
        image_url = data.get('image_url')
        
        if not image_url:
            response = jsonify({'error': 'No image_url provided'}), 400
            return add_cors_headers(response[0])
        
        
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
        
        return response
        
    except Exception as e:
        logging.error(f"DEBUG: backend.py - Error downloading album cover: {e}")
        response = jsonify({'error': f'Failed to download album cover: {str(e)}'}), 500
        return add_cors_headers(response[0])

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0') 