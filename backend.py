import os
from flask import Flask, request, jsonify, session, redirect
from flask_cors import CORS, cross_origin
from spotipy.oauth2 import SpotifyPKCE
import spotipy
from shared_constants import *

print("DEBUG: backend.py - Starting Flask backend initialization")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# --- CORS and Session Cookie Config for Cross-Origin Auth ---
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Allow cross-site cookies
app.config['SESSION_COOKIE_SECURE'] = True      # Required for SameSite=None (must use HTTPS)

# More comprehensive origins list including all localhost variants
CORS(app, supports_credentials=True, 
     origins=[
         # HTTPS variants
         "https://localhost:8000",
         "https://127.0.0.1:8000", 
         "https://[::1]:8000",
         "https://[::]:8000",
         # HTTP variants (for local development)
         "http://localhost:8000",
         "http://127.0.0.1:8000", 
         "http://[::1]:8000",
         "http://[::]:8000",
         # Production domains
         "https://spotisnake.onrender.com",
         "https://danielllesk.itch.io",
         "https://danielllesk.itch.io/spotisnake",
         "https://html-classic.itch.zone",
         "https://YOUR_FRONTEND_DOMAIN"
     ],
     allow_headers=["Content-Type", "Authorization", "Origin", "Accept"],
     expose_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Add CORS debugging middleware
@app.before_request
def log_request_info():
    print(f"DEBUG: backend.py - Request: {request.method} {request.path}")
    print(f"DEBUG: backend.py - Origin: {request.headers.get('Origin', 'No Origin')}")
    print(f"DEBUG: backend.py - User-Agent: {request.headers.get('User-Agent', 'No User-Agent')}")

# Add a catch-all OPTIONS handler for CORS preflight
@app.route('/<path:path>', methods=['OPTIONS'])
def catch_all_options(path):
    print(f"DEBUG: backend.py - OPTIONS preflight for /{path}")
    response = ('', 204)
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin, Accept'
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
    print("DEBUG: backend.py - get_spotify() called")
    token_info = session.get('token_info')
    if not token_info:
        print("DEBUG: backend.py - No token_info available (session)")
        return None
    
    print(f"DEBUG: backend.py - Token info type: {type(token_info)}")
    print(f"DEBUG: backend.py - Token info: {token_info}")
    
    try:
        if isinstance(token_info, dict) and 'access_token' in token_info:
            access_token = token_info['access_token']
        else:
            print("DEBUG: backend.py - Invalid token_info structure")
            return None
            
        print("DEBUG: backend.py - Creating Spotify client with token")
        return spotipy.Spotify(auth=access_token)
    except Exception as e:
        print(f"DEBUG: backend.py - Error creating Spotify client: {e}")
        return None

@app.route('/')
def index():
    print("DEBUG: backend.py - / endpoint called")
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
    print("DEBUG: backend.py - /login endpoint called")
    auth_url = sp_oauth.get_authorize_url()
    print(f"DEBUG: backend.py - Redirecting to auth URL: {auth_url}")
    return redirect(auth_url)

@app.route('/callback')
def callback():
    print("DEBUG: backend.py - /callback endpoint called")
    code = request.args.get('code')
    print(f"DEBUG: backend.py - Received auth code: {code[:10]}...")
    try:
        token_info = sp_oauth.get_access_token(code)
        print(f"DEBUG: backend.py - Raw token_info: {token_info}")
        print(f"DEBUG: backend.py - Token_info type: {type(token_info)}")
        # If token_info is a string, wrap it in a dict
        if isinstance(token_info, str):
            token_info = {'access_token': token_info}
        session['token_info'] = token_info
        print("DEBUG: backend.py - Token stored in session")
        # Test the token immediately
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_info = sp.current_user()
        print(f"DEBUG: backend.py - User authenticated: {user_info.get('id', 'unknown')}")
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
        print(f"DEBUG: backend.py - Error in callback: {e}")
        import traceback
        traceback.print_exc()
        return f"Login failed: {str(e)}", 400

@app.route('/me')
def me():
    print("DEBUG: backend.py - /me endpoint called")
    sp = get_spotify()
    if not sp:
        print("DEBUG: backend.py - Not authenticated for /me")
        response = jsonify({'error': 'Not authenticated'}), 401
        response[0].headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response[0].headers['Access-Control-Allow-Credentials'] = 'true'
        return response
    user_info = sp.current_user()
    print(f"DEBUG: backend.py - User info retrieved: {user_info.get('id', 'unknown')}")
    response = jsonify(user_info)
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@app.route('/search')
def search():
    print("DEBUG: backend.py - /search endpoint called")
    sp = get_spotify()
    if not sp:
        print("DEBUG: backend.py - Not authenticated for /search")
        return jsonify({'error': 'Not authenticated'}), 401
    q = request.args.get('q')
    print(f"DEBUG: backend.py - Searching for: {q}")
    results = sp.search(q, type='album', limit=5)
    print(f"DEBUG: backend.py - Found {len(results.get('albums', {}).get('items', []))} albums")
    return jsonify(results)

@app.route('/play', methods=['GET'])
def play_get_debug():
    print("DEBUG: backend.py - /play GET called (should not happen!)")
    print(f"DEBUG: backend.py - Request headers: {dict(request.headers)}")
    return "GET not allowed on /play", 405

@app.route('/play', methods=['POST'])
def play():
    print("DEBUG: backend.py - /play endpoint called")
    sp = get_spotify()
    if not sp:
        print("DEBUG: backend.py - Not authenticated for /play")
        return jsonify({'error': 'Not authenticated'}), 401
    uri = request.json.get('uri')
    device_id = request.json.get('device_id')
    position_ms = request.json.get('position_ms', 0)
    print(f"DEBUG: backend.py - Playing URI: {uri}, device: {device_id}, position: {position_ms}")
    sp.start_playback(device_id=device_id, uris=[uri] if uri else None, position_ms=position_ms)
    print("DEBUG: backend.py - Playback started successfully")
    return jsonify({'status': 'playing'})

@app.route('/pause', methods=['POST'])
def pause():
    print("DEBUG: backend.py - /pause endpoint called")
    sp = get_spotify()
    if not sp:
        print("DEBUG: backend.py - Not authenticated for /pause")
        return jsonify({'error': 'Not authenticated'}), 401
    device_id = request.json.get('device_id')
    print(f"DEBUG: backend.py - Pausing device: {device_id}")
    sp.pause_playback(device_id=device_id)
    print("DEBUG: backend.py - Playback paused successfully")
    return jsonify({'status': 'paused'})

@app.route('/devices')
def devices():
    print("DEBUG: backend.py - /devices endpoint called")
    sp = get_spotify()
    if not sp:
        print("DEBUG: backend.py - Not authenticated for /devices")
        return jsonify({'error': 'Not authenticated'}), 401
    devices_info = sp.devices()
    print(f"DEBUG: backend.py - Found {len(devices_info.get('devices', []))} devices")
    return jsonify(devices_info)

@app.route('/currently_playing')
def currently_playing():
    print("DEBUG: backend.py - /currently_playing endpoint called")
    sp = get_spotify()
    if not sp:
        print("DEBUG: backend.py - Not authenticated for /currently_playing")
        return jsonify({'error': 'Not authenticated'}), 401
    current = sp.current_playback()
    print(f"DEBUG: backend.py - Current playback: {current.get('item', {}).get('name', 'none') if current else 'none'}")
    return jsonify(current)

@app.route('/debug')
def debug_page():
    print("DEBUG: backend.py - /debug page called")
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
    print("DEBUG: backend.py - /debug_session endpoint called")
    token_info = session.get('token_info')
    if token_info:
        print("DEBUG: backend.py - Session has token_info")
        return jsonify({
            'has_token': True,
            'token_type': type(token_info).__name__,
            'has_access_token': 'access_token' in token_info if isinstance(token_info, dict) else False
        })
    else:
        print("DEBUG: backend.py - Session has no token_info")
        return jsonify({'has_token': False})

@app.route('/album_tracks')
def album_tracks():
    print("DEBUG: backend.py - /album_tracks endpoint called")
    sp = get_spotify()
    if not sp:
        print("DEBUG: backend.py - Not authenticated for /album_tracks")
        return jsonify({'error': 'Not authenticated'}), 401
    album_id = request.args.get('album_id')
    print(f"DEBUG: backend.py - Getting tracks for album: {album_id}")
    results = sp.album_tracks(album_id, limit=50)
    print(f"DEBUG: backend.py - Found {len(results.get('items', []))} tracks")
    return jsonify(results)

if __name__ == '__main__':
    print("DEBUG: backend.py - Starting Flask server on port 8000")
    app.run(debug=True, port=8000, host='0.0.0.0') 