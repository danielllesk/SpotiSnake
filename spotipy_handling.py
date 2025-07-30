print("spotipy_handling.py loaded")
print("DEBUG: spotipy_handling.py - Starting module initialization")

import pygame
from shared_constants import *
from io import BytesIO
import random
import asyncio
import os
import time
import js
print("DEBUG: spotipy_handling.py - All imports completed")

# Use deployed backend URL for production
BACKEND_URL = os.environ.get("SPOTISNAKE_BACKEND_URL", "https://spotisnake.onrender.com")
print(f"DEBUG: spotipy_handling.py - Using backend URL: {BACKEND_URL}")

# Test backend connectivity on startup
def test_backend_connectivity():
    """Test if backend is accessible and check CORS headers"""
    try:
        js_code = f'''
        console.log("DEBUG: Testing backend connectivity to: {BACKEND_URL}");
        console.log("DEBUG: Current origin: " + window.location.origin);
        
        // Test without credentials first
        fetch("{BACKEND_URL}/ping", {{
            method: "GET"
        }})
        .then(response => {{
            console.log("DEBUG: Backend test (no credentials) - Status:", response.status);
            console.log("DEBUG: Backend test (no credentials) - Headers:", response.headers);
            return response.text();
        }})
        .then(text => {{
            console.log("DEBUG: Backend test (no credentials) - Response:", text);
            window.backend_test_result = {{ status: 200, text: text }};
        }})
        .catch(error => {{
            console.log("DEBUG: Backend test (no credentials) - Error:", error);
            window.backend_test_result = {{ status: 500, error: error.toString() }};
        }});
        '''
        js.eval(js_code)
        print("DEBUG: spotipy_handling.py - Backend connectivity test initiated")
        
        # Wait a bit and check the result
        import time
        time.sleep(0.5)
        
        if hasattr(js.window, 'backend_test_result'):
            result = js.window.backend_test_result
            print(f"DEBUG: spotipy_handling.py - Backend test result: {result}")
        else:
            print("DEBUG: spotipy_handling.py - No backend test result available")
            
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Backend connectivity test failed: {e}")

# Run connectivity test
test_backend_connectivity()

# Remove requests session for browser build
# session = requests.Session()
# session.headers.update({
#     'User-Agent': 'SpotiSnake/1.0',
#     'Accept': 'application/json',
#     'Content-Type': 'application/json'
# })

clock = pygame.time.Clock()
pygame.init()

USER_ABORT_GAME_FROM_SEARCH = "USER_ABORT_GAME_FROM_SEARCH"

# Global state to prevent multiple login attempts
is_logging_in = False

# Local testing flag - set to True to bypass authentication for local testing
LOCAL_TESTING_MODE = False  # Set to False for production

device_id_cache = None  # Cache for Spotify device ID

def clear_device_id_cache():
    global device_id_cache
    device_id_cache = None

def backend_login():
    """Handles Spotify login through the backend server."""
    global is_logging_in
    print("DEBUG: spotipy_handling.py - backend_login called")
    
    if is_logging_in:
        print("DEBUG: spotipy_handling.py - Login already in progress, ignoring")
        return
    
    is_logging_in = True
    login_url = f"{BACKEND_URL}/login"
    print(f"DEBUG: spotipy_handling.py - Opening login URL: {login_url}")

    try:
        import js  # Only available in Pyodide/Pygbag
        if hasattr(js, 'window'):
            js.window.open(login_url, "_blank")
            print("DEBUG: spotipy_handling.py - Opened login URL in browser (js.window.open)")
        else:
            print("DEBUG: spotipy_handling.py - js module available but no window attribute")
            is_logging_in = False
    except ImportError:
        # Fallback for desktop Python
        try:
            import webbrowser
            webbrowser.open(login_url)
            print("DEBUG: spotipy_handling.py - Opened login URL in desktop browser (webbrowser.open)")
        except Exception as e:
            print(f"DEBUG: spotipy_handling.py - Error opening browser: {e}")
            is_logging_in = False

def is_pyodide():
    try:
        import js
        return hasattr(js, 'window')
    except ImportError:
        return False

# Helper to await JS Promises in Pygbag/Pyodide
import types

def await_js_promise(promise):
    # In Pyodide/Pygbag, we can directly await JS promises
    try:
        # Try to use the promise directly
        return promise
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in await_js_promise: {e}")
        # Fallback: return the promise as-is
        return promise

# Expose a Python callback for JS to call with the auth result
def handle_auth_result(result_json):
    import json
    print(f"DEBUG: spotipy_handling.py - handle_auth_result called with: {result_json}")
    try:
        data = json.loads(result_json)
    except json.JSONDecodeError:
        print("DEBUG: spotipy_handling.py - Failed to parse JSON, got:", result_json[:200])
        data = {}
    global is_logging_in
    if data.get('id'):
        print("DEBUG: spotipy_handling.py - Authentication successful (callback)")
        is_logging_in = False
        js.auth_success = True
    else:
        print("DEBUG: spotipy_handling.py - Authentication failed (callback)")
        js.auth_success = False

js.window.handle_auth_result = handle_auth_result  # Attach to window explicitly
js.auth_success = False

async def check_authenticated():
    print("DEBUG: spotipy_handling.py - check_authenticated called (async version)")
    import js
    import json
    
    js_code = f'''
    console.log("JS: Starting fetch for auth check");
    fetch("{BACKEND_URL}/me", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        console.log("JS: /me status:", response.status);
        console.log("JS: /me ok:", response.ok);
        return response.text().then(text => {{
            return {{ status: response.status, text: text }};
        }});
    }})
    .then(result => {{
        console.log("JS: /me response text:", result.text);
        window.auth_check_result = result;
    }})
    .catch(error => {{
        console.log("JS: Auth check error:", error);
        window.auth_check_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.3)  # Wait a bit longer for the fetch to complete
        
        if hasattr(js.window, 'auth_check_result'):
            result = js.window.auth_check_result
            print(f"DEBUG: spotipy_handling.py - Auth check result: {result}")
            
            # Handle JavaScript object properly
            try:
                if hasattr(result, 'status'):
                    status = result.status
                    print(f"DEBUG: spotipy_handling.py - Got status from object: {status}")
                    if status == 200:
                        print("DEBUG: spotipy_handling.py - User authenticated (status 200)")
                        return True
                    else:
                        print(f"DEBUG: spotipy_handling.py - Auth check failed with status: {status}")
                        return False
                elif isinstance(result, dict):
                    status = result.get('status', 500)
                    print(f"DEBUG: spotipy_handling.py - Got status from dict: {status}")
                    if status == 200:
                        print("DEBUG: spotipy_handling.py - User authenticated (dict result)")
                        return True
                    else:
                        print(f"DEBUG: spotipy_handling.py - Auth check failed with status: {status}")
                        return False
                else:
                    print(f"DEBUG: spotipy_handling.py - Auth check result is unexpected type: {type(result)}")
                    # Try to access properties anyway
                    try:
                        status = getattr(result, 'status', 500)
                        print(f"DEBUG: spotipy_handling.py - Got status via getattr: {status}")
                        if status == 200:
                            print("DEBUG: spotipy_handling.py - User authenticated (getattr result)")
                            return True
                        else:
                            print(f"DEBUG: spotipy_handling.py - Auth check failed with status: {status}")
                            return False
                    except Exception as e:
                        print(f"DEBUG: spotipy_handling.py - Error accessing object properties: {e}")
                        return False
            except Exception as e:
                print(f"DEBUG: spotipy_handling.py - Error processing result: {e}")
                return False
        else:
            print("DEBUG: spotipy_handling.py - No auth check result available")
            return False
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in check_authenticated: {e}")
        return False

def search_album(query):
    print(f"DEBUG: spotipy_handling.py - search_album called with query: {query}")
    # In browser, this should be handled by backend API call
    print("DEBUG: spotipy_handling.py - search_album should be handled by backend in browser build")
    return None

def play_track(uri, device_id=None, position_ms=0):
    print(f"DEBUG: spotipy_handling.py - play_track called with uri: {uri}, device_id: {device_id}, position_ms: {position_ms}")
    # In browser, this should be handled by backend API call
    print("DEBUG: spotipy_handling.py - play_track should be handled by backend in browser build")
    return False

def pause_playback(device_id=None):
    print(f"DEBUG: spotipy_handling.py - pause_playback called with device_id: {device_id}")
    # In browser, this should be handled by backend API call
    print("DEBUG: spotipy_handling.py - pause_playback should be handled by backend in browser build")
    return False

def get_devices():
    print("DEBUG: spotipy_handling.py - get_devices called")
    # In browser, this should be handled by backend API call
    print("DEBUG: spotipy_handling.py - get_devices should be handled by backend in browser build")
    return None

def get_current_playback():
    print("DEBUG: spotipy_handling.py - get_current_playback called")
    # In browser, this should be handled by backend API call
    print("DEBUG: spotipy_handling.py - get_current_playback should be handled by backend in browser build")
    return None

def get_album_tracks(album_id):
    print(f"DEBUG: spotipy_handling.py - get_album_tracks called with album_id: {album_id}")
    # In browser, this should be handled by backend API call
    print("DEBUG: spotipy_handling.py - get_album_tracks should be handled by backend in browser build")
    return None

async def download_and_resize_album_cover_async(url, target_width, target_height):
    """Download and resize album cover asynchronously using backend proxy to avoid CORS"""
    print(f"DEBUG: spotipy_handling.py - download_and_resize_album_cover_async called with url: {url}")
    
    if not url:
        print(f"DEBUG: spotipy_handling.py - No URL provided, creating fallback")
        return create_fallback_album_cover(target_width, target_height)
    
    import js
    import base64
    
    # Use backend proxy to avoid CORS issues
    js_code = f'''
    fetch("{BACKEND_URL}/proxy_image", {{
        method: "POST",
        headers: {{
            "Content-Type": "application/json"
        }},
        credentials: "include",
        body: JSON.stringify({{"image_url": "{url}"}})
    }})
    .then(response => {{
        if (!response.ok) {{
            throw new Error(`HTTP error! status: ${{response.status}}`);
        }}
        return response.blob();
    }})
    .then(blob => {{
        return new Promise((resolve, reject) => {{
            const reader = new FileReader();
            reader.onload = () => {{
                const base64 = reader.result.split(',')[1];
                window.image_download_result = {{ status: 200, data: base64 }};
            }};
            reader.onerror = () => {{
                window.image_download_result = {{ status: 500, error: "Failed to read blob" }};
            }};
            reader.readAsDataURL(blob);
        }});
    }})
    .catch(error => {{
        console.log("Image download error:", error);
        window.image_download_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        await asyncio.sleep(0.3)  # Wait a bit longer for the fetch to complete
        
        if hasattr(js.window, 'image_download_result'):
            result = js.window.image_download_result
            print(f"DEBUG: spotipy_handling.py - Image download result: {result}")
            
            if isinstance(result, dict) and result.get('status') == 200:
                # Convert base64 to pygame surface
                try:
                    base64_data = result.get('data')
                    if base64_data:
                        # Create a temporary file-like object from base64
                        image_data = base64.b64decode(base64_data)
                        import io
                        image_stream = io.BytesIO(image_data)
                        
                        # Load image with pygame
                        image = pygame.image.load(image_stream)
                        
                        # Resize to target dimensions
                        resized_image = pygame.transform.scale(image, (target_width, target_height))
                        
                        print(f"DEBUG: spotipy_handling.py - Album cover downloaded and resized successfully: {resized_image.get_size()}")
                        return resized_image
                except Exception as e:
                    print(f"DEBUG: spotipy_handling.py - Error processing downloaded image: {e}")
                    return create_fallback_album_cover(target_width, target_height)
            else:
                print(f"DEBUG: spotipy_handling.py - Image download failed: {result}")
                return create_fallback_album_cover(target_width, target_height)
        else:
            print("DEBUG: spotipy_handling.py - No image download result available")
            return create_fallback_album_cover(target_width, target_height)
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in download_and_resize_album_cover_async: {e}")
        return create_fallback_album_cover(target_width, target_height)

def download_and_resize_album_cover(url, target_width, target_height):
    print(f"DEBUG: spotipy_handling.py - download_and_resize_album_cover called with url: {url}")
    
    if not url:
        print(f"DEBUG: spotipy_handling.py - No URL provided, creating fallback")
        return create_fallback_album_cover(target_width, target_height)
    
    # Use the async version for browser builds
    try:
        # Create a simple event loop to run the async function
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use run_until_complete
            # So we'll use the fallback for now
            print(f"DEBUG: spotipy_handling.py - Using fallback cover (async context)")
            return create_fallback_album_cover(target_width, target_height)
        else:
            return loop.run_until_complete(download_and_resize_album_cover_async(url, target_width, target_height))
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in sync wrapper: {e}")
        return create_fallback_album_cover(target_width, target_height)

def create_fallback_album_cover(target_width, target_height):
    """Create a fallback album cover when image download fails"""
    try:
        surface = pygame.Surface((target_width, target_height))
        # Use a gradient-like effect with different colors
        for y in range(target_height):
            color_value = int(50 + (y / target_height) * 100)
            pygame.draw.line(surface, (color_value, color_value, color_value), (0, y), (target_width, y))
        
        # Add some text to indicate it's an album cover
        try:
            font = pygame.font.SysFont("Arial", min(target_width, target_height) // 8)
            text = font.render("ALBUM", True, (200, 200, 200))
            text_rect = text.get_rect(center=(target_width // 2, target_height // 2))
            surface.blit(text, text_rect)
            print(f"DEBUG: spotipy_handling.py - Fallback album cover created with text")
        except Exception as e:
            print(f"DEBUG: spotipy_handling.py - Font rendering failed: {e}")
            pass  # If font rendering fails, just use the gradient
        
        print(f"DEBUG: spotipy_handling.py - Fallback album cover surface created: {surface.get_size()}")
        return surface
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error creating fallback album cover: {e}")
        return None

def get_spotify_device():
    global device_id_cache
    print("DEBUG: spotipy_handling.py - get_spotify_device called")
    if device_id_cache is not None:
        print(f"DEBUG: spotipy_handling.py - Returning cached device_id: {device_id_cache}")
        return device_id_cache
    
    # Use synchronous approach with js.eval
    import js
    js_code = f'''
    fetch("{BACKEND_URL}/devices", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        console.log("Devices sync response status:", response.status);
        return response.text();
    }})
    .then(text => {{
        console.log("Devices sync response text:", text);
        window.devices_sync_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        console.log("Devices sync error:", error);
        window.devices_sync_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import time
        time.sleep(0.1)  # Wait for async operation
        
        if hasattr(js.window, 'devices_sync_result'):
            result = js.window.devices_sync_result
            # Handle both object and string cases
            if isinstance(result, dict):
                if result.get('status') == 200:
                    import json
                    devices = json.loads(result.get('text', '{}'))
                    if devices and devices.get('devices'):
                        active_device = next((d for d in devices['devices'] if d.get('is_active')), None)
                        if active_device:
                            print(f"DEBUG: spotipy_handling.py - Using active device: {active_device['id']}")
                            device_id_cache = active_device['id']
                            return device_id_cache
                        print(f"DEBUG: spotipy_handling.py - Using first device: {devices['devices'][0]['id']}")
                        device_id_cache = devices['devices'][0]['id']
                        return device_id_cache
            elif isinstance(result, str):
                # If it's a string, try to parse it as JSON
                try:
                    import json
                    parsed_result = json.loads(result)
                    if parsed_result and parsed_result.get('devices'):
                        active_device = next((d for d in parsed_result['devices'] if d.get('is_active')), None)
                        if active_device:
                            print(f"DEBUG: spotipy_handling.py - Using active device: {active_device['id']}")
                            device_id_cache = active_device['id']
                            return device_id_cache
                        print(f"DEBUG: spotipy_handling.py - Using first device: {parsed_result['devices'][0]['id']}")
                        device_id_cache = parsed_result['devices'][0]['id']
                        return device_id_cache
                except:
                    pass
            else:
                # If it's an object, try to access properties directly
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        import json
                        devices = json.loads(text)
                        if devices and devices.get('devices'):
                            active_device = next((d for d in devices['devices'] if d.get('is_active')), None)
                            if active_device:
                                print(f"DEBUG: spotipy_handling.py - Using active device: {active_device['id']}")
                                device_id_cache = active_device['id']
                                return device_id_cache
                            print(f"DEBUG: spotipy_handling.py - Using first device: {devices['devices'][0]['id']}")
                            device_id_cache = devices['devices'][0]['id']
                            return device_id_cache
                except:
                    pass
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in get_spotify_device: {e}")
    
    print("DEBUG: spotipy_handling.py - No devices found")
    return None

def play_track_sync(track_uri, position_ms):
    print(f"DEBUG: spotipy_handling.py - play_track_sync called with track_uri: {track_uri}, position_ms: {position_ms}")
    
    # Use synchronous approach with js.eval
    import js
    import json
    
    js_code = f'''
    fetch("{BACKEND_URL}/play", {{
        method: "POST",
        headers: {{
            "Content-Type": "application/json"
        }},
        credentials: "include",
        body: JSON.stringify({{"uri": "{track_uri}", "position_ms": {position_ms}}})
    }})
    .then(response => {{
        console.log("Play sync response status:", response.status);
        return response.text();
    }})
    .then(text => {{
        console.log("Play sync response text:", text);
        window.play_sync_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        console.log("Play sync error:", error);
        window.play_sync_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import time
        time.sleep(0.1)  # Wait for async operation
        
        if hasattr(js.window, 'play_sync_result'):
            result = js.window.play_sync_result
            print(f"DEBUG: spotipy_handling.py - Play sync result: {result}")
            # Handle both object and string cases
            if isinstance(result, dict):
                return result.get('status', 500) == 200
            elif isinstance(result, str):
                # If it's a string, try to parse it as JSON
                try:
                    parsed_result = json.loads(result)
                    return parsed_result.get('status', 500) == 200
                except:
                    return False
            else:
                # If it's an object, try to access properties directly
                try:
                    status = getattr(result, 'status', 500)
                    return status == 200
                except:
                    return False
        else:
            print("DEBUG: spotipy_handling.py - No play sync result available")
            return False
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in play_track_sync: {e}")
        return False

def play_uri_with_details(track_uri, position_ms=0):
    print(f"DEBUG: spotipy_handling.py - play_uri_with_details called with track_uri: {track_uri}, position_ms: {position_ms}")
    played_successfully = play_track_sync(track_uri, position_ms)
    print(f"DEBUG: spotipy_handling.py - play_uri_with_details result: {played_successfully}")
    return played_successfully, "Unknown Track", "Unknown Artist"

async def play_random_track_from_album(album_id, song_info_updater_callback):
    print(f"DEBUG: spotipy_handling.py - play_random_track_from_album called with album_id: {album_id}")
    
    # Extract album ID from URI if needed
    if album_id.startswith('spotify:album:'):
        album_id = album_id.replace('spotify:album:', '')
        print(f"DEBUG: spotipy_handling.py - Extracted album ID: {album_id}")
    
    # Use async approach with js.eval for getting album tracks
    import js
    import json
    import random
    
    js_code = f'''
    fetch("{BACKEND_URL}/album_tracks?album_id={album_id}", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        return response.text();
    }})
    .then(text => {{
        window.album_tracks_sync_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        window.album_tracks_sync_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.1)  # Wait for async operation
        
        tracks_data = None
        if hasattr(js.window, 'album_tracks_sync_result'):
            result = js.window.album_tracks_sync_result
            # Handle both object and string cases
            if isinstance(result, dict):
                if result.get('status') == 200:
                    tracks_data = json.loads(result.get('text', '{}'))
            elif isinstance(result, str):
                # If it's a string, try to parse it as JSON
                try:
                    tracks_data = json.loads(result)
                except:
                    pass
            else:
                # If it's an object, try to access properties directly
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        tracks_data = json.loads(text)
                except:
                    pass
        
        tracks = tracks_data.get('items', []) if tracks_data else []
        if not tracks:
            song_info_updater_callback("No Tracks In Album", "N/A", False)
            return
        
        track = random.choice(tracks)
        chosen_track_uri = track['uri']
        track_name = track.get('name', 'Unknown Track')
        track_artist = track.get('artists', [{}])[0].get('name', 'Unknown Artist')
        position_ms = random.randint(0, max(0, track.get('duration_ms', 0) - 30000))
        is_easter_egg_track_selected = (chosen_track_uri == EASTER_EGG_TRACK_URI)
        
        # Use async approach for playing track
        played_successfully = await play_track_via_backend(chosen_track_uri, position_ms)
        if played_successfully:
            song_info_updater_callback(track_name, track_artist, is_easter_egg_track_selected)
        else:
            song_info_updater_callback(track_name, f"(Failed: {track_artist})", False)
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in play_random_track_from_album: {e}")
        song_info_updater_callback("Error Loading Album", "N/A", False)

async def safe_pause_playback():
    print("DEBUG: spotipy_handling.py - safe_pause_playback called (disabled due to CORS)")
    # Temporarily disable pause to avoid CORS issues
    return True

async def cleanup():
    print("DEBUG: spotipy_handling.py - cleanup called")
    try:
        await safe_pause_playback()
        time.sleep(0.3)
        print("DEBUG: spotipy_handling.py - cleanup completed")
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Exception in cleanup: {e}")

async def get_album_search_input(screen, font):
    print("DEBUG: spotipy_handling.py - get_album_search_input called (START)")
    
    # Play background music during search
    async def music_task_wrapper():
        """Plays background music during album search."""
        print("DEBUG: spotipy_handling.py - Starting background music for search")
        await play_track_via_backend(SEARCH_TRACK_URI, 3000)

    try:
        await music_task_wrapper()
        print("DEBUG: spotipy_handling.py - Background music started (awaited)")
    except RuntimeError:
        print("DEBUG: spotipy_handling.py - No event loop running for background music")
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Exception starting background music: {e}")

    input_box = pygame.Rect(width // 2 - 200, 100, 400, 50)
    results_area = pygame.Rect(width // 2 - 200, 160, 400, 300)
    color_inactive = DARK_BLUE
    color_active = LIGHT_BLUE
    color = color_inactive
    active = False
    text = ''
    search_results = []
    album_covers = {}
    quit_button_font = pygame.font.SysFont("Press Start 2P", 20)
    quit_button_rect_local = pygame.Rect(20, height - 70, 250, 50)

    async def download_album_covers_async():
        """Download album covers asynchronously in the background"""
        nonlocal album_covers
        for album in search_results:
            if album['image_url'] and album['uri'] not in album_covers:
                try:
                    cover = await download_and_resize_album_cover_async(album['image_url'], 50, 50)
                    if cover:
                        album_covers[album['uri']] = cover
                        print(f"DEBUG: spotipy_handling.py - Downloaded cover for {album['name']}")
                except Exception as e:
                    print(f"DEBUG: spotipy_handling.py - Failed to download cover for {album['name']}: {e}")

    def draw_search_results_local():
        nonlocal album_covers
        if search_results:
            y_offset = results_area.y + 10
            for album in search_results:
                result_rect = pygame.Rect(results_area.x + 5, y_offset, results_area.width - 10, 70)
                if result_rect.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(screen, LIGHT_BLUE, result_rect)
                else:
                    pygame.draw.rect(screen, WHITE, result_rect)
                pygame.draw.rect(screen, DARK_BLUE, result_rect, 1)
                if album['uri'] in album_covers and album_covers[album['uri']]:
                    screen.blit(album_covers[album['uri']], (result_rect.x + 10, result_rect.y + 10))
                    text_start_x = result_rect.x + 70
                else:
                    text_start_x = result_rect.x + 10
                name_font_local = pygame.font.SysFont('corbel', 18)
                name_surf = name_font_local.render(album['name'], True, BLACK)
                screen.blit(name_surf, (text_start_x, result_rect.y + 10))
                artist_font_local = pygame.font.SysFont('corbel', 16)
                artist_surf = artist_font_local.render(album['artist'], True, DARK_GREY)
                screen.blit(artist_surf, (text_start_x, result_rect.y + 35))
                y_offset += 80
        elif text:
            no_results_surf = font.render("No results. Press Enter to search.", True, WHITE)
            screen.blit(no_results_surf, (results_area.x + 10, results_area.y + 10))
        else:
            no_results_surf = font.render("Type to search. Press Enter.", True, WHITE)
            screen.blit(no_results_surf, (results_area.x + 10, results_area.y + 10))

    loop_iteration = 0
    while True:
        loop_iteration += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try:
                    await safe_pause_playback()
                    await asyncio.sleep(0.2)
                except Exception:
                    pass
                print("DEBUG: spotipy_handling.py - User quit during album search UI")
                print("DEBUG: spotipy_handling.py - get_album_search_input returning USER_ABORT_GAME_FROM_SEARCH")
                return USER_ABORT_GAME_FROM_SEARCH
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                else:
                    active = False
                color = color_active if active else color_inactive
                if quit_button_rect_local.collidepoint(event.pos):
                    try:
                        await safe_pause_playback()
                        await asyncio.sleep(0.2)
                    except Exception:
                        pass
                    print("DEBUG: spotipy_handling.py - User clicked BACK TO MENU during album search UI")
                    print("DEBUG: spotipy_handling.py - get_album_search_input returning BACK_TO_MENU")
                    return "BACK_TO_MENU"
                if search_results:
                    y_offset_click = results_area.y + 10
                    for album_click in search_results:
                        result_rect_click = pygame.Rect(results_area.x + 5, y_offset_click, results_area.width - 10, 70)
                        if result_rect_click.collidepoint(event.pos):
                            print(f"DEBUG: spotipy_handling.py - User selected album: {album_click}")
                            print("DEBUG: spotipy_handling.py - get_album_search_input returning album result")
                            return album_click
                        y_offset_click += 80
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        if text:
                            print(f"DEBUG: spotipy_handling.py - Searching for: {text}")
                            # Use backend search
                            search_results = []
                            backend_results = await search_album_via_backend(text)
                            if backend_results and 'albums' in backend_results and 'items' in backend_results['albums']:
                                albums_found = len(backend_results['albums']['items'])
                                print(f"DEBUG: spotipy_handling.py - Found {albums_found} albums")
                                for album in backend_results['albums']['items']:
                                    album_data = {
                                        'name': album.get('name', 'Unknown Album'),
                                        'uri': album.get('uri', ''),
                                        'image_url': album.get('images', [{}])[0].get('url', None) if album.get('images') else None,
                                        'artist': album.get('artists', [{}])[0].get('name', 'Unknown Artist') if album.get('artists') else 'Unknown Artist'
                                    }
                                    search_results.append(album_data)
                                print(f"DEBUG: spotipy_handling.py - Added {len(search_results)} albums to search results")
                                # Download album covers immediately
                                print("DEBUG: spotipy_handling.py - Starting album cover downloads")
                                for album in search_results:
                                    if album['image_url']:
                                        try:
                                            cover = await download_and_resize_album_cover_async(album['image_url'], 50, 50)
                                            if cover:
                                                album_covers[album['uri']] = cover
                                                print(f"DEBUG: spotipy_handling.py - Downloaded cover for {album['name']}")
                                            else:
                                                print(f"DEBUG: spotipy_handling.py - Failed to download cover for {album['name']}")
                                        except Exception as e:
                                            print(f"DEBUG: spotipy_handling.py - Error downloading cover for {album['name']}: {e}")
                                print("DEBUG: spotipy_handling.py - Album cover downloads completed")
                            else:
                                print(f"DEBUG: spotipy_handling.py - No albums found in search results")
                            album_covers.clear()
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                        if not text:
                            search_results = []
                            album_covers.clear()
                    else:
                        text += event.unicode
        screen.fill((30, 30, 30))
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        label_font = pygame.font.SysFont("Press Start 2P", 25)
        label = label_font.render("Search for an album:", True, WHITE)
        screen.blit(label, (input_box.x, input_box.y - 40))
        txt_surface = font.render(text, True, BLACK)
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        pygame.draw.rect(screen, color, input_box, 2)
        draw_search_results_local()
        pygame.draw.rect(screen, LIGHT_BLUE, quit_button_rect_local)
        quit_text_surf = quit_button_font.render("BACK TO MENU", True, BLACK)
        quit_text_rect = quit_text_surf.get_rect(center=quit_button_rect_local.center)
        screen.blit(quit_text_surf, quit_text_rect)
        pygame.display.flip()
        await asyncio.sleep(0.01)
    print("DEBUG: spotipy_handling.py - get_album_search_input called (END, should never reach here)")

# Browser-safe: play track via backend
async def play_track_via_backend(uri, position_ms=0):
    print(f"DEBUG: spotipy_handling.py - play_track_via_backend called with uri={uri}, position_ms={position_ms}")
    import js
    import json
    
    # Use a simpler approach with js.eval for the entire fetch operation
    js_code = f'''
    fetch("{BACKEND_URL}/play", {{
        method: "POST",
        headers: {{
            "Content-Type": "application/json"
        }},
        credentials: "include",
        body: JSON.stringify({{"uri": "{uri}", "position_ms": {position_ms}}})
    }})
    .then(response => {{
        return response.text();
    }})
    .then(text => {{
        window.play_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        window.play_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        # Execute the fetch in JavaScript
        js.eval(js_code)
        
        # Wait a bit for the async operation to complete
        import asyncio
        await asyncio.sleep(0.1)
        
        # Check the result
        if hasattr(js.window, 'play_result'):
            result = js.window.play_result
            
            # Handle different result types
            if isinstance(result, dict):
                status = result.get('status', 500)
                if status == 200:
                    return True
                elif status == 404:
                    print("DEBUG: spotipy_handling.py - No active device found. Please open Spotify and start playing music.")
                    return False
                else:
                    return False
            elif isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                    status = parsed_result.get('status', 500)
                    if status == 200:
                        return True
                    elif status == 404:
                        print("DEBUG: spotipy_handling.py - No active device found. Please open Spotify and start playing music.")
                        return False
                    else:
                        return False
                except json.JSONDecodeError:
                    return False
            else:
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        return True
                    elif status == 404:
                        print("DEBUG: spotipy_handling.py - No active device found. Please open Spotify and start playing music.")
                        return False
                    else:
                        return False
                except Exception:
                    return False
        return False
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in play_track_via_backend: {e}")
        return False

# Browser-safe: search album via backend
async def search_album_via_backend(query):
    import js
    import json
    
    # URL encode the query to handle special characters
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    
    js_code = f'''
    // Clear previous search result
    window.search_result = null;
    console.log("JS: Starting search for: {query}");
    console.log("JS: Fetching from URL: {BACKEND_URL}/search?q={encoded_query}");
    
    // Use a simpler approach with better error handling
    try {{
        console.log("JS: About to execute fetch");
        fetch("{BACKEND_URL}/search?q={encoded_query}", {{
            method: "GET",
            credentials: "include",
            headers: {{
                "Accept": "application/json"
            }}
        }})
        .then(function(response) {{
            console.log("JS: Search response status:", response.status);
            console.log("JS: Search response ok:", response.ok);
            
            if (!response.ok) {{
                console.log("JS: Response not ok, getting error text");
                return response.text().then(function(text) {{
                    console.log("JS: Error response text:", text);
                    window.search_result = {{ status: response.status, text: text, error: true }};
                    console.log("JS: Error result stored in window");
                }});
            }}
            return response.text();
        }})
        .then(function(text) {{
            if (text) {{
                console.log("JS: Search response text length:", text.length);
                console.log("JS: Search response text preview:", text.substring(0, 200));
                window.search_result = {{ status: 200, text: text }};
                console.log("JS: Search result stored in window");
                console.log("JS: Window search_result value:", window.search_result);
            }}
        }})
        .catch(function(error) {{
            console.log("JS: Search fetch error:", error);
            console.log("JS: Error message:", error.message);
            window.search_result = {{ status: 500, error: error.toString(), message: error.message }};
            console.log("JS: Search error stored in window");
        }});
        console.log("JS: Fetch executed, waiting for response...");
    }} catch (error) {{
        console.log("JS: Top-level error:", error);
        window.search_result = {{ status: 500, error: error.toString(), message: error.message }};
        console.log("JS: Top-level error stored in window");
    }}
    '''
    
    try:
        import asyncio
        print(f"DEBUG: spotipy_handling.py - Executing search JavaScript code")
        js.eval(js_code)
        
        # Longer initial delay to let the fetch complete
        await asyncio.sleep(0.5)
        
        # Wait for the result with longer timeout
        max_attempts = 10  # Increased from 8
        for attempt in range(max_attempts):
            await asyncio.sleep(0.3)  # Increased from 0.2
            if hasattr(js.window, 'search_result'):
                result = js.window.search_result
                print(f"DEBUG: spotipy_handling.py - Search result found after {attempt + 1} attempts")
                print(f"DEBUG: spotipy_handling.py - Result value: {result}")
                
                # Check if the result is actually valid (not None)
                if result is not None:
                    print(f"DEBUG: spotipy_handling.py - Result is valid, proceeding")
                    break
                else:
                    print(f"DEBUG: spotipy_handling.py - Result is None, continuing to wait...")
                    # Check what other properties are in the window object
                    try:
                        window_props = [attr for attr in dir(js.window) if not attr.startswith('_')]
                        print(f"DEBUG: spotipy_handling.py - Window properties: {window_props[:10]}...")  # Show first 10
                    except:
                        print(f"DEBUG: spotipy_handling.py - Could not inspect window properties")
                    # Check if there are any JavaScript errors
                    try:
                        if hasattr(js.window, 'console') and hasattr(js.window.console, 'error'):
                            print(f"DEBUG: spotipy_handling.py - Checking for JS errors...")
                    except:
                        pass
                    continue
            print(f"DEBUG: spotipy_handling.py - Search attempt {attempt + 1}/{max_attempts}, no result yet")
            # Check if there are any JavaScript errors
            try:
                if hasattr(js.window, 'console') and hasattr(js.window.console, 'error'):
                    print(f"DEBUG: spotipy_handling.py - Checking for JS errors...")
            except:
                pass
        
        if hasattr(js.window, 'search_result'):
            result = js.window.search_result
            print(f"DEBUG: spotipy_handling.py - Search result from window: {result}")
            print(f"DEBUG: spotipy_handling.py - Search result type: {type(result)}")
            if result is not None:
                print(f"DEBUG: spotipy_handling.py - Search result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            else:
                print(f"DEBUG: spotipy_handling.py - Search result is None")
                return None
            
            # Handle different result types
            if isinstance(result, dict):
                status = result.get('status')
                print(f"DEBUG: spotipy_handling.py - Search response status: {status}")
                print(f"DEBUG: spotipy_handling.py - Search result keys: {list(result.keys())}")
                
                if status == 200:
                    try:
                        text = result.get('text', '{}')
                        print(f"DEBUG: spotipy_handling.py - Response text length: {len(text)}")
                        print(f"DEBUG: spotipy_handling.py - Response text preview: {text[:200]}")
                        parsed_data = json.loads(text)
                        print(f"DEBUG: spotipy_handling.py - Successfully parsed search data")
                        return parsed_data
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: spotipy_handling.py - Failed to parse search result JSON: {e}")
                        return None
                else:
                    print(f"DEBUG: spotipy_handling.py - Search failed with status: {status}")
                    error_message = result.get('message', 'No error message')
                    print(f"DEBUG: spotipy_handling.py - Error message: {error_message}")
                    
                    # Try to parse the error response to see what went wrong
                    try:
                        text = result.get('text', '{}')
                        if text:
                            error_data = json.loads(text)
                            print(f"DEBUG: spotipy_handling.py - Error response: {error_data}")
                            # If the error response contains valid search data, return it anyway
                            if 'albums' in error_data:
                                print(f"DEBUG: spotipy_handling.py - Found albums in error response, returning anyway")
                                return error_data
                    except Exception as e:
                        print(f"DEBUG: spotipy_handling.py - Could not parse error response: {e}")
                    return None
            elif isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                    return parsed_result
                except json.JSONDecodeError:
                    print(f"DEBUG: spotipy_handling.py - Failed to parse search result string as JSON")
                    return None
            else:
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        try:
                            parsed_data = json.loads(text)
                            return parsed_data
                        except json.JSONDecodeError:
                            print(f"DEBUG: spotipy_handling.py - Failed to parse search result object JSON")
                            return None
                    else:
                        print(f"DEBUG: spotipy_handling.py - Search failed with status: {status}")
                        return None
                except Exception as e:
                    print(f"DEBUG: spotipy_handling.py - Error accessing search result properties: {e}")
                    return None
        else:
            print(f"DEBUG: spotipy_handling.py - No search result found after {max_attempts} attempts")
            return None
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in search_album_via_backend: {e}")
        return None

# Browser-safe: pause playback via backend
async def pause_playback_via_backend():
    import js
    
    js_code = f'''
    fetch("{BACKEND_URL}/pause", {{
        method: "POST",
        credentials: "include"
    }})
    .then(response => {{
        console.log("Pause response status:", response.status);
        return response.text();
    }})
    .then(text => {{
        console.log("Pause response text:", text);
        window.pause_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        console.log("Pause error:", error);
        window.pause_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'pause_result'):
            result = js.window.pause_result
            print(f"DEBUG: spotipy_handling.py - Pause result: {result}")
            # Handle both object and string cases
            if isinstance(result, dict):
                return result.get('status', 500) == 200
            elif isinstance(result, str):
                # If it's a string, try to parse it as JSON
                try:
                    parsed_result = json.loads(result)
                    return parsed_result.get('status', 500) == 200
                except:
                    return False
            else:
                # If it's an object, try to access properties directly
                try:
                    status = getattr(result, 'status', 500)
                    return status == 200
                except:
                    return False
        else:
            print("DEBUG: spotipy_handling.py - No pause result available")
            return False
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in pause_playback_via_backend: {e}")
        return False

# Browser-safe: get devices via backend
async def get_devices_via_backend():
    import js
    import json
    
    js_code = f'''
    fetch("{BACKEND_URL}/devices", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        console.log("Devices response status:", response.status);
        return response.text();
    }})
    .then(text => {{
        console.log("Devices response text:", text);
        window.devices_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        console.log("Devices error:", error);
        window.devices_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'devices_result'):
            result = js.window.devices_result
            print(f"DEBUG: spotipy_handling.py - Devices result: {result}")
            # Handle both object and string cases
            if isinstance(result, dict):
                if result.get('status') == 200:
                    return json.loads(result.get('text', '{}'))
            elif isinstance(result, str):
                # If it's a string, try to parse it as JSON
                try:
                    parsed_result = json.loads(result)
                    return parsed_result
                except:
                    return None
            else:
                # If it's an object, try to access properties directly
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        return json.loads(text)
                except:
                    return None
        return None
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in get_devices_via_backend: {e}")
        return None

# Browser-safe: get current playback via backend
async def get_current_playback_via_backend():
    import js
    import json
    
    js_code = f'''
    fetch("{BACKEND_URL}/currently_playing", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        console.log("Currently playing response status:", response.status);
        return response.text();
    }})
    .then(text => {{
        console.log("Currently playing response text:", text);
        window.currently_playing_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        console.log("Currently playing error:", error);
        window.currently_playing_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'currently_playing_result'):
            result = js.window.currently_playing_result
            print(f"DEBUG: spotipy_handling.py - Currently playing result: {result}")
            # Handle both object and string cases
            if isinstance(result, dict):
                if result.get('status') == 200:
                    return json.loads(result.get('text', '{}'))
            elif isinstance(result, str):
                # If it's a string, try to parse it as JSON
                try:
                    parsed_result = json.loads(result)
                    return parsed_result
                except:
                    return None
            else:
                # If it's an object, try to access properties directly
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        return json.loads(text)
                except:
                    return None
        return None
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in get_current_playback_via_backend: {e}")
        return None

# Browser-safe: get album tracks via backend
async def get_album_tracks_via_backend(album_id):
    import js
    import json
    url = f"{BACKEND_URL}/album_tracks?album_id={album_id}"
    
    js_code = f'''
    fetch("{url}", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        console.log("Album tracks response status:", response.status);
        return response.text();
    }})
    .then(text => {{
        console.log("Album tracks response text:", text);
        window.album_tracks_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        console.log("Album tracks error:", error);
        window.album_tracks_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'album_tracks_result'):
            result = js.window.album_tracks_result
            print(f"DEBUG: spotipy_handling.py - Album tracks result: {result}")
            # Handle both object and string cases
            if isinstance(result, dict):
                if result.get('status') == 200:
                    return json.loads(result.get('text', '{}'))
            elif isinstance(result, str):
                # If it's a string, try to parse it as JSON
                try:
                    parsed_result = json.loads(result)
                    return parsed_result
                except:
                    return None
            else:
                # If it's an object, try to access properties directly
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        return json.loads(text)
                except:
                    return None
        return None
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in get_album_tracks_via_backend: {e}")
        return None
