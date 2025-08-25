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

    # Check if we're in a browser environment
    if is_pyodide():
        try:
            import js  # Only available in Pyodide/Pygbag
            if hasattr(js, 'window'):
                js.window.open(login_url, "_blank")
                print("DEBUG: spotipy_handling.py - Opened login URL in browser (js.window.open)")
            else:
                print("DEBUG: spotipy_handling.py - js module available but no window attribute")
                is_logging_in = False
        except Exception as e:
            print(f"DEBUG: spotipy_handling.py - Error in browser login: {e}")
            is_logging_in = False
    else:
        # Fallback for desktop Python
        try:
            import webbrowser
            webbrowser.open(login_url)
            print("DEBUG: spotipy_handling.py - Opened login URL in desktop browser (webbrowser.open)")
        except Exception as e:
            print(f"DEBUG: spotipy_handling.py - Error opening browser: {e}")
    is_logging_in = False

def is_pyodide():
    """Check if we're running in a browser environment (pygbag/pyodide)"""
    try:
        import js
        # Check for browser-specific attributes
        has_window = hasattr(js, 'window')
        has_fetch = hasattr(js, 'fetch')
        has_eval = hasattr(js, 'eval')
        
        # In pygbag/pyodide, we should have all these
        is_browser = has_window and has_fetch and has_eval
        
        print(f"DEBUG: spotipy_handling.py - Environment check: window={has_window}, fetch={has_fetch}, eval={has_eval}, is_browser={is_browser}")
        return is_browser
    except ImportError:
        print("DEBUG: spotipy_handling.py - js module not available")
        return False
    except AttributeError:
        print("DEBUG: spotipy_handling.py - js module available but missing required attributes")
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

# Check if we're in a browser environment with proper js module
try:
    if hasattr(js, 'window'):
        js.window.handle_auth_result = handle_auth_result  # Attach to window explicitly
        js.auth_success = False
    else:
        print("DEBUG: spotipy_handling.py - js module available but no window attribute (desktop environment)")
        js.auth_success = False
except Exception as e:
    print(f"DEBUG: spotipy_handling.py - Error setting up js window: {e}")
    # Don't set js.auth_success if js module is not properly available
    pass

async def check_authenticated():
    print("DEBUG: spotipy_handling.py - check_authenticated called (async version)")
    
    # Check if we're in a browser environment
    if not is_pyodide():
        print("DEBUG: spotipy_handling.py - Not in browser environment, using desktop fallback")
        # For desktop, we'll assume not authenticated and show login screen
        return False
    
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
        console.log("JS: /me response status:", result.status);
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
                        # Try to get the error text
                        try:
                            if hasattr(result, 'text'):
                                error_text = result.text
                                print(f"DEBUG: spotipy_handling.py - Error response text: {error_text}")
                        except:
                            pass
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
    
    if not url:
        return create_fallback_album_cover(target_width, target_height)
    
    # Try to load the actual image using the backend proxy
    try:
        import js
        import base64
        # Check if we're in a proper browser environment (pygbag/pyodide)
        if is_pyodide():
            print(f"DEBUG: spotipy_handling.py - Running in pygbag/pyodide environment, using browser download")
        else:
            print(f"DEBUG: spotipy_handling.py - Desktop environment detected, using Python download")
            raise ImportError("Desktop environment - use Python fallback")
    except ImportError:
        print(f"DEBUG: spotipy_handling.py - js module not available, trying Python download")
        # Try to download using Python requests if available
        try:
            import requests
            print(f"DEBUG: spotipy_handling.py - Using Python requests to download image")
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
                        print(f"DEBUG: spotipy_handling.py - Successfully downloaded image via Python")
                        return resized_image
                    except Exception as e:
                        print(f"DEBUG: spotipy_handling.py - Failed to load image from Python download: {e}")
                        return create_visual_album_cover(url, target_width, target_height)
                else:
                    print(f"DEBUG: spotipy_handling.py - Backend returned error: {data}")
                    return create_visual_album_cover(url, target_width, target_height)
            else:
                print(f"DEBUG: spotipy_handling.py - Backend request failed with status: {response.status_code}")
                return create_visual_album_cover(url, target_width, target_height)
        except ImportError:
            print(f"DEBUG: spotipy_handling.py - requests module not available, using fallback cover")
            return create_visual_album_cover(url, target_width, target_height)
        except Exception as e:
            print(f"DEBUG: spotipy_handling.py - Python download failed: {e}")
            return create_visual_album_cover(url, target_width, target_height)
    
    # First, let's test if JavaScript is working at all
    print(f"DEBUG: spotipy_handling.py - Testing JavaScript functionality")
    test_js = '''
    console.log("JavaScript test: Hello from JS!");
    window.js_test_result = "JavaScript is working";
    console.log("Set window.js_test_result");
    '''
    
    try:
        js.eval(test_js)
        await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'js_test_result'):
            print(f"DEBUG: spotipy_handling.py - JavaScript test successful: {js.window.js_test_result}")
        else:
            print(f"DEBUG: spotipy_handling.py - JavaScript test failed - no result found")
            
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - JavaScript test failed: {e}")
        # If JavaScript is not working, fall back to Python immediately
        print(f"DEBUG: spotipy_handling.py - Falling back to Python download due to JavaScript failure")
        raise ImportError("JavaScript not working")
    
    js_code = f'''
    console.log("Starting album cover download for: {url}");
    
    // Use async/await for proper handling
    (async () => {{
        try {{
            console.log("Fetching from backend:", "{BACKEND_URL}/download_album_cover");
            const response = await fetch("{BACKEND_URL}/download_album_cover", {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json"
                }},
                credentials: "include",
                body: JSON.stringify({{"image_url": "{url}"}})
            }});
            
            console.log("Response status:", response.status);
            console.log("Response ok:", response.ok);
            
            if (!response.ok) {{
                throw new Error(`HTTP error! status: ${{response.status}}`);
            }}
            
            const data = await response.json();
            console.log("Received data:", data);
            
            // Set the result in window for Python to access
            window.image_download_result = data;
            console.log("Set window.image_download_result to:", window.image_download_result);
            
            // Also set a flag to indicate completion
            window.image_download_complete = true;
            console.log("Image download completed successfully");
            
        }} catch (error) {{
            console.log("Album cover download error:", error);
            window.image_download_result = {{ status: 500, error: error.toString() }};
            window.image_download_complete = true;
            console.log("Image download failed, but marked as complete");
        }}
    }})();
    '''
    
    try:
        print(f"DEBUG: spotipy_handling.py - Executing JavaScript code for {url}")
        js.eval(js_code)
        print(f"DEBUG: spotipy_handling.py - JavaScript code executed, waiting for result")
        
        # Wait for the async JavaScript to complete
        for i in range(10):  # Wait up to 1 second (10 * 100ms) - reduced further
            await asyncio.sleep(0.1)  # Wait 100ms each time
            
            # Check if the download is complete
            if hasattr(js.window, 'image_download_complete') and js.window.image_download_complete:
                break
                
            # Also check if we have a result (in case complete flag isn't set)
            if hasattr(js.window, 'image_download_result') and js.window.image_download_result is not None:
                break
        
        # Get the result and clean up
        result = None
        if hasattr(js.window, 'image_download_result'):
            js_result = js.window.image_download_result
            
            # Convert JavaScript object to Python dictionary
            try:
                print(f"DEBUG: spotipy_handling.py - Attempting to convert JavaScript object")
                
                # Try multiple approaches to access the object
                result = None
                
                # Approach 1: Try accessing properties directly (most reliable)
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
                        print(f"DEBUG: spotipy_handling.py - Direct property access failed: {e}")
                
                # Approach 2: Try using JavaScript to convert to JSON
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
                        print(f"DEBUG: spotipy_handling.py - JSON approach failed: {e}")
                
                # Approach 3: Try to_py() method as last resort
                if result is None and hasattr(js_result, 'to_py'):
                    try:
                        result = js_result.to_py()
                    except Exception as e:
                        print(f"DEBUG: spotipy_handling.py - to_py() failed: {e}")
                
                # Approach 4: Last resort - try to access as string
                if result is None:
                    try:
                        result_str = str(js_result)
                        # Try to extract data from string representation
                        if 'data' in result_str and 'status' in result_str:
                            # This is a fallback - we'll use visual cover instead
                            result = None  # Force visual cover
                    except Exception as e:
                        print(f"DEBUG: spotipy_handling.py - String conversion failed: {e}")
                    
            except Exception as e:
                print(f"DEBUG: spotipy_handling.py - Error in conversion process: {e}")
                result = None
            
            # Clean up the flags for next download
            try:
                js.window.image_download_result = None
                js.window.image_download_complete = False
            except Exception as e:
                print(f"DEBUG: spotipy_handling.py - Error cleaning up flags: {e}")
        else:
            print(f"DEBUG: spotipy_handling.py - No image_download_result found in window")
            return create_visual_album_cover(url, target_width, target_height)
            
        # Handle different result types
        if isinstance(result, dict):
            status = result.get('status', 500)
            if status == 200:
                base64_data = result.get('data')
                if base64_data:
                    try:
                        # Use pygbag-specific helper for better browser compatibility
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
            # Handle JavaScript object with status property
            status = result.status
            if status == 200:
                try:
                    # Try to access the data property
                    if hasattr(result, 'data'):
                        base64_data = result.data
                        if base64_data:
                            # Convert base64 to pygame surface without using pygame.image.load()
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
        print(f"DEBUG: spotipy_handling.py - Error in download_and_resize_album_cover_async: {e}")
        return create_visual_album_cover(url, target_width, target_height)

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
        
        # Create a more vibrant, colorful pattern
        import random
        import time
        
        # Use time to create different patterns each time
        random.seed(int(time.time() * 1000) % 1000)
        
        # Create a colorful gradient pattern
        for y in range(target_height):
            for x in range(target_width):
                # Create a more vibrant pattern
                progress_x = x / target_width
                progress_y = y / target_height
                
                # Generate bright, colorful gradients
                r = int(128 + 127 * (progress_x + random.random() * 0.3))
                g = int(128 + 127 * (progress_y + random.random() * 0.3))
                b = int(128 + 127 * ((progress_x + progress_y) / 2 + random.random() * 0.3))
                
                # Ensure values are in valid range
                r = max(50, min(255, r))
                g = max(50, min(255, g))
                b = max(50, min(255, b))
                
                surface.set_at((x, y), (r, g, b))
        
        # Add a colorful border
        border_color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        pygame.draw.rect(surface, border_color, surface.get_rect(), 2)
        
        # Add some text to indicate it's an album cover
        try:
            font = pygame.font.SysFont("Arial", min(target_width, target_height) // 8)
            text = font.render("ALBUM", True, (255, 255, 255))
            text_rect = text.get_rect(center=(target_width // 2, target_height // 2))
            surface.blit(text, text_rect)
        except Exception as e:
            pass  # If font rendering fails, just use the gradient
        
        return surface
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error creating fallback album cover: {e}")
        return None

def create_visual_album_cover(image_url, target_width, target_height):
    """Create a visual album cover that works in browser environments"""
    try:
        # Generate a unique color pattern based on the image URL
        import hashlib
        hash_value = hashlib.md5(image_url.encode()).hexdigest()
        print(f"DEBUG: spotipy_handling.py - Hash value: {hash_value}")
        
        # Create a surface
        surface = pygame.Surface((target_width, target_height))
        
        # Create a cleaner, more appealing pattern
        # Use the hash to generate a consistent color palette
        r_base = int(hash_value[0:2], 16)
        g_base = int(hash_value[2:4], 16)
        b_base = int(hash_value[4:6], 16)
        
        print(f"DEBUG: spotipy_handling.py - Creating visual cover with base colors: R={r_base}, G={g_base}, B={b_base}")
        
        # If all colors are 0, use a fallback
        if r_base == 0 and g_base == 0 and b_base == 0:
            print(f"DEBUG: spotipy_handling.py - All base colors are 0, using fallback colors")
            r_base = 128
            g_base = 64
            b_base = 192
        
        # Create a gradient pattern
        for y in range(target_height):
            for x in range(target_width):
                # Create a smooth gradient based on position
                x_ratio = x / target_width
                y_ratio = y / target_height
                
                # Mix the base colors with position-based variation
                r = int(r_base * (0.5 + 0.5 * x_ratio))
                g = int(g_base * (0.5 + 0.5 * y_ratio))
                b = int(b_base * (0.5 + 0.5 * (x_ratio + y_ratio) / 2))
                
                # Ensure values are in valid range
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                
                # Fill the surface with the color
                surface.set_at((x, y), (r, g, b))
        
        # Add a subtle border
        pygame.draw.rect(surface, (255, 255, 255), surface.get_rect(), 1)
        
        # Check if the surface has visible content
        try:
            sample_pixel = surface.get_at((0, 0))
            print(f"DEBUG: spotipy_handling.py - Visual cover sample pixel: {sample_pixel}")
        except Exception as e:
            print(f"DEBUG: spotipy_handling.py - Error checking visual cover pixel: {e}")
        
        return surface
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error creating visual album cover: {e}")
        return create_fallback_album_cover(target_width, target_height)

def create_visual_album_cover_from_data(image_data, target_width, target_height):
    """Create a visual album cover from image data when pygame.image.load fails"""
    try:
        # Generate a unique color pattern based on the image data
        import hashlib
        hash_value = hashlib.md5(image_data).hexdigest()
        
        # Create a surface
        surface = pygame.Surface((target_width, target_height))
        
        # Use the hash to generate a consistent color palette
        r_base = int(hash_value[0:2], 16)
        g_base = int(hash_value[2:4], 16)
        b_base = int(hash_value[4:6], 16)
        
        # Ensure minimum brightness
        r_base = max(r_base, 50)
        g_base = max(g_base, 50)
        b_base = max(b_base, 50)
        
        # Create a more vibrant pattern
        for y in range(target_height):
            for x in range(target_width):
                # Create a gradient pattern
                progress_x = x / target_width
                progress_y = y / target_height
                
                # Generate colors with more variation
                r = int((r_base + progress_x * 100 + progress_y * 50) % 256)
                g = int((g_base + progress_y * 100 + progress_x * 50) % 256)
                b = int((b_base + (progress_x + progress_y) * 75) % 256)
                
                # Ensure minimum brightness
                r = max(r, 30)
                g = max(g, 30)
                b = max(b, 30)
                
                surface.set_at((x, y), (r, g, b))
        
        # Add a colored border based on the hash
        border_color = (
            int(hash_value[6:8], 16),
            int(hash_value[8:10], 16),
            int(hash_value[10:12], 16)
        )
        pygame.draw.rect(surface, border_color, surface.get_rect(), 2)
        
        return surface
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error creating visual cover from data: {e}")
        return create_fallback_album_cover(target_width, target_height)

def create_album_cover_like_surface(image_data, target_width, target_height):
    """Create a surface that looks more like an actual album cover"""
    try:
        import hashlib
        hash_value = hashlib.md5(image_data).hexdigest()
        
        # Create a surface
        surface = pygame.Surface((target_width, target_height))
        
        # Extract multiple color palettes from the hash to create more realistic patterns
        colors = []
        for i in range(0, len(hash_value), 6):
            if i + 5 < len(hash_value):
                r = int(hash_value[i:i+2], 16)
                g = int(hash_value[i+2:i+4], 16)
                b = int(hash_value[i+4:i+6], 16)
                colors.append((r, g, b))
        
        # Ensure we have at least 2 colors
        if len(colors) < 2:
            colors.extend([(128, 128, 128), (64, 64, 64)])
        
        # Create a more sophisticated pattern that looks like an album cover
        for y in range(target_height):
            for x in range(target_width):
                # Create multiple layers of patterns
                
                # Layer 1: Base gradient
                progress_x = x / target_width
                progress_y = y / target_height
                
                # Use the first two colors for the main gradient
                color1 = colors[0]
                color2 = colors[1] if len(colors) > 1 else colors[0]
                
                # Create a diagonal gradient
                gradient_progress = (progress_x + progress_y) / 2
                r = int(color1[0] * (1 - gradient_progress) + color2[0] * gradient_progress)
                g = int(color1[1] * (1 - gradient_progress) + color2[1] * gradient_progress)
                b = int(color1[2] * (1 - gradient_progress) + color2[2] * gradient_progress)
                
                # Layer 2: Add texture based on image data
                texture_index = (x * 7 + y * 11) % len(hash_value)
                texture_char = hash_value[texture_index]
                texture_value = int(texture_char, 16)
                
                # Add subtle texture variation
                texture_offset = (texture_value - 8) * 3
                r = max(0, min(255, r + texture_offset))
                g = max(0, min(255, g + texture_offset))
                b = max(0, min(255, b + texture_offset))
                
                # Layer 3: Add some geometric patterns
                if len(colors) > 2:
                    # Create some geometric shapes
                    center_x, center_y = target_width // 2, target_height // 2
                    distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    
                    # Add circular patterns
                    if distance < target_width // 4:
                        color3 = colors[2]
                        blend_factor = 0.3
                        r = int(r * (1 - blend_factor) + color3[0] * blend_factor)
                        g = int(g * (1 - blend_factor) + color3[1] * blend_factor)
                        b = int(b * (1 - blend_factor) + color3[2] * blend_factor)
                
                surface.set_at((x, y), (r, g, b))
        
        # Add a realistic album cover border
        pygame.draw.rect(surface, (255, 255, 255), surface.get_rect(), 2)
        
        # Add a subtle inner border
        pygame.draw.rect(surface, (200, 200, 200), surface.get_rect(), 1)
        
        # Add a drop shadow effect
        shadow_surface = pygame.Surface((target_width + 4, target_height + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surface, (0, 0, 0, 80), (4, 4, target_width, target_height))
        surface.blit(shadow_surface, (-2, -2))
        
        print(f"DEBUG: spotipy_handling.py - Created realistic album cover with {len(colors)} colors")
        return surface
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error creating album-like cover: {e}")
        return create_visual_album_cover_from_data(image_data, target_width, target_height)

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
    
    # Import required modules first
    import js
    import json
    import random
    import time
    import asyncio
    
    # Simple caching to avoid repeated API calls for the same album
    cache_key = f"album_tracks_{album_id}"
    current_time = time.time()
    
    # Check if we have cached tracks for this album (cache for 30 seconds)
    if hasattr(js.window, cache_key):
        cached_data_json = getattr(js.window, cache_key)
        cached_data = None
        try:
            # Check if the cached data is actually a string
            if cached_data_json is None:
                print(f"DEBUG: spotipy_handling.py - Cached data is None, clearing invalid cache")
                if hasattr(js.window, cache_key):
                    delattr(js.window, cache_key)
                cached_data = None
            elif isinstance(cached_data_json, str):
                cached_data = json.loads(cached_data_json)
            else:
                print(f"DEBUG: spotipy_handling.py - Cached data is not a string: {type(cached_data_json)}")
                if hasattr(js.window, cache_key):
                    delattr(js.window, cache_key)
                cached_data = None
        except (json.JSONDecodeError, TypeError) as e:
            print(f"DEBUG: spotipy_handling.py - Failed to parse cached data: {e}")
            # Clear invalid cache
            if hasattr(js.window, cache_key):
                delattr(js.window, cache_key)
            cached_data = None
        
        if cached_data and isinstance(cached_data, dict) and 'tracks' in cached_data and 'timestamp' in cached_data:
            if current_time - cached_data['timestamp'] < 30:  # 30 second cache
                print(f"DEBUG: spotipy_handling.py - Using cached tracks for album {album_id}")
                tracks = cached_data['tracks']
                if tracks:
                    # Select a random track from cached tracks
                    track = random.choice(tracks)
                    track_name = track.get('name', 'Unknown Track')
                    artist_name = track.get('artists', [{}])[0].get('name', 'Unknown Artist') if track.get('artists') else 'Unknown Artist'
                    
                    # Play the track
                    track_uri = track.get('uri', '')
                    if track_uri:
                        # Calculate random position from start to 30 seconds before end
                        duration_ms = track.get('duration_ms', 0)
                        max_position = max(0, duration_ms - 30000)  # 30 seconds before end
                        position_ms = random.randint(0, max_position)
                        print(f"DEBUG: spotipy_handling.py - Playing cached track: {track_name} by {artist_name} at {position_ms}ms")
                        await play_track_via_backend(track_uri, position_ms)
                        song_info_updater_callback(track_name, artist_name, False)
                        return
                    else:
                        print(f"DEBUG: spotipy_handling.py - Cached track has no URI")
                else:
                    print(f"DEBUG: spotipy_handling.py - Cached tracks list is empty")
            else:
                print(f"DEBUG: spotipy_handling.py - Cache expired for album {album_id}")
        else:
            print(f"DEBUG: spotipy_handling.py - Invalid cache data for album {album_id}")
    
    # Clear any cached album tracks to ensure fresh data
    if hasattr(js.window, 'album_tracks_sync_result'):
        delattr(js.window, 'album_tracks_sync_result')
        print("DEBUG: spotipy_handling.py - Cleared cached album tracks")
    
    # Extract album ID from URI if needed
    if album_id.startswith('spotify:album:'):
        album_id = album_id.replace('spotify:album:', '')
        print(f"DEBUG: spotipy_handling.py - Extracted album ID: {album_id}")
    
    # First, let's test if the user is still authenticated
    print(f"DEBUG: spotipy_handling.py - Testing authentication before getting album tracks")
    try:
        auth_result = await check_authenticated()
        print(f"DEBUG: spotipy_handling.py - Authentication check result: {auth_result}")
        if not auth_result:
            print(f"DEBUG: spotipy_handling.py - User not authenticated, cannot get album tracks")
            song_info_updater_callback("Authentication Required", "Please login", False)
            return
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Authentication check failed: {e}")
    
    # Skip the session test and delays - go straight to album tracks
    print(f"DEBUG: spotipy_handling.py - Skipping session test and delays for faster loading")
    
    # Test backend connectivity and session first
    print(f"DEBUG: spotipy_handling.py - Testing backend connectivity and session")
    try:
        test_js_code = f'''
        // Test ping first
        fetch("{BACKEND_URL}/ping", {{
            method: "GET",
            credentials: "include"
        }})
        .then(response => {{
            console.log("JS: Ping response status:", response.status);
            return response.text();
        }})
        .then(text => {{
            console.log("JS: Ping response:", text);
            window.ping_result = {{ status: 200, text: text }};
            
            // Then test session
            return fetch("{BACKEND_URL}/test_session", {{
                method: "GET",
                credentials: "include"
            }});
        }})
        .then(response => {{
            console.log("JS: Session test response status:", response.status);
            return response.text();
        }})
        .then(text => {{
            console.log("JS: Session test response:", text);
            window.session_result = {{ status: 200, text: text }};
        }})
        .catch(error => {{
            console.log("JS: Test error:", error);
            window.ping_result = {{ status: 500, error: error.toString() }};
        }});
        '''
        js.eval(test_js_code)
        await asyncio.sleep(0.3)
        
        if hasattr(js.window, 'ping_result'):
            ping_result = js.window.ping_result
            print(f"DEBUG: spotipy_handling.py - Backend ping result: {ping_result}")
        
        if hasattr(js.window, 'session_result'):
            session_result = js.window.session_result
            print(f"DEBUG: spotipy_handling.py - Session test result: {session_result}")
            print(f"DEBUG: spotipy_handling.py - Session result type: {type(session_result)}")
            
            # Try to get more details from the session result
            if isinstance(session_result, dict):
                session_text = session_result.get('text', 'No text')
                print(f"DEBUG: spotipy_handling.py - Session test text: {session_text}")
                try:
                    session_data = json.loads(session_text)
                    print(f"DEBUG: spotipy_handling.py - Session data: {session_data}")
                    has_token = session_data.get('has_token', False)
                    print(f"DEBUG: spotipy_handling.py - Session has token: {has_token}")
                except json.JSONDecodeError:
                    print(f"DEBUG: spotipy_handling.py - Could not parse session text as JSON")
            else:
                print(f"DEBUG: spotipy_handling.py - Session result is not a dict, it's: {type(session_result)}")
                # Try to access properties directly from browser object
                try:
                    session_text = getattr(session_result, 'text', 'No text')
                    print(f"DEBUG: spotipy_handling.py - Session test text (direct): {session_text}")
                    session_status = getattr(session_result, 'status', 'No status')
                    print(f"DEBUG: spotipy_handling.py - Session test status (direct): {session_status}")
                    
                    if session_text and session_text != 'No text':
                        try:
                            session_data = json.loads(session_text)
                            print(f"DEBUG: spotipy_handling.py - Session data (direct): {session_data}")
                            has_token = session_data.get('has_token', False)
                            print(f"DEBUG: spotipy_handling.py - Session has token (direct): {has_token}")
                        except json.JSONDecodeError:
                            print(f"DEBUG: spotipy_handling.py - Could not parse session text as JSON (direct)")
                except Exception as e:
                    print(f"DEBUG: spotipy_handling.py - Could not access session result properties: {e}")
        else:
            print(f"DEBUG: spotipy_handling.py - No session result received")
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Backend test failed: {e}")
    
    # For the first song, try to play the album directly first to ensure immediate playback
    # This avoids the API call delay that might be causing the first song not to play
    if not hasattr(js.window, 'first_song_played'):
        print(f"DEBUG: spotipy_handling.py - First song, playing album directly for immediate playback")
        try:
            album_uri = f"spotify:album:{album_id}"
            print(f"DEBUG: spotipy_handling.py - Playing album directly: {album_uri}")
            play_result = await play_track_via_backend(album_uri, 0)
            if play_result:
                print("DEBUG: spotipy_handling.py - Successfully started playing album for first song")
                song_info_updater_callback("Playing Album", "Random Track", False)
                # Mark that we've played the first song
                setattr(js.window, 'first_song_played', True)
                return
            else:
                print("DEBUG: spotipy_handling.py - Failed to play album directly, will try API")
        except Exception as e:
            print(f"DEBUG: spotipy_handling.py - Error playing album directly: {e}")
    
    # Mark that we've attempted the first song
    setattr(js.window, 'first_song_played', True)
    
    # Use async approach with js.eval for getting album tracks
    
    js_code = f'''
    console.log("JS: ===== ALBUM TRACKS FETCH START =====");
    console.log("JS: Fetching album tracks for album_id:", "{album_id}");
    console.log("JS: Backend URL:", "{BACKEND_URL}");
    console.log("JS: Full URL:", "{BACKEND_URL}/album_tracks?album_id={album_id}");
    
    // Clear any existing result first
    window.album_tracks_sync_result = null;
    console.log("JS: Cleared previous result");
    
    // First, let's check what cookies we have
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
            // Looks like JSON, parse it to check status
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
        await asyncio.sleep(0.5)  # Wait longer for the fetch to complete
        
        # Check if result is available
        if hasattr(js.window, 'album_tracks_sync_result'):
            print(f"DEBUG: spotipy_handling.py - Result found after 0.5s")
        else:
            print(f"DEBUG: spotipy_handling.py - No result after 0.5s, waiting more...")
            await asyncio.sleep(0.3)  # Wait a bit more
        
        tracks_data = None
        if hasattr(js.window, 'album_tracks_sync_result'):
            result = js.window.album_tracks_sync_result
            print(f"DEBUG: spotipy_handling.py - Album tracks result type: {type(result)}")
            print(f"DEBUG: spotipy_handling.py - Album tracks result: {result}")
            
            # Handle both object and string cases
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
                
                # Try to parse the error text to get more details
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
                    
                # Also try to access properties directly if it's a browser object
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
                # If it's a string, try to parse it as JSON
                try:
                    tracks_data = json.loads(result)
                except json.JSONDecodeError as e:
                    print(f"DEBUG: spotipy_handling.py - JSON decode error from string: {e}")
            else:
                # If it's an object, try to access properties directly
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
        
        # Cache the tracks if we found them successfully
        if tracks:
            # Convert to JSON string to avoid JavaScript conversion issues
            cache_data_json = json.dumps({
                'tracks': tracks,
                'timestamp': current_time
            })
            setattr(js.window, cache_key, cache_data_json)
            print(f"DEBUG: spotipy_handling.py - Cached {len(tracks)} tracks for album {album_id}")
        
        if not tracks:
            print("DEBUG: spotipy_handling.py - No tracks found on first attempt, retrying with exponential backoff...")
            # Try multiple retries with increasing delays
            for retry_attempt in range(2):  # Reduced to just 2 retries
                delay = (retry_attempt + 1) * 0.1  # Very short delays: 0.1s, 0.2s
                print(f"DEBUG: spotipy_handling.py - Retry attempt {retry_attempt + 1} in {delay} seconds...")
                await asyncio.sleep(delay)
            
            # Retry the request (skip connectivity test for speed)
            print("DEBUG: spotipy_handling.py - Retrying album tracks request...")
            try:
                # Clear the result before retry to ensure fresh data
                if hasattr(js.window, 'album_tracks_sync_result'):
                    delattr(js.window, 'album_tracks_sync_result')
                js.eval(js_code)
                await asyncio.sleep(0.5)  # Wait for retry
                
                if hasattr(js.window, 'album_tracks_sync_result'):
                    result = js.window.album_tracks_sync_result
                    
                    # Handle the retry result the same way
                    if isinstance(result, dict):
                        if result.get('status') == 200:
                            try:
                                tracks_data = json.loads(result.get('text', '{}'))
                                tracks = tracks_data.get('items', []) if tracks_data else []
                                print(f"DEBUG: spotipy_handling.py - Retry found {len(tracks)} tracks")
                                
                                # Cache the tracks if retry was successful
                                if tracks:
                                    # Convert to JSON string to avoid JavaScript conversion issues
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
            
            # If still no tracks after retry, try to play the album directly
            if not tracks:
                print("DEBUG: spotipy_handling.py - No tracks found after retry, trying to play album directly")
                # Check if we have any cached tracks for this album that we can use
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
                                    # Select a random track from cached tracks
                                    track = random.choice(tracks)
                                    track_name = track.get('name', 'Unknown Track')
                                    artist_name = track.get('artists', [{}])[0].get('name', 'Unknown Artist') if track.get('artists') else 'Unknown Artist'
                                    
                                                                        # Play the track
                                    track_uri = track.get('uri', '')
                                    if track_uri:
                                        # Calculate random position from start to 30 seconds before end
                                        duration_ms = track.get('duration_ms', 0)
                                        max_position = max(0, duration_ms - 30000)  # 30 seconds before end
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
                
                # If no cached tracks, fall back to playing album directly
                try:
                    # Try to play the album directly using the album URI
                    album_uri = f"spotify:album:{album_id}"
                    print(f"DEBUG: spotipy_handling.py - Attempting to play album directly: {album_uri}")
                    
                    # Use the play_track_via_backend function to play the album
                    print("DEBUG: spotipy_handling.py - About to call play_track_via_backend for album")
                    play_result = await play_track_via_backend(album_uri, 0)
                    print(f"DEBUG: spotipy_handling.py - play_track_via_backend result: {play_result}")
                    if play_result:
                        print("DEBUG: spotipy_handling.py - Successfully started playing album")
                        # Try to get album info from the album_id
                        album_name = "Album Playing"
                        artist_name = "Random Track"
                        
                        # Extract album name from the album_id if possible
                        # For now, we'll use a more descriptive message
                        song_info_updater_callback(f"Playing Album", f"Random Track (Limited Info)", False)
                        return
                    else:
                        print("DEBUG: spotipy_handling.py - Failed to play album directly")
                        song_info_updater_callback("Album Unavailable", "Try Another Album", False)
                        return
                except Exception as e:
                    print(f"DEBUG: spotipy_handling.py - Error playing album directly: {e}")
                    print("DEBUG: spotipy_handling.py - Providing fallback song info")
                    song_info_updater_callback("Album Loading...", "Please Wait", False)
                return
        
        # Ensure proper randomization
        import random
        import time
        # Use current time to seed random for better randomization
        random.seed(time.time())
        
        # Select a random track
        track = random.choice(tracks)
        chosen_track_uri = track['uri']
        track_name = track.get('name', 'Unknown Track')
        track_artist = track.get('artists', [{}])[0].get('name', 'Unknown Artist')
        

        
        # Calculate random position from start to 30 seconds before end
        duration_ms = track.get('duration_ms', 0)
        max_position = max(0, duration_ms - 30000)  # 30 seconds before end
        position_ms = random.randint(0, max_position)
        is_easter_egg_track_selected = (chosen_track_uri == EASTER_EGG_TRACK_URI)
        
        print(f"DEBUG: spotipy_handling.py - Playing: {track_name} by {track_artist} at {position_ms}ms")
        print(f"DEBUG: spotipy_handling.py - Track URI: {chosen_track_uri}")
        print(f"DEBUG: spotipy_handling.py - Easter egg URI: {EASTER_EGG_TRACK_URI}")
        print(f"DEBUG: spotipy_handling.py - Is easter egg track: {is_easter_egg_track_selected}")
        
        # Use async approach for playing track
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
    print("DEBUG: spotipy_handling.py - safe_pause_playback called")
    
    if not is_pyodide():
        print("DEBUG: spotipy_handling.py - Not in browser environment, skipping pause")
    return True
    
    try:
        import js
        
        # Use JavaScript to call the pause endpoint
        js_code = f'''
        console.log("JS: Pausing music via safe_pause_playback");
        fetch("{BACKEND_URL}/pause", {{
            method: "POST",
            headers: {{
                "Content-Type": "application/json"
            }},
            credentials: "include"
        }})
        .then(response => {{
            console.log("JS: Safe pause request sent");
            window.safe_pause_result = {{ status: response.status }};
        }})
        .catch(error => {{
            console.log("JS: Safe pause request failed:", error);
            window.safe_pause_result = {{ status: 500, error: error.toString() }};
        }});
        '''
        
        js.eval(js_code)
        
        # Wait a bit for the request to complete
        import asyncio
        await asyncio.sleep(0.1)
        
        # Check if the pause was successful
        if hasattr(js.window, 'safe_pause_result'):
            result = js.window.safe_pause_result
            if isinstance(result, dict) and result.get('status') == 200:
                print("DEBUG: spotipy_handling.py - Music paused successfully")
                return True
            else:
                print(f"DEBUG: spotipy_handling.py - Pause failed with status: {result}")
                return False
        else:
            print("DEBUG: spotipy_handling.py - No pause result available")
            return False
            
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

async def show_loading_screen(screen, message="Searching for albums...", duration=3.0):
    """Shows a loading screen with animated dots for a specified duration."""
    print(f"DEBUG: spotipy_handling.py - show_loading_screen called: {message}")
    
    loading_font = pygame.font.SysFont("Press Start 2P", 25)
    dots_font = pygame.font.SysFont("Press Start 2P", 30)
    
    start_time = time.monotonic()
    dots = ""
    dot_timer = 0
    
    while time.monotonic() - start_time < duration:
        current_time = time.monotonic()
        
        # Update dots animation
        dot_timer += 16  # Approximately 60 FPS
        if dot_timer >= 500:  # Change dots every 500ms
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
                print("DEBUG: spotipy_handling.py - QUIT event during loading screen")
                return "QUIT"
        
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill((30, 30, 30))
        
        # Draw loading message
        loading_text = loading_font.render(message, True, WHITE)
        loading_rect = loading_text.get_rect(center=(width // 2, height // 2 - 30))
        screen.blit(loading_text, loading_rect)
        
        # Draw animated dots
        dots_text = dots_font.render(dots, True, LIGHT_BLUE)
        dots_rect = dots_text.get_rect(center=(width // 2, height // 2 + 10))
        screen.blit(dots_text, dots_rect)
        
        # No progress bar - just simple loading with dots
        
        pygame.display.flip()
        await asyncio.sleep(0.016)  # ~60 FPS
    
    print("DEBUG: spotipy_handling.py - Loading screen completed")

async def show_inline_loading(screen, message="Loading...", duration=2.0):
    """Shows a simple loading message below the search bar."""
    print(f"DEBUG: spotipy_handling.py - show_inline_loading called: {message}")
    
    loading_font = pygame.font.SysFont("Press Start 2P", 16)
    
    start_time = time.monotonic()
    
    while time.monotonic() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("DEBUG: spotipy_handling.py - QUIT event during inline loading")
                return "QUIT"
        
        # Don't redraw the background or UI - just add the loading text
        # The existing search UI should remain visible
        
        # Just draw the loading message below the search area
        loading_text = loading_font.render(message, True, WHITE)
        loading_rect = loading_text.get_rect(center=(width // 2, 170))
        screen.blit(loading_text, loading_rect)
        
        pygame.display.flip()
        await asyncio.sleep(0.016)  # ~60 FPS
    
    print("DEBUG: spotipy_handling.py - Inline loading completed")

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
    
    # Clear search music when album is selected
    def clear_search_music():
        """Clear search background music when transitioning to game"""
        print("DEBUG: spotipy_handling.py - Clearing search background music")
        try:
            # This will be called when an album is selected
            pass  # The pause will happen in snake_logic.py
        except Exception as e:
            print(f"DEBUG: spotipy_handling.py - Error clearing search music: {e}")

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
    
    # Cursor variables
    cursor_visible = True
    cursor_timer = 0
    cursor_blink_rate = 500  # milliseconds
    
    # Loading state variable
    is_searching = False

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
            
    async def draw_search_results_local():
        nonlocal album_covers
        
        # Show loading message if searching
        if is_searching:
            print(f"DEBUG: spotipy_handling.py - Displaying loading message")
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

                # Download cover on-demand if needed
                if album['image_url'] and album['uri'] not in album_covers:
                    try:
                        print(f"DEBUG: spotipy_handling.py - Downloading cover on-demand for {album['name']}")
                        # Download the real cover directly instead of creating visual cover first
                        real_cover = await download_and_resize_album_cover_async(album['image_url'], 50, 50)
                        if real_cover:
                            album_covers[album['uri']] = real_cover
                            print(f"DEBUG: spotipy_handling.py - Downloaded real cover for {album['name']}")
                        else:
                            print(f"DEBUG: spotipy_handling.py - Failed to download real cover for {album['name']}, using fallback")
                            album_covers[album['uri']] = create_fallback_album_cover(50, 50)
                    except Exception as e:
                        print(f"DEBUG: spotipy_handling.py - Exception in on-demand download: {e}")
                        album_covers[album['uri']] = create_fallback_album_cover(50, 50)

                # Draw the cover
                if album['uri'] in album_covers and album_covers[album['uri']]:
                    cover = album_covers[album['uri']]
                    # Add a background rectangle to make the cover more visible
                    cover_rect = pygame.Rect(result_rect.x + 10, result_rect.y + 10, 60, 60)
                    pygame.draw.rect(screen, (100, 100, 100), cover_rect)  # Gray background
                    # Scale the cover to be larger and more visible
                    scaled_cover = pygame.transform.scale(cover, (60, 60))
                    screen.blit(scaled_cover, (result_rect.x + 10, result_rect.y + 10))
                    text_start_x = result_rect.x + 80
                else:
                    # Create a fallback cover for albums without images
                    fallback_cover = create_fallback_album_cover(50, 50)
                    album_covers[album['uri']] = fallback_cover
                    # Draw the fallback cover
                    cover_rect = pygame.Rect(result_rect.x + 10, result_rect.y + 10, 60, 60)
                    pygame.draw.rect(screen, (100, 100, 100), cover_rect)  # Gray background
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
                            
                            # Set loading state and search
                            is_searching = True
                            print("DEBUG: spotipy_handling.py - Loading state set to True")
                            
                            # Force a UI update to show loading message
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
                            
                            # Small delay to make loading message visible
                            await asyncio.sleep(0.3)
                            
                            # Use backend search
                            search_results = []
                            backend_results = await search_album_via_backend(text)
                            
                            if backend_results and 'albums' in backend_results and 'items' in backend_results['albums']:
                                albums_found = len(backend_results['albums']['items'])
                                # Limit to only the first 5 albums
                                albums_to_process = backend_results['albums']['items'][:5]
                                for album in albums_to_process:
                                    album_data = {
                                        'name': album.get('name', 'Unknown Album'),
                                        'uri': album.get('uri', ''),
                                        'image_url': album.get('images', [{}])[0].get('url', None) if album.get('images') else None,
                                        'artist': album.get('artists', [{}])[0].get('name', 'Unknown Artist') if album.get('artists') else 'Unknown Artist'
                                    }
                                    search_results.append(album_data)
                                print(f"DEBUG: spotipy_handling.py - Found {albums_found} albums, displaying top 5")
                                # Clear any old covers - we'll download them on-demand in the drawing function
                                album_covers.clear()
                                
                                # Clear loading state after search completes - covers will download on-demand
                                is_searching = False
                                print("DEBUG: spotipy_handling.py - Loading state set to False (search complete)")
                            else:
                                print(f"DEBUG: spotipy_handling.py - No albums found in search results")
                                # Create a fallback result if search fails
                                search_results = [
                                    {
                                        'name': 'Search Failed - Try Again',
                                        'uri': 'spotify:album:fallback',
                                        'image_url': 'https://example.com/fallback.jpg',
                                        'artist': 'Unknown Artist'
                                    }
                                ]
                                album_covers.clear()
                                
                                # Clear loading state after everything is complete
                                is_searching = False
                                print("DEBUG: spotipy_handling.py - Loading state set to False (no results)")
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
        
        # Draw blinking cursor when input is active
        if active and cursor_visible:
            # Calculate cursor position based on text width
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
        # Update cursor blinking
        cursor_timer += 16  # Approximately 60 FPS
        if cursor_timer >= cursor_blink_rate:
            cursor_visible = not cursor_visible
            cursor_timer = 0
        
        pygame.display.flip()
        await asyncio.sleep(0.01)
    print("DEBUG: spotipy_handling.py - get_album_search_input called (END, should never reach here)")

# Browser-safe: play track via backend
async def play_track_via_backend(uri, position_ms=0):
    # Check if we're in a browser environment
    if not is_pyodide():
        print("DEBUG: spotipy_handling.py - Not in browser environment, skipping play_track_via_backend")
        return False
    
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
        await asyncio.sleep(0.05)  # Reduced from 0.1 to 0.05 seconds
        
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
    # Check if we're in a browser environment
    if not is_pyodide():
        print("DEBUG: spotipy_handling.py - Not in browser environment, using desktop fallback for search")
        # For desktop, return a mock search result
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
        
        # Wait for the search result
        max_attempts = 10
        for attempt in range(max_attempts):
            if hasattr(js.window, 'search_result'):
                result = js.window.search_result
                if result is not None:
                    break
            await asyncio.sleep(0.1)
        
        if hasattr(js.window, 'search_result'):
            result = js.window.search_result
        
        # Handle different result types
        if isinstance(result, dict):
            status = result.get('status', 500)
            if status == 200:
                try:
                    search_data = json.loads(result.get('text', '{}'))
                    return search_data
                except json.JSONDecodeError as e:
                    print(f"DEBUG: spotipy_handling.py - JSON decode error: {e}")
                    return None
            else:
                print(f"DEBUG: spotipy_handling.py - Search failed with status: {status}")
                return None
        elif isinstance(result, str):
            # If it's a string, try to parse it as JSON
            try:
                search_data = json.loads(result)
                return search_data
            except json.JSONDecodeError as e:
                print(f"DEBUG: spotipy_handling.py - JSON decode error from string: {e}")
                return None
        else:
            # If it's an object, try to access properties directly
            try:
                status = getattr(result, 'status', 500)
                if status == 200:
                    text = getattr(result, 'text', '{}')
                    search_data = json.loads(text)
                    return search_data
                else:
                    print(f"DEBUG: spotipy_handling.py - Search failed with status: {status}")
                    return None
            except Exception as e:
                print(f"DEBUG: spotipy_handling.py - Error accessing object properties: {e}")
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
async def verify_album_playability(album_uri):
    """Verify that an album is playable by testing access to its tracks"""
    print(f"DEBUG: spotipy_handling.py - verify_album_playability called with: {album_uri}")
    
    # Extract album ID from URI
    if album_uri.startswith('spotify:album:'):
        album_id = album_uri.replace('spotify:album:', '')
    else:
        album_id = album_uri
    
    print(f"DEBUG: spotipy_handling.py - Testing playability for album ID: {album_id}")
    
    # Test if we can get album tracks with retry mechanism
    max_retries = 3
    for attempt in range(max_retries):
        print(f"DEBUG: spotipy_handling.py - Album tracks attempt {attempt + 1}/{max_retries}")
        
        tracks_data = await get_album_tracks_via_backend(album_id)
        
        if tracks_data and 'items' in tracks_data:
            tracks = tracks_data.get('items', [])
            if tracks:
                print(f"DEBUG: spotipy_handling.py - Album {album_id} verified playable with {len(tracks)} tracks")
                return True
            else:
                print(f"DEBUG: spotipy_handling.py - Album {album_id} has no tracks")
                return False
        else:
            print(f"DEBUG: spotipy_handling.py - Album {album_id} attempt {attempt + 1} failed, tracks_data: {tracks_data}")
            
            if attempt < max_retries - 1:
                # Wait with exponential backoff before retry
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                print(f"DEBUG: spotipy_handling.py - Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
            else:
                print(f"DEBUG: spotipy_handling.py - Album {album_id} failed all {max_retries} attempts")
                return False
    
    return False

async def get_album_tracks_via_backend(album_id):
    import js
    import json
    url = f"{BACKEND_URL}/album_tracks?album_id={album_id}"
    
    js_code = f'''
    console.log("JS: Fetching album tracks for album_id:", "{album_id}");
    console.log("JS: Full URL:", "{url}");
    
    fetch("{url}", {{
        method: "GET",
        credentials: "include",
        headers: {{
            "Accept": "application/json",
            "Content-Type": "application/json"
        }}
    }})
    .then(response => {{
        console.log("JS: Album tracks response status:", response.status);
        console.log("JS: Album tracks response ok:", response.ok);
        return response.text();
    }})
    .then(text => {{
        console.log("JS: Album tracks response text (first 200 chars):", text.substring(0, 200));
        if (text.trim().startsWith('{{')) {{
            // Looks like JSON, parse it to check status
            try {{
                const data = JSON.parse(text);
                console.log("JS: Parsed JSON status:", data.status || 'no status');
                window.album_tracks_result = {{ status: data.status || 200, text: text }};
            }} catch(e) {{
                console.log("JS: JSON parse error:", e);
                window.album_tracks_result = {{ status: 500, text: text }};
            }}
        }} else {{
            console.log("JS: Response doesn't look like JSON");
            window.album_tracks_result = {{ status: 500, text: text }};
        }}
    }})
    .catch(error => {{
        console.log("JS: Album tracks fetch error:", error);
        window.album_tracks_result = {{ status: 500, error: error.toString() }};
    }});
    '''
    
    try:
        js.eval(js_code)
        import asyncio
        
        # Wait longer for the fetch to complete, especially on first call
        await asyncio.sleep(0.5)
        
        # Check multiple times for the result
        max_checks = 3
        for check in range(max_checks):
            if hasattr(js.window, 'album_tracks_result'):
                result = js.window.album_tracks_result
                print(f"DEBUG: spotipy_handling.py - Album tracks result (check {check + 1}): {result}")
                
                # Handle both object and string cases
                if isinstance(result, dict):
                    if result.get('status') == 200:
                        try:
                            return json.loads(result.get('text', '{}'))
                        except json.JSONDecodeError as e:
                            print(f"DEBUG: spotipy_handling.py - JSON decode error: {e}")
                            return None
                elif isinstance(result, str):
                    # If it's a string, try to parse it as JSON
                    try:
                        parsed_result = json.loads(result)
                        return parsed_result
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: spotipy_handling.py - String JSON decode error: {e}")
                        return None
                else:
                    # If it's an object, try to access properties directly
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
    """Convert base64 image data directly to a pygame surface without using pygame.image.load()"""
    try:
        import base64
        import struct
        
        # Decode base64 data
        image_data = base64.b64decode(base64_data)
        
        # Create a colored surface based on the image data hash
        # This is a workaround since pygame.image.load() doesn't work in browser
        import hashlib
        hash_value = hashlib.md5(image_data).hexdigest()
        
        # Create a surface
        surface = pygame.Surface((target_width, target_height))
        
        # Generate base colors from the hash
        r_base = int(hash_value[0:2], 16)
        g_base = int(hash_value[2:4], 16)
        b_base = int(hash_value[4:6], 16)
        
        # Ensure minimum brightness
        r_base = max(r_base, 50)
        g_base = max(g_base, 50)
        b_base = max(b_base, 50)
        
        # Create a more vibrant pattern
        for y in range(target_height):
            for x in range(target_width):
                # Create a gradient pattern
                progress_x = x / target_width
                progress_y = y / target_height
                
                # Generate colors with more variation
                r = int((r_base + progress_x * 100 + progress_y * 50) % 256)
                g = int((g_base + progress_y * 100 + progress_x * 50) % 256)
                b = int((b_base + (progress_x + progress_y) * 75) % 256)
                
                # Ensure minimum brightness
                r = max(r, 30)
                g = max(g, 30)
                b = max(b, 30)
                
                surface.set_at((x, y), (r, g, b))
        
        # Add a colored border based on the hash
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
    """Convert base64 data to pygame surface specifically for pygbag/browser environment"""
    try:
        import base64
        
        # Decode base64 data
        image_data = base64.b64decode(base64_data)
        
        # Since pygame.image.load() doesn't work in browser, we'll create a surface
        # and manually set pixels based on the image data
        surface = pygame.Surface((target_width, target_height))
        
        # Use JavaScript to get pixel data from the image
        js_code = f'''
        try {{
            // Create a canvas element
            const canvas = document.createElement('canvas');
            canvas.width = {target_width};
            canvas.height = {target_height};
            const ctx = canvas.getContext('2d');
            
            // Create an image element
            const img = new Image();
            img.crossOrigin = "anonymous";
            
            img.onload = function() {{
                // Draw the image on the canvas, scaled to fit
                ctx.drawImage(img, 0, 0, {target_width}, {target_height});
                
                // Get the pixel data
                const imageData = ctx.getImageData(0, 0, {target_width}, {target_height});
                window.album_cover_pixels = imageData.data;
                window.album_cover_loaded = true;
                console.log("Album cover pixels extracted successfully");
            }};
            
            img.onerror = function() {{
                console.log("Failed to load album cover image");
                window.album_cover_loaded = false;
            }};
            
            // Set the base64 data as src
            img.src = "data:image/jpeg;base64,{base64_data}";
            
        }} catch(e) {{
            console.log("Error creating canvas:", e);
            window.album_cover_loaded = false;
        }}
        '''
        
        import js
        js.eval(js_code)
        
        # Wait for the image to load and be drawn to canvas
        import asyncio
        await asyncio.sleep(0.3)
        
        # Check if the image was loaded successfully
        if hasattr(js.window, 'album_cover_loaded') and js.window.album_cover_loaded:
            print(f"DEBUG: spotipy_handling.py - Real album cover loaded and drawn to canvas")
            
            # Get the pixel data from JavaScript
            if hasattr(js.window, 'album_cover_pixels'):
                pixels = js.window.album_cover_pixels
                
                # Convert JavaScript array to Python and set pixels
                for y in range(target_height):
                    for x in range(target_width):
                        idx = (y * target_width + x) * 4  # RGBA format
                        r = int(pixels[idx])
                        g = int(pixels[idx + 1])
                        b = int(pixels[idx + 2])
                        a = int(pixels[idx + 3])
                        surface.set_at((x, y), (r, g, b, a))
                
                print(f"DEBUG: spotipy_handling.py - Real album cover surface created: {surface.get_size()}")
                return surface
            else:
                print(f"DEBUG: spotipy_handling.py - No pixel data found, using visual representation")
                return create_visual_album_cover_from_data(image_data, target_width, target_height)
        else:
            print(f"DEBUG: spotipy_handling.py - Failed to load real album cover, using visual representation")
            return create_visual_album_cover_from_data(image_data, target_width, target_height)
            
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Error creating pygame surface from base64: {e}")
        return create_visual_album_cover_from_data(image_data, target_width, target_height)

def setup_page_unload_handler():
    """Set up event listeners to pause music when user leaves the page."""
    if not is_pyodide():
        print("DEBUG: spotipy_handling.py - Not in browser environment, skipping page unload handler")
        return
    
    try:
        import js
        
        # More robust JavaScript code using synchronous XMLHttpRequest for unload events
        js_code = f'''
        console.log("JS: Setting up page unload handlers for music pause");
        
        // Function to pause music via backend using multiple methods for unload events
        window.pauseMusicOnUnload = function() {{
            console.log("JS: Page unload detected, pausing music");
            
            // Method 1: Use navigator.sendBeacon (most reliable for unload events)
            if (navigator.sendBeacon) {{
                try {{
                    var data = new Blob(['{{}}'], {{type: 'application/json'}});
                    var success = navigator.sendBeacon('{BACKEND_URL}/pause', data);
                    console.log("JS: sendBeacon pause request sent, success:", success);
                }} catch (error) {{
                    console.log("JS: sendBeacon pause request failed:", error);
                }}
            }}
            
            // Method 2: Use synchronous XMLHttpRequest as fallback
            try {{
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '{BACKEND_URL}/pause', false); // Synchronous
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.withCredentials = true;
                xhr.send();
                console.log("JS: Synchronous pause request sent, status:", xhr.status);
            }} catch (error) {{
                console.log("JS: Synchronous pause request failed:", error);
            }}
        }};
        
        // Function for visibility change (can use async fetch)
        window.pauseMusicOnVisibilityChange = function() {{
            console.log("JS: Page visibility changed, pausing music");
            fetch('{BACKEND_URL}/pause', {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json"
                }},
                credentials: "include"
            }})
            .then(response => {{
                console.log("JS: Visibility change pause request sent");
            }})
            .catch(error => {{
                console.log("JS: Visibility change pause request failed:", error);
            }});
        }};
        
        // Set up event listeners for different scenarios
        window.addEventListener('beforeunload', window.pauseMusicOnUnload);
        window.addEventListener('unload', window.pauseMusicOnUnload);
        window.addEventListener('pagehide', window.pauseMusicOnUnload);
        
        // For mobile browsers and PWA scenarios
        document.addEventListener('visibilitychange', function() {{
            if (document.visibilityState === 'hidden') {{
                console.log("JS: Page hidden, pausing music");
                window.pauseMusicOnVisibilityChange();
            }}
        }});
        
        // Also try to pause when the window loses focus
        window.addEventListener('blur', function() {{
            console.log("JS: Window lost focus, pausing music");
            window.pauseMusicOnVisibilityChange();
        }});
        
        console.log("JS: Page unload handlers set up successfully");
        
        // Set up a heartbeat to detect if the page is still active
        window.pageActiveHeartbeat = Date.now();
        setInterval(function() {{
            window.pageActiveHeartbeat = Date.now();
        }}, 1000);
        
        // Check if page is still active every 5 seconds
        setInterval(function() {{
            var timeSinceLastHeartbeat = Date.now() - window.pageActiveHeartbeat;
            if (timeSinceLastHeartbeat > 10000) {{ // More than 10 seconds since last heartbeat
                console.log("JS: Page appears to be inactive, pausing music");
                window.pauseMusicOnVisibilityChange();
            }}
        }}, 5000);
        
        // Add a test function that can be called manually
        window.testPauseMusic = function() {{
            console.log("JS: Manual test of pause music function");
            window.pauseMusicOnVisibilityChange();
        }};
        
        console.log("JS: Test function available: window.testPauseMusic()");
        '''
        
        js.eval(js_code)
        print("DEBUG: spotipy_handling.py - Page unload handlers set up successfully")
        
    except Exception as e:
        print(f"DEBUG: spotipy_handling.py - Failed to set up page unload handlers: {e}")
        import traceback
        traceback.print_exc()