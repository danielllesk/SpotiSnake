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
# Use deployed backend URL for production
BACKEND_URL = os.environ.get("SPOTISNAKE_BACKEND_URL", "https://spotisnake.onrender.com")
print(f"DEBUG: spotipy_handling.py - Using backend URL: {BACKEND_URL}")

# Test backend connectivity on startup
def test_backend_connectivity():
    """Test if backend is accessible"""
    try:
        js_code = f'''
        console.log("Testing backend connectivity to: {BACKEND_URL}");
        fetch("{BACKEND_URL}/ping", {{
            method: "GET",
            credentials: "include"
        }})
        .then(response => {{
            console.log("Backend connectivity test - Status:", response.status);
            return response.text();
        }})
        .then(text => {{
            console.log("Backend connectivity test - Response:", text);
        }})
        .catch(error => {{
            console.log("Backend connectivity test - Error:", error);
        }});
        '''
        js.eval(js_code)
        print("DEBUG: spotipy_handling.py - Backend connectivity test initiated")
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

def check_authenticated():
    print("DEBUG: spotipy_handling.py - check_authenticated called (JS callback version)")
    url = f"{BACKEND_URL}/me"
    js_code = f'''
    console.log("JS: Starting fetch for auth check");
    fetch("{url}", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        console.log("JS: /me status:", response.status);
        const ct = response.headers.get("Content-Type") || "";
        console.log("JS: /me Content-Type:", ct);
        if (response.ok && ct.includes("application/json")) {{
            return response.text();
        }} else {{
            console.log("JS: Auth check failed - not authenticated yet");
            window.handle_auth_result(JSON.stringify({{"error": "Not authenticated"}}));
            return;
        }}
    }})
    .then(text => {{
        if (text) {{
            console.log("JS: Fetched text:", text);
            window.handle_auth_result(text);
        }}
    }})
    .catch(error => {{
        console.log("JS: Auth check error:", error);
        window.handle_auth_result(JSON.stringify({{"error": "Network error"}}));
    }});
    '''
    js.eval(js_code)
    return js.auth_success

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

def download_and_resize_album_cover(url, target_width, target_height):
    print(f"DEBUG: spotipy_handling.py - download_and_resize_album_cover called with url: {url}")
    # In browser, album covers must be pre-bundled or loaded from local assets
    print("DEBUG: spotipy_handling.py - download_and_resize_album_cover should use local assets in browser build")
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
            return result.get('status', 500) == 200
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

def play_random_track_from_album(album_id, song_info_updater_callback):
    print(f"DEBUG: spotipy_handling.py - play_random_track_from_album called with album_id: {album_id}")
    
    # Use synchronous approach with js.eval for getting album tracks
    import js
    import json
    import random
    
    js_code = f'''
    fetch("{BACKEND_URL}/album_tracks?album_id={album_id}", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        console.log("Album tracks sync response status:", response.status);
        return response.text();
    }})
    .then(text => {{
        console.log("Album tracks sync response text:", text);
        window.album_tracks_sync_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        console.log("Album tracks sync error:", error);
        window.album_tracks_sync_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import time
        time.sleep(0.1)  # Wait for async operation
        
        tracks_data = None
        if hasattr(js.window, 'album_tracks_sync_result'):
            result = js.window.album_tracks_sync_result
            if result.get('status') == 200:
                tracks_data = json.loads(result.get('text', '{}'))
        
        tracks = tracks_data.get('items', []) if tracks_data else []
        if not tracks:
            print("DEBUG: spotipy_handling.py - No tracks found in album")
            song_info_updater_callback("No Tracks In Album", "N/A", False)
            return
        
        track = random.choice(tracks)
        chosen_track_uri = track['uri']
        track_name = track.get('name', 'Unknown Track')
        track_artist = track.get('artists', [{}])[0].get('name', 'Unknown Artist')
        position_ms = random.randint(0, max(0, track.get('duration_ms', 0) - 30000))
        is_easter_egg_track_selected = (chosen_track_uri == EASTER_EGG_TRACK_URI)
        print(f"DEBUG: spotipy_handling.py - Selected track: {track_name} by {track_artist}")
        
        # Use synchronous approach for playing track
        played_successfully = play_track_sync(chosen_track_uri, position_ms)
        if played_successfully:
            print(f"DEBUG: spotipy_handling.py - Track started successfully")
            song_info_updater_callback(track_name, track_artist, is_easter_egg_track_selected)
        else:
            print(f"DEBUG: spotipy_handling.py - Track failed to start")
            song_info_updater_callback(track_name, f"(Failed: {track_artist})", False)
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in play_random_track_from_album: {e}")
        song_info_updater_callback("Error Loading Album", "N/A", False)

async def safe_pause_playback():
    print("DEBUG: spotipy_handling.py - safe_pause_playback called")
    try:
        result = await pause_playback_via_backend()
        print(f"DEBUG: spotipy_handling.py - safe_pause_playback result: {result}")
        return result
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Exception in safe_pause_playback: {e}")
        return False

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

    def draw_search_results_local():
        if search_results:
            pygame.draw.rect(screen, WHITE, results_area)
            y_offset = results_area.y + 10
            for album in search_results:
                result_rect = pygame.Rect(results_area.x + 5, y_offset, results_area.width - 10, 70)
                if result_rect.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(screen, LIGHT_BLUE, result_rect)
                else:
                    pygame.draw.rect(screen, WHITE, result_rect)
                pygame.draw.rect(screen, DARK_BLUE, result_rect, 1)
                if album['image_url'] and album['uri'] not in album_covers:
                    try:
                        album_covers[album['uri']] = download_and_resize_album_cover(album['image_url'], 50, 50)
                    except Exception:
                        album_covers[album['uri']] = None
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
                            print(f"DEBUG: spotipy_handling.py - album search ENTER pressed, text: {text}")
                            # Use backend search
                            search_results = []
                            backend_results = search_album(text)
                            if backend_results and 'albums' in backend_results and 'items' in backend_results['albums']:
                                for album in backend_results['albums']['items']:
                                    search_results.append({
                                        'name': album.get('name', 'Unknown Album'),
                                        'uri': album.get('uri', ''),
                                        'image_url': album.get('images', [{}])[0].get('url', None) if album.get('images') else None,
                                        'artist': album.get('artists', [{}])[0].get('name', 'Unknown Artist') if album.get('artists') else 'Unknown Artist'
                                    })
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
        console.log("Play response status:", response.status);
        return response.text();
    }})
    .then(text => {{
        console.log("Play response text:", text);
        window.play_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        console.log("Play error:", error);
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
            print(f"DEBUG: spotipy_handling.py - Play result: {result}")
            return result.get('status', 500) == 200
        else:
            print("DEBUG: spotipy_handling.py - No play result available")
            return False
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in play_track_via_backend: {e}")
        return False

# Browser-safe: search album via backend
async def search_album_via_backend(query):
    import js
    import json
    
    js_code = f'''
    fetch("{BACKEND_URL}/search?q={query}", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        console.log("Search response status:", response.status);
        return response.text();
    }})
    .then(text => {{
        console.log("Search response text:", text);
        window.search_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        console.log("Search error:", error);
        window.search_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'search_result'):
            result = js.window.search_result
            print(f"DEBUG: spotipy_handling.py - Search result: {result}")
            if result.get('status') == 200:
                return json.loads(result.get('text', '{}'))
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
            return result.get('status', 500) == 200
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
            if result.get('status') == 200:
                return json.loads(result.get('text', '{}'))
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
            if result.get('status') == 200:
                return json.loads(result.get('text', '{}'))
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
            if result.get('status') == 200:
                return json.loads(result.get('text', '{}'))
        return None
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in get_album_tracks_via_backend: {e}")
        return None
