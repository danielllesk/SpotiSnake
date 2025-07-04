import os
from flask import Flask, request, jsonify, session, redirect
from flask_cors import CORS, cross_origin
from spotipy.oauth2 import SpotifyPKCE
import spotipy
from shared_constants import *

print("DEBUG: backend.py - Starting Flask backend initialization")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
CORS(app)  # This will allow all origins (for dev only!)
# For production, use:
# CORS(app, origins=["http://127.0.0.1:8000", "http://localhost:8000", "https://yourgame.com"])

# Add a catch-all OPTIONS handler for CORS preflight
@app.route('/<path:path>', methods=['OPTIONS'])
def catch_all_options(path):
    print(f"DEBUG: backend.py - OPTIONS preflight for /{path}")
    return ('', 204)

print("DEBUG: backend.py - Setting up Spotify PKCE authentication")
sp_oauth = SpotifyPKCE(
    client_id=SPOTIFY_CLIENT_ID,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SPOTIFY_AUTH_SCOPE,
    open_browser=False,  # handles redirect
    cache_path=None
)

# Global token storage (in production, use a proper database)
global_token_info = None

def get_spotify():
    print("DEBUG: backend.py - get_spotify() called")
    global global_token_info
    if not global_token_info:
        print("DEBUG: backend.py - No token_info available")
        return None
    
    print(f"DEBUG: backend.py - Token info type: {type(global_token_info)}")
    print(f"DEBUG: backend.py - Token info: {global_token_info}")
    
    try:
        if isinstance(global_token_info, dict) and 'access_token' in global_token_info:
            access_token = global_token_info['access_token']
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
    global global_token_info
    code = request.args.get('code')
    print(f"DEBUG: backend.py - Received auth code: {code[:10]}...")
    
    try:
        token_info = sp_oauth.get_access_token(code)
        print(f"DEBUG: backend.py - Raw token_info: {token_info}")
        print(f"DEBUG: backend.py - Token_info type: {type(token_info)}")
        # If token_info is a string, wrap it in a dict
        if isinstance(token_info, str):
            token_info = {'access_token': token_info}
        global_token_info = token_info
        print("DEBUG: backend.py - Token stored globally")
        
        # Test the token immediately
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_info = sp.current_user()
        print(f"DEBUG: backend.py - User authenticated: {user_info.get('id', 'unknown')}")
        
        return """
        <html>
            <head><title>Login Successful</title></head>
            <body>
                <h1>Login Successful!</h1>
                <p>You can close this tab and return to the game.</p>
                <p>If the game doesn't recognize your login, try refreshing the game.</p>
                <script>
                    // Auto-close after 3 seconds
                    setTimeout(function() {
                        window.close();
                    }, 3000);
                </script>
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
        return jsonify({'error': 'Not authenticated'}), 401
    user_info = sp.current_user()
    print(f"DEBUG: backend.py - User info retrieved: {user_info.get('id', 'unknown')}")
    return jsonify(user_info)

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