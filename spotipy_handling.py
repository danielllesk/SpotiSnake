import pygame
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from shared_constants import *
import requests
from io import BytesIO
import random
import time
from concurrent.futures import ThreadPoolExecutor

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
executor = ThreadPoolExecutor(max_workers=1)

def get_spotify_device(spotify_instance):
    global cached_device_id
    if cached_device_id is None:
        try:
            devices = spotify_instance.devices()
            if not devices or not devices['devices']:
                print("No Spotify devices found. Please open Spotify on your device.")
                return None
            cached_device_id = devices['devices'][0]['id']
            print("Successfully connected to Spotify device!")
        except Exception as e:
            print(f"Error getting Spotify device: {e}")
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
    login_text = "Login with Spotify"
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
                    try:
                        sp = authenticate_spotify()
                        if sp:
                            return sp
                        else:
                            error_message = "Login failed. Please ensure Spotify is open and try again."
                            error_timer = time.time()
                    except Exception as e:
                        error_message = "Login failed. Please try again."
                        error_timer = time.time()
                        print(f"Login error: {e}")
                    finally:
                        is_authenticating = False

        screen.fill(DARK_GREY)
        
        # Draw title with larger font
        title = title_font.render("Welcome to SpotiSnake!", True, LIGHT_BLUE)
        screen.blit(title, (width//2 - title.get_width()//2, height//4))
        
        # Draw login button
        if is_authenticating:
            button_color = DARK_BLUE
            login_text = "Logging in..."
        else:
            button_color = LIGHT_BLUE
            login_text = "Login with Spotify"
            
        pygame.draw.rect(screen, button_color, login_button)
        text_surf = font.render(login_text, True, BLACK)
        text_rect = text_surf.get_rect(center=login_button.center)
        screen.blit(text_surf, text_rect)
        
        # Draw instructions
        instructions = [
            "Click to login with Spotify",
            "Spotify Browser will open for log-in",
            "Return to this window after log-in confirmed",
            "NOTE: you need a Spotify Premium account to play music"
        ]
        y_offset = height//2 + 50
        for instruction in instructions:
            text = font.render(instruction, True, WHITE)
            screen.blit(text, (width//2 - text.get_width()//2, y_offset))
            y_offset += 60
            
        # Draw error message if any
        if error_message and time.time() - error_timer < 3:
            error_surf = font.render(error_message, True, (255, 0, 0))
            screen.blit(error_surf, (width//2 - error_surf.get_width()//2, height//2 + 150))

        pygame.display.flip()
        clock.tick(30)

def play_track_sync(track_uri, position_ms):
    """Synchronous function to play a track"""
    global sp, cached_device_id
    try:
        sp.start_playback(
            device_id=cached_device_id,
            uris=[track_uri],
            position_ms=position_ms
        )
        return True
    except Exception as e:
        print(f"Error in playback: {e}")
        return False

def play_specific_track(track_uri):
    """Plays a specific track URI from the beginning."""
    global sp, cached_device_id, executor
    if not sp or not cached_device_id:
        print("Spotify not ready or no device for specific track.")
        return False
    try:
        # Use the executor to run the playback in a separate thread
        future = executor.submit(play_track_sync, track_uri, 0) # Play from position 0
        print(f"Attempting to play specific Easter Egg track: {track_uri}")
        # We could add future.add_done_callback(handle_future_result) if needed
        return True
    except Exception as e:
        print(f"Error submitting specific track {track_uri} for playback: {e}")
        return False

def play_random_track_from_album(album_uri):
    """Plays a random track from the album and returns if it was the Easter Egg track."""
    global sp # Ensure sp is accessible
    try:
        # Get tracks and select a random one in a single API call
        results = sp.album_tracks(album_uri, limit=50)
        tracks = results['items']
        
        if not tracks:
            return False, False # Did not play, not Easter Egg
            
        # Select a random track
        track = random.choice(tracks)
        track_uri = track['uri']
        
        # Calculate random position
        position_ms = random.randint(0, max(0, track['duration_ms'] - 30000))
        
        # Use the executor to run the playback in a separate thread
        future = executor.submit(play_track_sync, track_uri, position_ms)
        
        is_easter_egg_track_selected = (track_uri == EASTER_EGG_TRACK_URI)
        if is_easter_egg_track_selected:
            print(f"Randomly selected track is the Easter Egg track: {track_uri}")
            
        # future.add_done_callback(some_callback_if_needed) # Optional: if you need to know when it finishes/fails
        return True, is_easter_egg_track_selected # Played successfully, and whether it was the EE track
            
    except Exception as e:
        print(f"Error playing random track from album {album_uri}: {e}")
        return False, False # Did not play, not Easter Egg

# Cleanup function
def cleanup():
    try:
        if sp:
            sp.pause_playback()
        if executor:
            executor.shutdown(wait=False)
    except:
        pass

# Add cleanup to pygame quit
pygame.quit = cleanup

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
        response = requests.get(url, verify=False) # Consider removing verify=False for security if possible
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
