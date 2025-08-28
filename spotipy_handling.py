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
        fetch("{BACKEND_URL}/ping", {{
            method: "GET"
        }})
        .then(response => {{
            return response.text();
        }})
        .then(text => {{
            window.backend_test_result = {{ status: 200, text: text }};
        }})
        .catch(error => {{
            window.backend_test_result = {{ status: 500, error: error.toString() }};
        }});
        '''
        js.eval(js_code)
        
        import time
        time.sleep(0.5)
        
        if hasattr(js.window, 'backend_test_result'):
            result = js.window.backend_test_result
        else:
            pass
            
    except Exception as e:
        pass

test_backend_connectivity()
clock = pygame.time.Clock()
pygame.init()

USER_ABORT_GAME_FROM_SEARCH = "USER_ABORT_GAME_FROM_SEARCH"

is_logging_in = False

LOCAL_TESTING_MODE = False  

device_id_cache = None  # Cache for Spotify device ID

def clear_device_id_cache():
    global device_id_cache
    device_id_cache = None

def backend_login():
    """Handles Spotify login through the backend server."""
    global is_logging_in
    
    if is_logging_in:
        return
    
    is_logging_in = True
    login_url = f"{BACKEND_URL}/login"

    # Check if we're in a browser environment
    if is_pyodide():
        try:
            import js  
            if hasattr(js, 'window'):
                js.window.open(login_url, "_blank")
            else:
                is_logging_in = False
        except Exception as e:
            is_logging_in = False
    else:
        try:
            import webbrowser
            webbrowser.open(login_url)
        except Exception as e:
            pass
    is_logging_in = False

def is_pyodide():
    """Check if we're running in a browser environment (pygbag/pyodide)"""
    try:
        import js
        has_window = hasattr(js, 'window')
        has_fetch = hasattr(js, 'fetch')
        has_eval = hasattr(js, 'eval')
        is_browser = has_window and has_fetch and has_eval
        
        return is_browser
    except ImportError:
        return False
    except AttributeError:
        return False

import types

def await_js_promise(promise):
    try:
        return promise
    except Exception as e:
        return promise

def handle_auth_result(result_json):
    import json
    try:
        data = json.loads(result_json)
    except json.JSONDecodeError:
        data = {}
    global is_logging_in
    if data.get('id'):
        is_logging_in = False
        js.auth_success = True
    else:
        js.auth_success = False

try:
    if hasattr(js, 'window'):
        js.window.handle_auth_result = handle_auth_result  # Attach to window explicitly
        js.auth_success = False
    else:
        js.auth_success = False
except Exception as e:
    pass

async def check_authenticated():
    if not is_pyodide():
        return False
    
    import js
    import json
    
    js_code = f'''
    fetch("{BACKEND_URL}/me", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        return response.text().then(text => {{
            return {{ status: response.status, text: text }};
        }});
    }})
    .then(result => {{
        window.auth_check_result = result;
    }})
    .catch(error => {{
        window.auth_check_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.3)
        
        if hasattr(js.window, 'auth_check_result'):
            result = js.window.auth_check_result
            
            try:
                if hasattr(result, 'status'):
                    status = result.status
                    if status == 200:
                        # Check if the response actually contains user data, not an error
                        try:
                            if hasattr(result, 'text'):
                                response_text = result.text
                                if '"error"' in response_text.lower():
                                    return False
                                if '"id"' in response_text or '"display_name"' in response_text:
                                    return True
                                else:
                                    return False
                        except Exception as e:
                            return False
                    else:
                        try:
                            if hasattr(result, 'text'):
                                error_text = result.text
                        except:
                            pass
                        return False
                elif isinstance(result, dict):
                    status = result.get('status', 500)
                    if status == 200:
                        response_text = result.get('text', '')
                        if '"error"' in response_text.lower():
                            return False
                        if '"id"' in response_text or '"display_name"' in response_text:
                            return True
                        else:
                            return False
                    else:
                        return False
                else:
                    try:
                        status = getattr(result, 'status', 500)
                        if status == 200:
                            return True
                        else:
                            return False
                    except Exception as e:
                        return False
            except Exception as e:
                return False
        else:
            return False
    except Exception as e:
        return False

async def download_and_resize_album_cover_async(url, target_width, target_height):
    """Download and resize album cover asynchronously using backend proxy to avoid CORS"""
    
    if not url:
        return create_fallback_album_cover(target_width, target_height)
    
    # Try to load the actual image using the backend proxy
    try:
        import js
        import base64
        if is_pyodide():
            pass
        else:
            raise ImportError("Desktop environment - use Python fallback")
    except ImportError:
        try:
            import requests
            response = requests.post(f"{BACKEND_URL}/download_album_cover", 
                                   json={"image_url": url},
                                   timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 200 and data.get('data'):
                    base64_data = data['data']
                    try:
                        image_data = base64.b64decode(base64_data)
                        import io
                        image_stream = io.BytesIO(image_data)
                        image = pygame.image.load(image_stream)
                        resized_image = pygame.transform.scale(image, (target_width, target_height))
                        return resized_image
                    except Exception as e:
                        return create_visual_album_cover(url, target_width, target_height)
                else:
                    return create_visual_album_cover(url, target_width, target_height)
            else:
                return create_visual_album_cover(url, target_width, target_height)
        except ImportError:
            return create_visual_album_cover(url, target_width, target_height)
        except Exception as e:
            return create_visual_album_cover(url, target_width, target_height)
    
    test_js = '''
    window.js_test_result = "JavaScript is working";
    '''
    
    try:
        js.eval(test_js)
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'js_test_result'):
            pass
        else:
            raise ImportError("JavaScript not working")
    except Exception as e:
        raise ImportError("JavaScript not working")
    
    js_code = f'''
    (async () => {{
        try {{
            const response = await fetch("{BACKEND_URL}/download_album_cover", {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json"
                }},
                credentials: "include",
                body: JSON.stringify({{"image_url": "{url}"}})
            }});
            
            if (!response.ok) {{
                throw new Error(`HTTP error! status: ${{response.status}}`);
            }}
            
            const data = await response.json();
            window.image_download_result = data;
            window.image_download_complete = true;
            
        }} catch (error) {{
            window.image_download_result = {{ status: 500, error: error.toString() }};
            window.image_download_complete = true;
        }}
    }})();
    '''
    
    try:
        js.eval(js_code)
        
        # Wait for the async JavaScript to complete
        for i in range(10):  # Wait up to 1 second (10 * 100ms) - reduced further
            await asyncio.sleep(0.1)  # Wait 100ms each time
            
            # Check if the download is complete
            if hasattr(js.window, 'image_download_complete') and js.window.image_download_complete:
                break
                
            if hasattr(js.window, 'image_download_result') and js.window.image_download_result is not None:
                break
        
        result = None
        if hasattr(js.window, 'image_download_result'):
            js_result = js.window.image_download_result
            
            try:
                result = None
                
                if hasattr(js_result, 'status'):
                    try:
                        status = js_result.status
                        data = getattr(js_result, 'data', None)
                        error = getattr(js_result, 'error', None)
                        result = {
                            'status': status,
                            'data': data,
                            'error': error
                        }
                    except Exception as e:
                        pass
                
                if result is None:
                    try:
                        js_code = '''
                        try {
                            const jsonStr = JSON.stringify(window.image_download_result);
                            window.converted_result = jsonStr;
                        } catch(e) {
                            window.converted_result = null;
                        }
                        '''
                        js.eval(js_code)
                        await asyncio.sleep(0.1)
                        
                        if hasattr(js.window, 'converted_result') and js.window.converted_result:
                            import json
                            result = json.loads(js.window.converted_result)
                    except Exception as e:
                        pass
                
                if result is None and hasattr(js_result, 'to_py'):
                    try:
                        result = js_result.to_py()
                    except Exception as e:
                        pass
                
                if result is None:
                    try:
                        result_str = str(js_result)
                        if 'data' in result_str and 'status' in result_str:
                            result = None
                    except Exception as e:
                        pass
                    
            except Exception as e:
                result = None
            
            try:
                js.window.image_download_result = None
                js.window.image_download_complete = False
            except Exception as e:
                pass
        else:
            return create_visual_album_cover(url, target_width, target_height)
            
        if isinstance(result, dict):
            status = result.get('status', 500)
            if status == 200:
                base64_data = result.get('data')
                if base64_data:
                    try:
                        resized_image = await base64_to_pygame_surface_pygbag(base64_data, target_width, target_height)
                        if resized_image:
                            return resized_image
                        else:
                            return create_visual_album_cover(url, target_width, target_height)
                    except Exception as e:
                        return create_visual_album_cover(url, target_width, target_height)
                else:
                    return create_visual_album_cover(url, target_width, target_height)
            else:
                return create_visual_album_cover(url, target_width, target_height)
        elif hasattr(result, 'status'):
            status = result.status
            if status == 200:
                try:
                    if hasattr(result, 'data'):
                        base64_data = result.data
                        if base64_data:
                            surface = base64_to_pygame_surface(base64_data, target_width, target_height)
                            if surface:
                                return surface
                            else:
                                return create_visual_album_cover(url, target_width, target_height)
                        else:
                            return create_visual_album_cover(url, target_width, target_height)
                    else:
                        return create_visual_album_cover(url, target_width, target_height)
                except Exception as e:
                    return create_visual_album_cover(url, target_width, target_height)
            else:
                return create_visual_album_cover(url, target_width, target_height)
        elif result is None:
            return create_visual_album_cover(url, target_width, target_height)
        else:
            return create_visual_album_cover(url, target_width, target_height)
    except Exception as e:
        return create_visual_album_cover(url, target_width, target_height)

def download_and_resize_album_cover(url, target_width, target_height):
    if not url:
        return create_fallback_album_cover(target_width, target_height)
    
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return create_fallback_album_cover(target_width, target_height)
        else:
            return loop.run_until_complete(download_and_resize_album_cover_async(url, target_width, target_height))
    except Exception as e:
        return create_fallback_album_cover(target_width, target_height)

def create_fallback_album_cover(target_width, target_height):
    """Create a fallback album cover when image download fails"""
    try:
        surface = pygame.Surface((target_width, target_height))
        
        import random
        import time
        
        random.seed(int(time.time() * 1000) % 1000)
        
        for y in range(target_height):
            for x in range(target_width):
                progress_x = x / target_width
                progress_y = y / target_height
                
                r = int(128 + 127 * (progress_x + random.random() * 0.3))
                g = int(128 + 127 * (progress_y + random.random() * 0.3))
                b = int(128 + 127 * ((progress_x + progress_y) / 2 + random.random() * 0.3))
                
                r = max(50, min(255, r))
                g = max(50, min(255, g))
                b = max(50, min(255, b))
                
                surface.set_at((x, y), (r, g, b))
        
        border_color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        pygame.draw.rect(surface, border_color, surface.get_rect(), 2)
        
        try:
            font = pygame.font.SysFont("Arial", min(target_width, target_height) // 8)
            text = font.render("ALBUM", True, (255, 255, 255))
            text_rect = text.get_rect(center=(target_width // 2, target_height // 2))
            surface.blit(text, text_rect)
        except Exception as e:
            pass
        
        return surface
    except Exception as e:
        return None

def create_visual_album_cover(image_url, target_width, target_height):
    """Create a visual album cover that works in browser environments"""
    try:
        import hashlib
        hash_value = hashlib.md5(image_url.encode()).hexdigest()
        
        surface = pygame.Surface((target_width, target_height))
        
        r_base = int(hash_value[0:2], 16)
        g_base = int(hash_value[2:4], 16)
        b_base = int(hash_value[4:6], 16)
        
        if r_base == 0 and g_base == 0 and b_base == 0:
            r_base = 128
            g_base = 64
            b_base = 192
        
        for y in range(target_height):
            for x in range(target_width):
                x_ratio = x / target_width
                y_ratio = y / target_height
                
                r = int(r_base * (0.5 + 0.5 * x_ratio))
                g = int(g_base * (0.5 + 0.5 * y_ratio))
                b = int(b_base * (0.5 + 0.5 * (x_ratio + y_ratio) / 2))
                
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                
                surface.set_at((x, y), (r, g, b))
        
        pygame.draw.rect(surface, (255, 255, 255), surface.get_rect(), 1)
        
        return surface
    except Exception as e:
        return create_fallback_album_cover(target_width, target_height)

def create_visual_album_cover_from_data(image_data, target_width, target_height):
    """Create a visual album cover from image data when pygame.image.load fails"""
    try:
        import hashlib
        hash_value = hashlib.md5(image_data).hexdigest()
        
        surface = pygame.Surface((target_width, target_height))
        
        r_base = int(hash_value[0:2], 16)
        g_base = int(hash_value[2:4], 16)
        b_base = int(hash_value[4:6], 16)
        
        r_base = max(r_base, 50)
        g_base = max(g_base, 50)
        b_base = max(b_base, 50)
        
        for y in range(target_height):
            for x in range(target_width):
                progress_x = x / target_width
                progress_y = y / target_height
                
                r = int((r_base + progress_x * 100 + progress_y * 50) % 256)
                g = int((g_base + progress_y * 100 + progress_x * 50) % 256)
                b = int((b_base + (progress_x + progress_y) * 75) % 256)
                
                r = max(r, 30)
                g = max(g, 30)
                b = max(b, 30)
                
                surface.set_at((x, y), (r, g, b))
        
        border_color = (
            int(hash_value[6:8], 16),
            int(hash_value[8:10], 16),
            int(hash_value[10:12], 16)
        )
        pygame.draw.rect(surface, border_color, surface.get_rect(), 2)
        
        return surface
    except Exception as e:
        return create_fallback_album_cover(target_width, target_height)

def create_album_cover_like_surface(image_data, target_width, target_height):
    """Create a surface that looks more like an actual album cover"""
    try:
        import hashlib
        hash_value = hashlib.md5(image_data).hexdigest()
        
        surface = pygame.Surface((target_width, target_height))
        
        colors = []
        for i in range(0, len(hash_value), 6):
            if i + 5 < len(hash_value):
                r = int(hash_value[i:i+2], 16)
                g = int(hash_value[i+2:i+4], 16)
                b = int(hash_value[i+4:i+6], 16)
                colors.append((r, g, b))
        
        if len(colors) < 2:
            colors.extend([(128, 128, 128), (64, 64, 64)])
        
        for y in range(target_height):
            for x in range(target_width):
                progress_x = x / target_width
                progress_y = y / target_height
                
                color1 = colors[0]
                color2 = colors[1] if len(colors) > 1 else colors[0]
                
                gradient_progress = (progress_x + progress_y) / 2
                r = int(color1[0] * (1 - gradient_progress) + color2[0] * gradient_progress)
                g = int(color1[1] * (1 - gradient_progress) + color2[1] * gradient_progress)
                b = int(color1[2] * (1 - gradient_progress) + color2[2] * gradient_progress)
                
                texture_index = (x * 7 + y * 11) % len(hash_value)
                texture_char = hash_value[texture_index]
                texture_value = int(texture_char, 16)
                
                texture_offset = (texture_value - 8) * 3
                r = max(0, min(255, r + texture_offset))
                g = max(0, min(255, g + texture_offset))
                b = max(0, min(255, b + texture_offset))
                
                if len(colors) > 2:
                    center_x, center_y = target_width // 2, target_height // 2
                    distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    
                    if distance < target_width // 4:
                        color3 = colors[2]
                        blend_factor = 0.3
                        r = int(r * (1 - blend_factor) + color3[0] * blend_factor)
                        g = int(g * (1 - blend_factor) + color3[1] * blend_factor)
                        b = int(b * (1 - blend_factor) + color3[2] * blend_factor)
                
                surface.set_at((x, y), (r, g, b))
        
        pygame.draw.rect(surface, (255, 255, 255), surface.get_rect(), 2)
        pygame.draw.rect(surface, (200, 200, 200), surface.get_rect(), 1)
        
        shadow_surface = pygame.Surface((target_width + 4, target_height + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surface, (0, 0, 0, 80), (4, 4, target_width, target_height))
        surface.blit(shadow_surface, (-2, -2))
        
        return surface
    except Exception as e:
        return create_visual_album_cover_from_data(image_data, target_width, target_height)

def get_spotify_device():
    global device_id_cache
    if device_id_cache is not None:
        return device_id_cache
    
    import js
    js_code = f'''
    fetch("{BACKEND_URL}/devices", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        return response.text();
    }})
    .then(text => {{
        window.devices_sync_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        window.devices_sync_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import time
        time.sleep(0.1)
        
        if hasattr(js.window, 'devices_sync_result'):
            result = js.window.devices_sync_result
            if isinstance(result, dict):
                if result.get('status') == 200:
                    import json
                    devices = json.loads(result.get('text', '{}'))
                    if devices and devices.get('devices'):
                        active_device = next((d for d in devices['devices'] if d.get('is_active')), None)
                        if active_device:
                            device_id_cache = active_device['id']
                            return device_id_cache
                        device_id_cache = devices['devices'][0]['id']
                        return device_id_cache
            elif isinstance(result, str):
                try:
                    import json
                    parsed_result = json.loads(result)
                    if parsed_result and parsed_result.get('devices'):
                        active_device = next((d for d in parsed_result['devices'] if d.get('is_active')), None)
                        if active_device:
                            device_id_cache = active_device['id']
                            return device_id_cache
                        device_id_cache = parsed_result['devices'][0]['id']
                        return device_id_cache
                except:
                    pass
            else:
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        import json
                        devices = json.loads(text)
                        if devices and devices.get('devices'):
                            active_device = next((d for d in devices['devices'] if d.get('is_active')), None)
                            if active_device:
                                device_id_cache = active_device['id']
                                return device_id_cache
                            device_id_cache = devices['devices'][0]['id']
                            return device_id_cache
                except:
                    pass
    except Exception as e:
        pass
    
    return None

def play_track_sync(track_uri, position_ms):
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
        return response.text();
    }})
    .then(text => {{
        window.play_sync_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        window.play_sync_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import time
        time.sleep(0.1)
        
        if hasattr(js.window, 'play_sync_result'):
            result = js.window.play_sync_result
            if isinstance(result, dict):
                return result.get('status', 500) == 200
            elif isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                    return parsed_result.get('status', 500) == 200
                except:
                    return False
            else:
                try:
                    status = getattr(result, 'status', 500)
                    return status == 200
                except:
                    return False
        else:
            return False
    except Exception as e:
        return False

def play_uri_with_details(track_uri, position_ms=0):
    played_successfully = play_track_sync(track_uri, position_ms)
    return played_successfully, "Unknown Track", "Unknown Artist"

async def play_random_track_from_album(album_id, song_info_updater_callback):
    import js
    import json
    import random
    import time
    import asyncio
    
    cache_key = f"album_tracks_{album_id}"
    current_time = time.time()
    
    if hasattr(js.window, cache_key):
        cached_data_json = getattr(js.window, cache_key)
        cached_data = None
        try:
            if cached_data_json is None:
                if hasattr(js.window, cache_key):
                    delattr(js.window, cache_key)
                cached_data = None
            elif isinstance(cached_data_json, str):
                cached_data = json.loads(cached_data_json)
            else:
                if hasattr(js.window, cache_key):
                    delattr(js.window, cache_key)
                cached_data = None
        except (json.JSONDecodeError, TypeError) as e:
            if hasattr(js.window, cache_key):
                delattr(js.window, cache_key)
            cached_data = None
        
        if cached_data and isinstance(cached_data, dict) and 'tracks' in cached_data and 'timestamp' in cached_data:
            if current_time - cached_data['timestamp'] < 30:
                tracks = cached_data['tracks']
                if tracks:
                    track = random.choice(tracks)
                    track_name = track.get('name', 'Unknown Track')
                    artist_name = track.get('artists', [{}])[0].get('name', 'Unknown Artist') if track.get('artists') else 'Unknown Artist'
                    
                    track_uri = track.get('uri', '')
                    if track_uri:
                        duration_ms = track.get('duration_ms', 0)
                        max_position = max(0, duration_ms - 30000)
                        position_ms = random.randint(0, max_position)
                        await play_track_via_backend(track_uri, position_ms)
                        song_info_updater_callback(track_name, artist_name, False)
                        return
                    else:
                        pass
                else:
                    pass
            else:
                pass
        else:
            pass
    
    if hasattr(js.window, 'album_tracks_sync_result'):
        delattr(js.window, 'album_tracks_sync_result')
    
    if album_id.startswith('spotify:album:'):
        album_id = album_id.replace('spotify:album:', '')
    
    try:
        auth_result = await check_authenticated()
        if not auth_result:
            song_info_updater_callback("Authentication Required", "Please login", False)
            return
    except Exception as e:
        pass
    
    try:
        test_js_code = f'''
        fetch("{BACKEND_URL}/ping", {{
            method: "GET",
            credentials: "include"
        }})
        .then(response => {{
            return response.text();
        }})
        .then(text => {{
            window.ping_result = {{ status: 200, text: text }};
            
            return fetch("{BACKEND_URL}/test_session", {{
                method: "GET",
                credentials: "include"
            }});
        }})
        .then(response => {{
            return response.text();
        }})
        .then(text => {{
            window.session_result = {{ status: 200, text: text }};
        }})
        .catch(error => {{
            window.ping_result = {{ status: 500, error: error.toString() }};
        }});
        '''
        js.eval(test_js_code)
        await asyncio.sleep(0.3)
        
        if hasattr(js.window, 'ping_result'):
            ping_result = js.window.ping_result
        
        if hasattr(js.window, 'session_result'):
            session_result = js.window.session_result
            
            if isinstance(session_result, dict):
                session_text = session_result.get('text', 'No text')
                try:
                    session_data = json.loads(session_text)
                    has_token = session_data.get('has_token', False)
                except json.JSONDecodeError:
                    pass
            else:
                session_text = getattr(session_result, 'text', 'No text')
                has_token = session_text != 'No text'
        
        if not has_token:
            song_info_updater_callback("Authentication Required", "Please login", False)
            return
    except Exception as e:
        pass
    
    if not hasattr(js.window, 'first_song_played'):
        try:
            album_uri = f"spotify:album:{album_id}"
            play_result = await play_track_via_backend(album_uri, 0)
            if play_result:
                song_info_updater_callback("Playing Album", "Random Track", False)
                setattr(js.window, 'first_song_played', True)
                return
            else:
                pass
        except Exception as e:
            pass
    
    setattr(js.window, 'first_song_played', True)
    
    js_code = f'''
    console.log("JS: ===== ALBUM TRACKS FETCH START =====");
    console.log("JS: Fetching album tracks for album_id:", "{album_id}");
    console.log("JS: Backend URL:", "{BACKEND_URL}");
    console.log("JS: Full URL:", "{BACKEND_URL}/album_tracks?album_id={album_id}");
    
    window.album_tracks_sync_result = null;
    
    console.log("JS: Current cookies:", document.cookie);
    
    fetch("{BACKEND_URL}/album_tracks?album_id={album_id}", {{
        method: "GET",
        credentials: "include",
        cache: "no-cache",
        headers: {{
            "Accept": "application/json",
            "Content-Type": "application/json"
        }}
    }})
    .then(response => {{
        console.log("JS: Album tracks response status:", response.status);
        console.log("JS: Album tracks response ok:", response.ok);
        console.log("JS: Album tracks response headers:", response.headers);
        
        if (!response.ok) {{
            console.log("JS: Response not ok, getting error text");
            return response.text().then(text => {{
                console.log("JS: Error response text:", text);
                window.album_tracks_sync_result = {{ status: response.status, text: text }};
                throw new Error("Response not ok");
            }});
        }}
        
        return response.text();
    }})
    .then(text => {{
        console.log("JS: Album tracks response text length:", text.length);
        console.log("JS: Album tracks response text preview:", text.substring(0, 200));
        
        if (text.trim().startsWith('{{')) {{
            try {{
                const data = JSON.parse(text);
                console.log("JS: Parsed JSON status:", data.status || 'no status');
                console.log("JS: Parsed JSON keys:", Object.keys(data));
                window.album_tracks_sync_result = {{ status: data.status || 200, text: text }};
            }} catch(e) {{
                console.log("JS: JSON parse error:", e);
                window.album_tracks_sync_result = {{ status: 500, text: text }};
            }}
        }} else {{
            console.log("JS: Response doesn't look like JSON");
            window.album_tracks_sync_result = {{ status: 500, text: text }};
        }}
        
        console.log("JS: Result stored in window:", window.album_tracks_sync_result);
    }})
    .catch(error => {{
        console.log("JS: Album tracks fetch error:", error);
        console.log("JS: Error message:", error.message);
        
        if (!window.album_tracks_sync_result) {{
        window.album_tracks_sync_result = {{ status: 500, error: error.toString() }};
        }}
        
        console.log("JS: Final result in window:", window.album_tracks_sync_result);
    }});
    '''
    
    try:
        js.eval(js_code)
        print(f"DEBUG: spotipy_handling.py - JavaScript code executed, waiting for result...")
        await asyncio.sleep(0.5)
        
        if hasattr(js.window, 'album_tracks_sync_result'):
            print(f"DEBUG: spotipy_handling.py - Result found after 0.5s")
        else:
            print(f"DEBUG: spotipy_handling.py - No result after 0.5s, waiting more...")
            await asyncio.sleep(0.3)
        
        tracks_data = None
        if hasattr(js.window, 'album_tracks_sync_result'):
            result = js.window.album_tracks_sync_result
            print(f"DEBUG: spotipy_handling.py - Album tracks result type: {type(result)}")
            print(f"DEBUG: spotipy_handling.py - Album tracks result: {result}")
            
            if isinstance(result, dict):
                if result.get('status') == 200:
                    try:
                        tracks_data = json.loads(result.get('text', '{}'))
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: spotipy_handling.py - JSON decode error: {e}")
                else:
                    error_status = result.get('status')
                    error_text = result.get('text', 'No error text')
                    error_error = result.get('error', 'No error field')
                    print(f"DEBUG: spotipy_handling.py - Album tracks failed with status: {error_status}")
                    print(f"DEBUG: spotipy_handling.py - Error text: {error_text}")
                    print(f"DEBUG: spotipy_handling.py - Error field: {error_error}")
                    print(f"DEBUG: spotipy_handling.py - Full error response: {result}")
                    print(f"DEBUG: spotipy_handling.py - Result type: {type(result)}")
                    print(f"DEBUG: spotipy_handling.py - Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                
                if error_text and error_text.strip().startswith('{'):
                    try:
                        error_data = json.loads(error_text)
                        print(f"DEBUG: spotipy_handling.py - Parsed error data: {error_data}")
                        if 'msg' in error_data:
                            print(f"DEBUG: spotipy_handling.py - Spotify error message: {error_data['msg']}")
                        if 'status' in error_data:
                            print(f"DEBUG: spotipy_handling.py - Spotify API status: {error_data['status']}")
                    except json.JSONDecodeError:
                        print(f"DEBUG: spotipy_handling.py - Could not parse error text as JSON")
                else:
                    print(f"DEBUG: spotipy_handling.py - Error text is not JSON: '{error_text[:200]}...'")
                    
                if not isinstance(result, dict):
                    try:
                        direct_status = getattr(result, 'status', 'No direct status')
                        direct_text = getattr(result, 'text', 'No direct text')
                        direct_error = getattr(result, 'error', 'No direct error')
                        print(f"DEBUG: spotipy_handling.py - Direct status: {direct_status}")
                        print(f"DEBUG: spotipy_handling.py - Direct text: {direct_text}")
                        print(f"DEBUG: spotipy_handling.py - Direct error: {direct_error}")
                    except Exception as e:
                        print(f"DEBUG: spotipy_handling.py - Could not access direct properties: {e}")
            elif isinstance(result, str):
                try:
                    tracks_data = json.loads(result)
                except json.JSONDecodeError as e:
                    print(f"DEBUG: spotipy_handling.py - JSON decode error from string: {e}")
            else:
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        tracks_data = json.loads(text)
                    else:
                        print(f"DEBUG: spotipy_handling.py - Album tracks failed with status: {status}")
                except Exception as e:
                    print(f"DEBUG: spotipy_handling.py - Error accessing object properties: {e}")
        else:
            print("DEBUG: spotipy_handling.py - No album tracks result available")
        
        tracks = tracks_data.get('items', []) if tracks_data else []
        print(f"DEBUG: spotipy_handling.py - Found {len(tracks)} tracks")
        
        if tracks:
            cache_data_json = json.dumps({
                'tracks': tracks,
                'timestamp': current_time
            })
            setattr(js.window, cache_key, cache_data_json)
            print(f"DEBUG: spotipy_handling.py - Cached {len(tracks)} tracks for album {album_id}")
        
        if not tracks:
            print("DEBUG: spotipy_handling.py - No tracks found on first attempt, retrying with exponential backoff...")
            for retry_attempt in range(2):
                delay = (retry_attempt + 1) * 0.1
                print(f"DEBUG: spotipy_handling.py - Retry attempt {retry_attempt + 1} in {delay} seconds...")
                await asyncio.sleep(delay)
            
            print("DEBUG: spotipy_handling.py - Retrying album tracks request...")
            try:
                if hasattr(js.window, 'album_tracks_sync_result'):
                    delattr(js.window, 'album_tracks_sync_result')
                js.eval(js_code)
                await asyncio.sleep(0.5)
                
                if hasattr(js.window, 'album_tracks_sync_result'):
                    result = js.window.album_tracks_sync_result
                    
                    if isinstance(result, dict):
                        if result.get('status') == 200:
                            try:
                                tracks_data = json.loads(result.get('text', '{}'))
                                tracks = tracks_data.get('items', []) if tracks_data else []
                                print(f"DEBUG: spotipy_handling.py - Retry found {len(tracks)} tracks")
                                
                                if tracks:
                                    cache_data_json = json.dumps({
                                        'tracks': tracks,
                                        'timestamp': current_time
                                    })
                                    setattr(js.window, cache_key, cache_data_json)
                                    print(f"DEBUG: spotipy_handling.py - Cached {len(tracks)} tracks from retry for album {album_id}")
                            except json.JSONDecodeError as e:
                                print(f"DEBUG: spotipy_handling.py - Retry JSON decode error: {e}")
                        else:
                            retry_status = result.get('status')
                            retry_text = result.get('text', 'No error text')
                            retry_error = result.get('error', 'No error field')
                            print(f"DEBUG: spotipy_handling.py - Retry failed with status: {retry_status}")
                            print(f"DEBUG: spotipy_handling.py - Retry error text: {retry_text}")
                            print(f"DEBUG: spotipy_handling.py - Retry error field: {retry_error}")
            except Exception as e:
                print(f"DEBUG: spotipy_handling.py - Retry attempt failed: {e}")
            
            if not tracks:
                print("DEBUG: spotipy_handling.py - No tracks found after retry, trying to play album directly")
                if hasattr(js.window, cache_key):
                    try:
                        cached_data_json = getattr(js.window, cache_key)
                        if cached_data_json is None:
                            print(f"DEBUG: spotipy_handling.py - Fallback cache is None, skipping")
                            pass
                        elif isinstance(cached_data_json, str):
                            cached_data = json.loads(cached_data_json)
                            if isinstance(cached_data, dict) and 'tracks' in cached_data:
                                tracks = cached_data['tracks']
                                print(f"DEBUG: spotipy_handling.py - Using cached tracks as fallback: {len(tracks)} tracks")
                                if tracks:
                                    track = random.choice(tracks)
                                    track_name = track.get('name', 'Unknown Track')
                                    artist_name = track.get('artists', [{}])[0].get('name', 'Unknown Artist') if track.get('artists') else 'Unknown Artist'
                                    
                                    track_uri = track.get('uri', '')
                                    if track_uri:
                                        duration_ms = track.get('duration_ms', 0)
                                        max_position = max(0, duration_ms - 30000)
                                        position_ms = random.randint(0, max_position)
                                        is_easter_egg_track_selected = (track_uri == EASTER_EGG_TRACK_URI)
                                        print(f"DEBUG: spotipy_handling.py - Playing cached fallback track: {track_name} by {artist_name} at {position_ms}ms")
                                        print(f"DEBUG: spotipy_handling.py - Track URI: {track_uri}")
                                        print(f"DEBUG: spotipy_handling.py - Easter egg URI: {EASTER_EGG_TRACK_URI}")
                                        print(f"DEBUG: spotipy_handling.py - Is easter egg track: {is_easter_egg_track_selected}")
                                        await play_track_via_backend(track_uri, position_ms)
                                        song_info_updater_callback(track_name, artist_name, is_easter_egg_track_selected)
                                        return
                    except Exception as e:
                        print(f"DEBUG: spotipy_handling.py - Failed to use cached tracks as fallback: {e}")
                
                try:
                    album_uri = f"spotify:album:{album_id}"
                    print(f"DEBUG: spotipy_handling.py - Attempting to play album directly: {album_uri}")
                    
                    play_result = await play_track_via_backend(album_uri, 0)
                    if play_result:
                        song_info_updater_callback("Playing Album", "Random Track", False)
                        album_name = "Album Playing"
                        artist_name = "Random Track"
                        
                        song_info_updater_callback(f"Playing Album", f"Random Track (Limited Info)", False)
                        return
                    else:
                        song_info_updater_callback("Album Unavailable", "Try Another Album", False)
                        return
                except Exception as e:
                    print(f"DEBUG: spotipy_handling.py - Error playing album directly: {e}")
                    print("DEBUG: spotipy_handling.py - Providing fallback song info")
                    song_info_updater_callback("Album Loading...", "Please Wait", False)
                return
        
        import random
        import time
        random.seed(time.time())
        
        track = random.choice(tracks)
        chosen_track_uri = track['uri']
        track_name = track.get('name', 'Unknown Track')
        track_artist = track.get('artists', [{}])[0].get('name', 'Unknown Artist')
        
        duration_ms = track.get('duration_ms', 0)
        max_position = max(0, duration_ms - 30000)
        position_ms = random.randint(0, max_position)
        is_easter_egg_track_selected = (chosen_track_uri == EASTER_EGG_TRACK_URI)
        
        print(f"DEBUG: spotipy_handling.py - Playing: {track_name} by {track_artist} at {position_ms}ms")
        print(f"DEBUG: spotipy_handling.py - Track URI: {chosen_track_uri}")
        print(f"DEBUG: spotipy_handling.py - Easter egg URI: {EASTER_EGG_TRACK_URI}")
        print(f"DEBUG: spotipy_handling.py - Is easter egg track: {is_easter_egg_track_selected}")
        
        played_successfully = await play_track_via_backend(chosen_track_uri, position_ms)
        if played_successfully:
            print(f"DEBUG: spotipy_handling.py - Successfully started playing: {track_name}")
            song_info_updater_callback(track_name, track_artist, is_easter_egg_track_selected)
        else:
            print(f"DEBUG: spotipy_handling.py - Failed to start playing: {track_name}")
            song_info_updater_callback("Failed to Start", "Check Spotify App", False)
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in play_random_track_from_album: {e}")
        import traceback
        traceback.print_exc()
        song_info_updater_callback("Album Error", "Try Again Later", False)

async def safe_pause_playback():
    if not is_pyodide():
        pass
    return True
    
    try:
        import js
        
        js_code = f'''
        fetch("{BACKEND_URL}/pause", {{
            method: "POST",
            headers: {{
                "Content-Type": "application/json"
            }},
            credentials: "include"
        }})
        .then(response => {{
            window.safe_pause_result = {{ status: response.status }};
        }})
        .catch(error => {{
            window.safe_pause_result = {{ status: 500, error: error.toString() }};
        }});
        '''
        
        js.eval(js_code)
        
        import asyncio
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'safe_pause_result'):
            result = js.window.safe_pause_result
            if isinstance(result, dict) and result.get('status') == 200:
                return True
            else:
                return False
        else:
            return False
            
    except Exception as e:
        return False

async def cleanup():
    try:
        await safe_pause_playback()
        time.sleep(0.3)
    except Exception as e:
        pass

async def show_loading_screen(screen, message="Searching for albums...", duration=3.0):
    """Shows a loading screen with animated dots for a specified duration."""
    
    loading_font = pygame.font.SysFont("Press Start 2P", 25)
    dots_font = pygame.font.SysFont("Press Start 2P", 30)
    
    start_time = time.monotonic()
    dots = ""
    dot_timer = 0
    
    while time.monotonic() - start_time < duration:
        current_time = time.monotonic()
        
        dot_timer += 16
        if dot_timer >= 500:
            if dots == "":
                dots = "."
            elif dots == ".":
                dots = ".."
            elif dots == "..":
                dots = "..."
            else:
                dots = ""
            dot_timer = 0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
        
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill((30, 30, 30))
        
        loading_text = loading_font.render(message, True, WHITE)
        loading_rect = loading_text.get_rect(center=(width // 2, height // 2 - 30))
        screen.blit(loading_text, loading_rect)
        
        dots_text = dots_font.render(dots, True, LIGHT_BLUE)
        dots_rect = dots_text.get_rect(center=(width // 2, height // 2 + 10))
        screen.blit(dots_text, dots_rect)
        
        pygame.display.flip()
        await asyncio.sleep(0.016)

async def show_inline_loading(screen, message="Loading...", duration=2.0):
    """Shows a simple loading message below the search bar."""
    
    loading_font = pygame.font.SysFont("Press Start 2P", 16)
    
    start_time = time.monotonic()
    
    while time.monotonic() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
        
        loading_text = loading_font.render(message, True, WHITE)
        loading_rect = loading_text.get_rect(center=(width // 2, 170))
        screen.blit(loading_text, loading_rect)
        
        pygame.display.flip()
        await asyncio.sleep(0.016)

async def get_album_search_input(screen, font):
    async def music_task_wrapper():
        await play_track_via_backend(SEARCH_TRACK_URI, 3000)

    try:
        await music_task_wrapper()
    except RuntimeError:
        pass
    except Exception as e:
        pass
    
    def clear_search_music():
        try:
            pass
        except Exception as e:
            pass

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
    
    cursor_visible = True
    cursor_timer = 0
    cursor_blink_rate = 500
    
    is_searching = False

    async def download_album_covers_async():
        nonlocal album_covers
        for album in search_results:
            if album['image_url'] and album['uri'] not in album_covers:
                try:
                    cover = await download_and_resize_album_cover_async(album['image_url'], 50, 50)
                    if cover:
                        album_covers[album['uri']] = cover
                except Exception as e:
                    pass
            
    async def draw_search_results_local():
        nonlocal album_covers
        
        if is_searching:
            loading_font = pygame.font.SysFont("Press Start 2P", 20)
            loading_text = loading_font.render("Searching for album... hang on", True, WHITE)
            loading_rect = loading_text.get_rect(center=(width // 2, 250))
            screen.blit(loading_text, loading_rect)
            return

        if search_results:
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
                        real_cover = await download_and_resize_album_cover_async(album['image_url'], 50, 50)
                        if real_cover:
                            album_covers[album['uri']] = real_cover
                        else:
                            album_covers[album['uri']] = create_fallback_album_cover(50, 50)
                    except Exception as e:
                        album_covers[album['uri']] = create_fallback_album_cover(50, 50)

                if album['uri'] in album_covers and album_covers[album['uri']]:
                    cover = album_covers[album['uri']]
                    cover_rect = pygame.Rect(result_rect.x + 10, result_rect.y + 10, 60, 60)
                    pygame.draw.rect(screen, (100, 100, 100), cover_rect)
                    scaled_cover = pygame.transform.scale(cover, (60, 60))
                    screen.blit(scaled_cover, (result_rect.x + 10, result_rect.y + 10))
                    text_start_x = result_rect.x + 80
                else:
                    fallback_cover = create_fallback_album_cover(50, 50)
                    album_covers[album['uri']] = fallback_cover
                    cover_rect = pygame.Rect(result_rect.x + 10, result_rect.y + 10, 60, 60)
                    pygame.draw.rect(screen, (100, 100, 100), cover_rect)
                    scaled_cover = pygame.transform.scale(fallback_cover, (60, 60))
                    screen.blit(scaled_cover, (result_rect.x + 10, result_rect.y + 10))
                    text_start_x = result_rect.x + 80
                
                name_font_local = pygame.font.SysFont('corbel', 18)
                name_surf = name_font_local.render(album['name'], True, BLACK)
                screen.blit(name_surf, (text_start_x, result_rect.y + 10))
                artist_font_local = pygame.font.SysFont('corbel', 16)
                artist_surf = artist_font_local.render(album['artist'], True, DARK_GREY)
                screen.blit(artist_surf, (text_start_x, result_rect.y + 35))
                y_offset += 80
        elif text:
            no_results_surf = font.render("Press Enter to search", True, WHITE)
            screen.blit(no_results_surf, (results_area.x + 10, results_area.y + 10))
        else:
            no_results_surf = font.render("Press Enter to search", True, WHITE)
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
                    return "BACK_TO_MENU"
                if search_results:
                    y_offset_click = results_area.y + 10
                    for album_click in search_results:
                        result_rect_click = pygame.Rect(results_area.x + 5, y_offset_click, results_area.width - 10, 70)
                        if result_rect_click.collidepoint(event.pos):
                            return album_click
                        y_offset_click += 80
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        if text:
                            is_searching = True
                            
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
                            await draw_search_results_local()
                            pygame.draw.rect(screen, LIGHT_BLUE, quit_button_rect_local)
                            quit_text_surf = quit_button_font.render("BACK TO MENU", True, BLACK)
                            quit_text_rect = quit_text_surf.get_rect(center=quit_button_rect_local.center)
                            screen.blit(quit_text_surf, quit_text_rect)
                            pygame.display.flip()
                            
                            await asyncio.sleep(0.3)
                            
                            search_results = []
                            backend_results = await search_album_via_backend(text)
                            
                            if backend_results and 'albums' in backend_results and 'items' in backend_results['albums']:
                                albums_found = len(backend_results['albums']['items'])
                                albums_to_process = backend_results['albums']['items'][:5]
                                for album in albums_to_process:
                                    album_data = {
                                        'name': album.get('name', 'Unknown Album'),
                                        'uri': album.get('uri', ''),
                                        'image_url': album.get('images', [{}])[0].get('url', None) if album.get('images') else None,
                                        'artist': album.get('artists', [{}])[0].get('name', 'Unknown Artist') if album.get('artists') else 'Unknown Artist'
                                    }
                                    search_results.append(album_data)
                                album_covers.clear()
                                
                                is_searching = False
                            else:
                                search_results = [
                                    {
                                        'name': 'Search Failed - Try Again',
                                        'uri': 'spotify:album:fallback',
                                        'image_url': 'https://example.com/fallback.jpg',
                                        'artist': 'Unknown Artist'
                                    }
                                ]
                                album_covers.clear()
                                
                                is_searching = False
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
        
        if active and cursor_visible:
            text_width = txt_surface.get_width()
            cursor_x = input_box.x + 5 + text_width
            cursor_y = input_box.y + 5
            cursor_height = txt_surface.get_height()
            pygame.draw.line(screen, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_height), 2)
        
        pygame.draw.rect(screen, color, input_box, 2)
        await draw_search_results_local()
        pygame.draw.rect(screen, LIGHT_BLUE, quit_button_rect_local)
        quit_text_surf = quit_button_font.render("BACK TO MENU", True, BLACK)
        quit_text_rect = quit_text_surf.get_rect(center=quit_button_rect_local.center)
        screen.blit(quit_text_surf, quit_text_rect)
        cursor_timer += 16
        if cursor_timer >= cursor_blink_rate:
            cursor_visible = not cursor_visible
            cursor_timer = 0
        
        pygame.display.flip()
        await asyncio.sleep(0.01)

async def play_track_via_backend(uri, position_ms=0):
    if not is_pyodide():
        return False
    
    import js
    import json
    
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
        js.eval(js_code)
        
        import asyncio
        await asyncio.sleep(0.05)
        
        if hasattr(js.window, 'play_result'):
            result = js.window.play_result
            
            if isinstance(result, dict):
                status = result.get('status', 500)
                if status == 200:
                    return True
                elif status == 404:
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
                        return False
                    else:
                        return False
                except Exception:
                    return False
        return False
    except Exception as e:
        return False

async def search_album_via_backend(query):
    if not is_pyodide():
        return {
            'albums': {
                'items': [
                    {
                        'name': 'Demo Album (Desktop Mode)',
                        'uri': 'spotify:album:demo123',
                        'images': [{'url': 'https://example.com/demo.jpg'}],
                        'artists': [{'name': 'Demo Artist'}]
                    },
                    {
                        'name': 'Test Album 2',
                        'uri': 'spotify:album:demo456',
                        'images': [{'url': 'https://example.com/test2.jpg'}],
                        'artists': [{'name': 'Test Artist'}]
                    }
                ]
            }
        }
    
    import js
    import json
    
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    
    js_code = f'''
    window.search_result = null;
    
    try {{
        fetch("{BACKEND_URL}/search?q={encoded_query}", {{
            method: "GET",
            credentials: "include",
            headers: {{
                "Accept": "application/json"
            }}
        }})
        .then(function(response) {{
            if (!response.ok) {{
                return response.text().then(function(text) {{
                    window.search_result = {{ status: response.status, text: text, error: true }};
                }});
            }}
            return response.text();
        }})
        .then(function(text) {{
            if (text) {{
                window.search_result = {{ status: 200, text: text }};
            }}
        }})
        .catch(function(error) {{
            window.search_result = {{ status: 500, error: error.toString(), message: error.message }};
        }});
    }} catch (error) {{
        window.search_result = {{ status: 500, error: error.toString(), message: error.message }};
    }}
    '''
    
    try:
        import asyncio
        js.eval(js_code)
        
        max_attempts = 10
        for attempt in range(max_attempts):
            if hasattr(js.window, 'search_result'):
                result = js.window.search_result
                if result is not None:
                    break
            await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'search_result'):
            result = js.window.search_result
        
        if isinstance(result, dict):
            status = result.get('status', 500)
            if status == 200:
                try:
                    search_data = json.loads(result.get('text', '{}'))
                    return search_data
                except json.JSONDecodeError as e:
                    return None
            else:
                return None
        elif isinstance(result, str):
            try:
                search_data = json.loads(result)
                return search_data
            except json.JSONDecodeError as e:
                return None
        else:
            try:
                status = getattr(result, 'status', 500)
                if status == 200:
                    text = getattr(result, 'text', '{}')
                    search_data = json.loads(text)
                    return search_data
                else:
                    return None
            except Exception as e:
                return None
    except Exception as e:
        return None

async def pause_playback_via_backend():
    import js
    
    js_code = f'''
    fetch("{BACKEND_URL}/pause", {{
        method: "POST",
        credentials: "include"
    }})
    .then(response => {{
        return response.text();
    }})
    .then(text => {{
        window.pause_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        window.pause_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'pause_result'):
            result = js.window.pause_result
            if isinstance(result, dict):
                return result.get('status', 500) == 200
            elif isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                    return parsed_result.get('status', 500) == 200
                except:
                    return False
            else:
                try:
                    status = getattr(result, 'status', 500)
                    return status == 200
                except:
                    return False
        else:
            return False
    except Exception as e:
        return False

async def get_devices_via_backend():
    import js
    import json
    
    js_code = f'''
    fetch("{BACKEND_URL}/devices", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        return response.text();
    }})
    .then(text => {{
        window.devices_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        window.devices_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'devices_result'):
            result = js.window.devices_result
            if isinstance(result, dict):
                return json.loads(result.get('text', '{}'))
            elif isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                    return parsed_result
                except:
                    return None
            else:
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        return json.loads(text)
                except:
                    return None
        return None
    except Exception as e:
        return None

async def get_current_playback_via_backend():
    import js
    import json
    
    js_code = f'''
    fetch("{BACKEND_URL}/currently_playing", {{
        method: "GET",
        credentials: "include"
    }})
    .then(response => {{
        return response.text();
    }})
    .then(text => {{
        window.currently_playing_result = {{ status: 200, text: text }};
    }})
    .catch(error => {{
        window.currently_playing_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'currently_playing_result'):
            result = js.window.currently_playing_result
            if isinstance(result, dict):
                return json.loads(result.get('text', '{}'))
            elif isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                    return parsed_result
                except:
                    return None
            else:
                try:
                    status = getattr(result, 'status', 500)
                    if status == 200:
                        text = getattr(result, 'text', '{}')
                        return json.loads(text)
                except:
                    return None
        return None
    except Exception as e:
        return None

async def verify_album_playability(album_uri):
    """Verify that an album is playable by testing access to its tracks"""
    
    if album_uri.startswith('spotify:album:'):
        album_id = album_uri.replace('spotify:album:', '')
    else:
        album_id = album_uri
    
    max_retries = 3
    for attempt in range(max_retries):
        
        tracks_data = await get_album_tracks_via_backend(album_id)
        
        if tracks_data and 'items' in tracks_data:
            tracks = tracks_data.get('items', [])
            if tracks:
                return True
            else:
                return False
        else:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
            else:
                return False
    
    return False

async def get_album_tracks_via_backend(album_id):
    import js
    import json
    url = f"{BACKEND_URL}/album_tracks?album_id={album_id}"
    
    js_code = f'''
    fetch("{url}", {{
        method: "GET",
        credentials: "include",
        headers: {{
            "Accept": "application/json",
            "Content-Type": "application/json"
        }}
    }})
    .then(response => {{
        return response.text();
    }})
    .then(text => {{
        if (text.trim().startsWith('{{')) {{
            try {{
                const data = JSON.parse(text);
                window.album_tracks_result = {{ status: data.status || 200, text: text }};
            }} catch(e) {{
                window.album_tracks_result = {{ status: 500, text: text }};
            }}
        }} else {{
            window.album_tracks_result = {{ status: 500, text: text }};
        }}
    }})
    .catch(error => {{
        window.album_tracks_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        
        await asyncio.sleep(0.5)
        
        max_checks = 3
        for check in range(max_checks):
            if hasattr(js.window, 'album_tracks_result'):
                result = js.window.album_tracks_result
                print(f"DEBUG: spotipy_handling.py - Album tracks result (check {check + 1}): {result}")
                
                if isinstance(result, dict):
                    if result.get('status') == 200:
                        try:
                            return json.loads(result.get('text', '{}'))
                        except json.JSONDecodeError as e:
                            print(f"DEBUG: spotipy_handling.py - JSON decode error: {e}")
                            return None
                elif isinstance(result, str):
                    try:
                        parsed_result = json.loads(result)
                        return parsed_result
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: spotipy_handling.py - String JSON decode error: {e}")
                        return None
                else:
                    try:
                        status = getattr(result, 'status', 500)
                        if status == 200:
                            text = getattr(result, 'text', '{}')
                            return json.loads(text)
                    except Exception as e:
                        print(f"DEBUG: spotipy_handling.py - Object property access error: {e}")
                        return None
            
            if check < max_checks - 1:
                print(f"DEBUG: spotipy_handling.py - No result yet, waiting... (check {check + 1})")
                await asyncio.sleep(0.3)
        
        print("DEBUG: spotipy_handling.py - No album tracks result after all checks")
        return None
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error in get_album_tracks_via_backend: {e}")
        return None

def base64_to_pygame_surface(base64_data, target_width, target_height):
    try:
        import base64
        import struct
        
        image_data = base64.b64decode(base64_data)
        
        import hashlib
        hash_value = hashlib.md5(image_data).hexdigest()
        
        surface = pygame.Surface((target_width, target_height))
        
        r_base = int(hash_value[0:2], 16)
        g_base = int(hash_value[2:4], 16)
        b_base = int(hash_value[4:6], 16)
        
        r_base = max(r_base, 50)
        g_base = max(g_base, 50)
        b_base = max(b_base, 50)
        
        for y in range(target_height):
            for x in range(target_width):
                progress_x = x / target_width
                progress_y = y / target_height
                
                r = int((r_base + progress_x * 100 + progress_y * 50) % 256)
                g = int((g_base + progress_y * 100 + progress_x * 50) % 256)
                b = int((b_base + (progress_x + progress_y) * 75) % 256)
                
                r = max(r, 30)
                g = max(g, 30)
                b = max(b, 30)
                
                surface.set_at((x, y), (r, g, b))
        
        border_color = (
            int(hash_value[6:8], 16),
            int(hash_value[8:10], 16),
            int(hash_value[10:12], 16)
        )
        pygame.draw.rect(surface, border_color, surface.get_rect(), 2)
        
        print(f"DEBUG: spotipy_handling.py - Created surface from base64 data: {surface.get_size()}")
        print(f"DEBUG: spotipy_handling.py - Base colors: R={r_base}, G={g_base}, B={b_base}")
        return surface
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error converting base64 to surface: {e}")
        return None

async def base64_to_pygame_surface_pygbag(base64_data, target_width, target_height):
    try:
        import base64
        
        image_data = base64.b64decode(base64_data)
        
        surface = pygame.Surface((target_width, target_height))
        
        js_code = f'''
        try {{
            const canvas = document.createElement('canvas');
            canvas.width = {target_width};
            canvas.height = {target_height};
            const ctx = canvas.getContext('2d');
            
            const img = new Image();
            img.crossOrigin = "anonymous";
            
            img.onload = function() {{
                ctx.drawImage(img, 0, 0, {target_width}, {target_height});
                
                const imageData = ctx.getImageData(0, 0, {target_width}, {target_height});
                window.album_cover_pixels = imageData.data;
                window.album_cover_loaded = true;
            }};
            
            img.onerror = function() {{
                window.album_cover_loaded = false;
            }};
            
            img.src = "data:image/jpeg;base64,{base64_data}";
            
        }} catch(e) {{
            window.album_cover_loaded = false;
        }}
        '''
        
        import js
        js.eval(js_code)
        
        import asyncio
        await asyncio.sleep(0.3)
        
        if hasattr(js.window, 'album_cover_loaded') and js.window.album_cover_loaded:
            if hasattr(js.window, 'album_cover_pixels'):
                pixels = js.window.album_cover_pixels
                
                for y in range(target_height):
                    for x in range(target_width):
                        idx = (y * target_width + x) * 4
                        r = int(pixels[idx])
                        g = int(pixels[idx + 1])
                        b = int(pixels[idx + 2])
                        a = int(pixels[idx + 3])
                        surface.set_at((x, y), (r, g, b, a))
                
                return surface
            else:
                return create_visual_album_cover_from_data(image_data, target_width, target_height)
        else:
            return create_visual_album_cover_from_data(image_data, target_width, target_height)
            
    except Exception as e:
        return create_visual_album_cover_from_data(image_data, target_width, target_height)

def setup_page_unload_handler():
    if not is_pyodide():
        return
    
    try:
        import js
        
        js_code = f'''
        window.pauseMusicOnUnload = function() {{
            if (navigator.sendBeacon) {{
                try {{
                    var data = new Blob(['{{}}'], {{type: 'application/json'}});
                    var success = navigator.sendBeacon('{BACKEND_URL}/pause', data);
                }} catch (error) {{
                    // sendBeacon failed
                }}
            }}
            
            try {{
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '{BACKEND_URL}/pause', false);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.withCredentials = true;
                xhr.send();
            }} catch (error) {{
                // Synchronous request failed
            }}
        }};
        
        window.pauseMusicOnVisibilityChange = function() {{
            fetch('{BACKEND_URL}/pause', {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json"
                }},
                credentials: "include"
            }})
            .then(response => {{
                // Pause request sent
            }})
            .catch(error => {{
                // Pause request failed
            }});
        }};
        
        window.addEventListener('beforeunload', window.pauseMusicOnUnload);
        window.addEventListener('unload', window.pauseMusicOnUnload);
        window.addEventListener('pagehide', window.pauseMusicOnUnload);
        
        document.addEventListener('visibilitychange', function() {{
            if (document.visibilityState === 'hidden') {{
                window.pauseMusicOnVisibilityChange();
            }}
        }});
        
        window.addEventListener('blur', function() {{
            window.pauseMusicOnVisibilityChange();
        }});
        
        window.pageActiveHeartbeat = Date.now();
        setInterval(function() {{
            window.pageActiveHeartbeat = Date.now();
        }}, 1000);
        
        setInterval(function() {{
            var timeSinceLastHeartbeat = Date.now() - window.pageActiveHeartbeat;
            if (timeSinceLastHeartbeat > 10000) {{
                window.pauseMusicOnVisibilityChange();
            }}
        }}, 5000);
        
        window.testPauseMusic = function() {{
            window.pauseMusicOnVisibilityChange();
        }};
        '''
        
        js.eval(js_code)
        
    except Exception as e:
        import traceback
        traceback.print_exc()

# Set up page unload handlers on module import
setup_page_unload_handler()