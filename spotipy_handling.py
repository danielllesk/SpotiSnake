import pygame
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from shared_constants import *
import requests
from io import BytesIO
import random
import time
import asyncio

clock = pygame.time.Clock()
pygame.init()

# Define the required scopes for playback
SCOPES = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-email",
    "user-read-private"
]

# Global variables
sp = None
cached_device_id = None

EASTER_EGG_TRACK_URI = "spotify:track:4UQMOPSUVJVicIQzjAcRRZ"

def get_spotify_device(spotify_instance):
    global cached_device_id
    # Check cache first
    if cached_device_id:
        # Optional: Add a periodic check here if devices change frequently or if playback fails
        # For now, assume cached_device_id is valid if present
        pass # Keep using cached_device_id
    else: # No cached ID, or it was cleared
        try:
            if not spotify_instance:
                print("Spotify instance not available to fetch devices.")
                return None
            devices = spotify_instance.devices()
            if not devices or not devices['devices']:
                print("No Spotify devices found. Please open Spotify on your device.")
                cached_device_id = None # Ensure it's None if no devices
                return None
            # Prefer active device, otherwise take the first one
            active_device = next((d for d in devices['devices'] if d.get('is_active')), None)
            if active_device:
                cached_device_id = active_device['id']
                print(f"Using active Spotify device: {active_device['name']}")
            else:
                cached_device_id = devices['devices'][0]['id']
                print(f"No active device. Using first available: {devices['devices'][0]['name']}")
        except Exception as e:
            print(f"Error getting Spotify device: {e}")
            cached_device_id = None # Ensure it's None on error
            return None
    return cached_device_id

def authenticate_spotify():
    try:
        # Using the SpotiSnake app credentials
        auth_manager = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=" ".join(SCOPES),
            open_browser=True,
            cache_handler=None
        )
        
        # Create Spotify instance
        spotify_instance = spotipy.Spotify(auth_manager=auth_manager)
        
        # Test the connection
        user = spotify_instance.current_user()
        print(f"Successfully connected to Spotify as {user['display_name']}!")
        
        # Get the device ID right after authentication
        if get_spotify_device(spotify_instance) is None:
            print("Failed to find a valid Spotify device. Please open Spotify and try again.")
            return None
            
        return spotify_instance
    except Exception as e:
        print(f"Authentication error: {e}")
        return None

def show_login_screen(screen, font):
    global sp
    login_button = pygame.Rect(width//2 - 150, height//2 - 25, 300, 50)
    login_text_default = "Login with Spotify"
    current_login_text = login_text_default
    error_message = None
    error_timer = 0
    is_authenticating = False
    
    # Create a larger font for the title
    title_font = pygame.font.SysFont("Press Start 2P", 55)
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                if login_button.collidepoint(event.pos) and not is_authenticating:
                    is_authenticating = True
                    current_login_text = "Logging in..."
                    # Force screen update for "Logging in..." message before blocking auth call
                    # (This part might be tricky without async here, auth can block)
                    pygame.draw.rect(screen, DARK_BLUE, login_button)
                    text_surf_auth = font.render(current_login_text, True, BLACK)
                    text_rect_auth = text_surf_auth.get_rect(center=login_button.center)
                    screen.blit(text_surf_auth, text_rect_auth)
                    pygame.display.flip()

                    try:
                        sp = authenticate_spotify()
                        if sp:
                            return sp
                        else:
                            error_message = "Login failed. Ensure Spotify is open & Premium."
                            error_timer = time.time()
                    except Exception as e:
                        error_message = "Login error. Try again."
                        error_timer = time.time()
                        print(f"Login error during auth: {e}")
                    finally:
                        is_authenticating = False
                        current_login_text = login_text_default # Reset button text

        screen.fill(DARK_GREY)
        
        # Draw title with larger font
        title = title_font.render("Welcome to SpotiSnake!", True, LIGHT_BLUE)
        screen.blit(title, (width//2 - title.get_width()//2, height//4))
        
        # Draw login button
        if is_authenticating:
            button_color = DARK_BLUE
        else:
            button_color = LIGHT_BLUE
            
        pygame.draw.rect(screen, button_color, login_button)
        text_surf = font.render(current_login_text, True, BLACK)
        text_rect = text_surf.get_rect(center=login_button.center)
        screen.blit(text_surf, text_rect)
        
        # Draw instructions
        instructions = [
            "Click to login with Spotify",
            "Browser will open for log-in",
            "Return here after log-in",
            "NOTE: Spotify Premium needed"
        ]
        y_offset = height//2 + 50
        small_font = pygame.font.SysFont("Press Start 2P", 20) # Smaller font for instructions
        for instruction in instructions:
            text = small_font.render(instruction, True, WHITE)
            screen.blit(text, (width//2 - text.get_width()//2, y_offset))
            y_offset += 40 # Adjusted spacing
            
        if error_message and time.time() - error_timer < 5: # Show error longer
            error_surf = small_font.render(error_message, True, RED)
            screen.blit(error_surf, (width//2 - error_surf.get_width()//2, height - 50)) # Error at bottom

        pygame.display.flip()
        clock.tick(30)

def play_track_sync(track_uri, position_ms):
    """Synchronous function to play a track. Returns success_bool."""
    global sp, cached_device_id
    sync_start_time = time.perf_counter()
    print(f"[{sync_start_time:.4f}] play_track_sync: Called for {track_uri}")

    if not sp:
        print(f"[{time.perf_counter():.4f}] play_track_sync: Spotify not initialized.")
        return False
    
    device_fetch_start = time.perf_counter()
    device_to_use = get_spotify_device(sp) 
    device_fetch_end = time.perf_counter()
    print(f"[{device_fetch_end:.4f}] play_track_sync: get_spotify_device took {device_fetch_end - device_fetch_start:.4f}s. Device: {device_to_use}")

    if not device_to_use:
        print(f"[{time.perf_counter():.4f}] play_track_sync: No Spotify device available.")
        return False

    try:
        print(f"[{time.perf_counter():.4f}] play_track_sync: Attempting sp.start_playback for {track_uri}...")
        playback_call_start = time.perf_counter()
        sp.start_playback(
            device_id=device_to_use,
            uris=[track_uri],
            position_ms=position_ms
        )
        playback_call_end = time.perf_counter()
        print(f"[{playback_call_end:.4f}] play_track_sync: sp.start_playback for {track_uri} took {playback_call_end - playback_call_start:.4f}s. Success.")
        return True
    except spotipy.exceptions.SpotifyException as e:
        print(f"[{time.perf_counter():.4f}] play_track_sync: Spotify API error: {e.status_code} - {e.msg} for URI {track_uri}")
        if e.status_code == 403 or e.status_code == 404: 
            cached_device_id = None 
            print(f"[{time.perf_counter():.4f}] play_track_sync: Cleared cached_device_id.")
        return False
    except Exception as e:
        print(f"[{time.perf_counter():.4f}] play_track_sync: Generic error for URI {track_uri}: {e}")
        return False
    finally:
        sync_end_time = time.perf_counter()
        print(f"[{sync_end_time:.4f}] play_track_sync: Finished for {track_uri}. Total time: {sync_end_time - sync_start_time:.4f}s")

def play_uri_with_details(track_uri, position_ms=0):
    """Plays a specific URI and returns success, name, artist. Contains blocking calls."""
    global sp
    if not sp:
        return False, "N/A", "Spotify Not Init"
    
    track_name = "Error fetching name"
    track_artist = "Error fetching artist"
    try:
        track_info = sp.track(track_uri)
        track_name = track_info.get('name', 'Unknown Track')
        if track_info.get('artists') and len(track_info['artists']) > 0:
            track_artist = track_info['artists'][0].get('name', 'Unknown Artist')
    except Exception as e:
        print(f"Error fetching track details for {track_uri}: {e}")

    played_successfully = play_track_sync(track_uri, position_ms)
    
    return played_successfully, track_name, track_artist

async def play_random_track_from_album(album_uri, song_info_updater_callback):
    """Plays a random track asynchronously and calls a callback with track details."""
    global sp
    async_overall_start_time = time.perf_counter()
    print(f"[{async_overall_start_time:.4f}] play_random_track_from_album (callback ver): Called for {album_uri}")

    if not sp:
        print(f"[{time.perf_counter():.4f}] play_random_track_from_album: Spotify not initialized.")
        # Call updater with error state if desired, or let caller handle no-op
        # song_info_updater_callback("N/A", "Spotify Not Init", False)
        return # Or return False to indicate immediate failure to initiate
    
    track_name, track_artist, is_easter_egg_track_selected, played_successfully = "Error", "Unknown", False, False

    try:
        print(f"[{time.perf_counter():.4f}] play_random_track_from_album: Calling sp.album_tracks in thread for {album_uri}...")
        album_tracks_thread_start = time.perf_counter()
        # sp.album_tracks is blocking
        results = await asyncio.to_thread(sp.album_tracks, album_uri, limit=50) 
        album_tracks_thread_end = time.perf_counter()
        print(f"[{album_tracks_thread_end:.4f}] play_random_track_from_album: sp.album_tracks in thread took {album_tracks_thread_end - album_tracks_thread_start:.4f}s.")

        tracks = results.get('items')
        if not tracks:
            print(f"[{time.perf_counter():.4f}] play_random_track_from_album: No tracks found in album {album_uri}.")
            track_name, track_artist = "No Tracks In Album", "N/A"
            # Call updater immediately with this info, playback won't happen
            song_info_updater_callback(track_name, track_artist, False)
            return 
        
        track = random.choice(tracks)
        chosen_track_uri = track['uri']
        track_name = track.get('name', 'Unknown Track')
        track_artist_list = track.get('artists')
        if track_artist_list and len(track_artist_list) > 0:
            track_artist = track_artist_list[0].get('name', 'Unknown Artist')
        else:
            track_artist = "Unknown Artist"
        
        position_ms = random.randint(0, max(0, track.get('duration_ms', 0) - 30000))
        is_easter_egg_track_selected = (chosen_track_uri == EASTER_EGG_TRACK_URI)
        
        print(f"[{time.perf_counter():.4f}] play_random_track_from_album: Chosen: {track_name}. Calling play_track_sync in thread...")
        play_sync_thread_start = time.perf_counter()
        # play_track_sync is blocking
        played_successfully = await asyncio.to_thread(play_track_sync, chosen_track_uri, position_ms) 
        play_sync_thread_end = time.perf_counter()
        print(f"[{play_sync_thread_end:.4f}] play_random_track_from_album: play_track_sync in thread took {play_sync_thread_end - play_sync_thread_start:.4f}s. Result: {played_successfully}")
        
        if played_successfully:
            print(f"[{time.perf_counter():.4f}] play_random_track_from_album: Playback successful for {track_name}.")
            if is_easter_egg_track_selected:
                print(f"[{time.perf_counter():.4f}] play_random_track_from_album: Randomly selected track is Easter Egg: {track_name}")
            # Call the updater with the successful track's info
            song_info_updater_callback(track_name, track_artist, is_easter_egg_track_selected)
        else:
            print(f"[{time.perf_counter():.4f}] play_random_track_from_album: Playback FAILED for {track_name}.")
            # Call updater with info about the track that failed to play
            song_info_updater_callback(track_name, f"(Failed: {track_artist})", False) # Mark as failed in artist string

    except Exception as e:
        print(f"[{time.perf_counter():.4f}] play_random_track_from_album: Error for {album_uri}: {e}")
        # On general error, call updater with error state
        song_info_updater_callback("Error During Playback", str(e), False)
    finally:
        async_overall_end_time = time.perf_counter()
        print(f"[{async_overall_end_time:.4f}] play_random_track_from_album (callback ver): Finished for {album_uri}. Total async function time: {async_overall_end_time - async_overall_start_time:.4f}s")

def cleanup():
    global cached_device_id
    print("Running cleanup...")
    try:
        if sp:
            try:
                print("Attempting to pause playback on cleanup...")
                current_playback = sp.current_playback()
                if current_playback and current_playback.get('is_playing'):
                    sp.pause_playback()
                    print("Playback paused.")
                else:
                    print("No active playback to pause or already paused.")
            except Exception as e:
                print(f"Error pausing on cleanup: {e}")
    except Exception as e:
        print(f"Error during sp check in cleanup: {e}")
    finally:
        cached_device_id = None # Clear cached device ID on cleanup
        print("Cleanup finished. Cached device ID cleared.")

def search_album(query):
    global sp
    if not sp:
        print("No Spotify instance available. Please log in first.")
        return []
        
    try:
        print(f"Searching for: {query}")  # Debug print
        results = sp.search(q=query, type='album', limit=5)
        if not results or 'albums' not in results:
            print("No results found")
            return []
        albums = results.get('albums', {}).get('items', [])
        album_info = []
        for album in albums:
            name = album.get('name', 'Unknown Album')
            uri = album.get('uri', '')
            images = album.get('images', [])
            image_url = images[-1]['url'] if images else None
            artists = album.get('artists', [])
            artist_name = artists[0].get('name', 'Unknown Artist') if artists else 'Unknown Artist'
            if uri:
                album_info.append({
                    'name': name,
                    'uri': uri,
                    'image_url': image_url,
                    'artist': artist_name
                })
        print(f"Found {len(album_info)} albums")  # Debug print
        return album_info
    except Exception as e:
        print(f"Error searching for album: {e}")
        return []

def download_and_resize_album_cover(url, target_width, target_height):
    try:
        response = requests.get(url)
        response.raise_for_status()
        img_data = BytesIO(response.content)
        image = pygame.image.load(img_data)
        image = pygame.transform.scale(image, (target_width, target_height))
        return image
    except Exception as e:
        print(f"Error downloading or resizing album art: {e}")
        return None

def get_album_search_input(screen, font):
    global sp
    if not sp:
        print("No Spotify instance available. Please log in first.")
        return None
        
    input_box = pygame.Rect(100, 100, 400, 50)
    results_area = pygame.Rect(100, 160, 400, 300)
    color_inactive = DARK_BLUE
    color_active = LIGHT_BLUE
    color = color_inactive
    active = False
    text = ''
    search_results = []
    album_covers = {}

    def draw_button(text_content, x, y, w, h, inactive_color, active_color): # Renamed text to text_content to avoid conflict
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        button_font = pygame.font.SysFont("Press Start 2P", 25)
        if x < mouse[0] < x + w and y < mouse[1] < y + h:
            pygame.draw.rect(screen, active_color, (x, y, w, h))
            if click[0] == 1:
                return True
        else:
            pygame.draw.rect(screen, inactive_color, (x, y, w, h))
        text_surf = button_font.render(text_content, True, BLACK)
        text_rect = text_surf.get_rect(center=(x + w // 2, y + h // 2))
        screen.blit(text_surf, text_rect)
        return False

    def draw_search_results():
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
                    album_covers[album['uri']] = download_and_resize_album_cover(album['image_url'], 50, 50)
                if album['uri'] in album_covers and album_covers[album['uri']]:
                    screen.blit(album_covers[album['uri']], (result_rect.x + 10, result_rect.y + 10))
                    text_start_x = result_rect.x + 70
                else:
                    text_start_x = result_rect.x + 10
                name_font = pygame.font.SysFont('times new roman', 20)
                name_surf = name_font.render(album['name'], True, BLACK)
                screen.blit(name_surf, (text_start_x, result_rect.y + 10))
                artist_font = pygame.font.SysFont('times new roman', 20)
                artist_surf = artist_font.render(album['artist'], True, DARK_BLUE)
                screen.blit(artist_surf, (text_start_x, result_rect.y + 40))
                y_offset += 80
        else:
            no_results_surf = font.render("No results found, click enter to search", True, WHITE)
            screen.blit(no_results_surf, (results_area.x + 10, results_area.y + 10))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try:
                    if sp:
                        sp.pause_playback()
                except:
                    pass
                pygame.quit()
                return None # Important to return None to signal quit
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                    color = color_active if active else color_inactive
                elif search_results:
                    y_offset = results_area.y + 10
                    for album in search_results:
                        result_rect = pygame.Rect(results_area.x + 5, y_offset, results_area.width - 10, 70)
                        if result_rect.collidepoint(event.pos):
                            return album
                        y_offset += 80
                else:
                    active = False # Deactivate input box if clicked outside
                    color = color_inactive
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        if text:
                            print(f"Searching for: {text}")
                            search_results = search_album(text)
                            album_covers.clear() # Clear old covers
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                        if not text: # Clear results if text is empty
                            search_results = []
                            album_covers.clear()
                    else:
                        text += event.unicode

        screen.fill((30, 30, 30))
        label_font = pygame.font.SysFont("Press Start 2P", 25)
        label = label_font.render("Search for an album:", True, WHITE)
        screen.blit(label, (input_box.x, input_box.y - 30))
        txt_surface = font.render(text, True, color)
        # Adjust input_box width dynamically based on text, but with a minimum
        current_width = max(400, txt_surface.get_width() + 10)
        input_box.w = current_width
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        pygame.draw.rect(screen, color, input_box, 2)
        draw_search_results()
        
        # Draw quit button at bottom left
        # Ensure button_width and button_height are defined or use constants
        # For example:
        button_width_val = 100 
        button_height_val = 50
        quit_button_x = 20
        quit_button_y = height - button_height_val - 20
        if draw_button("Quit", quit_button_x, quit_button_y, button_width_val, button_height_val, LIGHT_BLUE, DARK_BLUE):
            try:
                if sp:
                    sp.pause_playback()
            except:
                pass
            pygame.quit()
            return None # Important to return None to signal quit
            
        pygame.display.flip()
        clock.tick(30)