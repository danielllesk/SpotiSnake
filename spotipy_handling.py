import pygame
import spotipy
from spotipy.oauth2 import SpotifyPKCE
from shared_constants import *
import requests
from io import BytesIO
import random
import time
import asyncio
import traceback
import json
import os

clock = pygame.time.Clock()
pygame.init()

# Defines what my application can do with the spotify account
SCOPES = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-email",
    "user-read-private"
]

USER_ABORT_GAME_FROM_SEARCH = "USER_ABORT_GAME_FROM_SEARCH"

def get_spotify_device(spotify_instance):
    """Gets a Spotify device ID, using cache or fetching new if needed."""
    global cached_device_id
    # Check cache 
    if cached_device_id:
        pass # Keep using cached_device_id
    else: 
        try:
            if not spotify_instance:
                return None
            devices = spotify_instance.devices()
            if not devices or not devices['devices']:
                cached_device_id = None # Ensure it's None if no devices
                return None
            # Prefer active device otherwise take the first one
            active_device = next((d for d in devices['devices'] if d.get('is_active')), None)
            if active_device:
                cached_device_id = active_device['id']
            else:
                cached_device_id = devices['devices'][0]['id']
        except Exception: 
            traceback.print_exc()
            cached_device_id = None
            return None
    return cached_device_id

def authenticate_spotify():
    """Handles Spotify PKCE authentication and returns a Spotify instance.""" #third time changing auth flow
    try:
        # Check if cache exists and is valid
        cache_valid = False
        if os.path.exists('.cache'):
            try:
                with open('.cache', 'r') as f:
                    token_info = json.load(f)
                    # Check if token exists and hasn't expired
                    if (token_info.get('access_token') and 
                        token_info.get('expires_at') and 
                        time.time() < token_info.get('expires_at', 0)):
                        cache_valid = True
                    else:
                        print("Token expired or invalid, removing cache")
                        os.remove('.cache')
            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                print("Invalid cache file, removing")
                if os.path.exists('.cache'):
                    os.remove('.cache')

        auth_manager = SpotifyPKCE(
            client_id=SPOTIFY_CLIENT_ID,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_AUTH_SCOPE,
            open_browser=True,
            cache_path=".cache"
        )
        
        # Create Spotify instance
        spotify_instance = spotipy.Spotify(auth_manager=auth_manager)
        
        # Test the connection by trying to get user info
        try:
            user_info = spotify_instance.current_user()
            if not user_info:
                print("Failed to get user info, authentication may have failed")
                return None
            print(f"Authenticated as: {user_info.get('display_name', 'Unknown')}")
        except Exception as e:
            print(f"Authentication test failed: {e}")
            return None
        
        # Test device connection
        if get_spotify_device(spotify_instance) is None:
            print("No active Spotify devices found")
            return None
            
        return spotify_instance
    except Exception as e:
        print(f"Auth error: {str(e)}")
        traceback.print_exc()
        return None

def show_login_screen(screen, font):
    """Displays the Spotify login screen and handles the authentication flow."""
    clock = pygame.time.Clock()  # Moved inside function where it's used
    global sp
    login_button = pygame.Rect(width//2 - 150, height//2 - 25, 300, 50)
    login_text_default = "Login with Spotify"
    current_login_text = login_text_default
    error_message = None
    error_timer = 0
    is_authenticating = False
    
    title_font = pygame.font.SysFont("Press Start 2P", 55)
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                if login_button.collidepoint(event.pos) and not is_authenticating:
                    is_authenticating = True
                    current_login_text = "Logging in..."
                    pygame.draw.rect(screen, DARK_BLUE, login_button)
                    text_surf_auth = font.render(current_login_text, True, BLACK)
                    text_rect_auth = text_surf_auth.get_rect(center=login_button.center)
                    screen.blit(text_surf_auth, text_rect_auth)
                    pygame.display.flip()

                    temp_sp_instance = None
                    try:
                        temp_sp_instance = authenticate_spotify()
                        if temp_sp_instance:
                            sp = temp_sp_instance
                            return sp 
                        else:
                            error_message = "Login failed. Ensure Spotify is open & Premium."
                            error_timer = time.time()
                    except Exception as e:
                        error_message = f"Login error: {str(e)}"
                        error_timer = time.time()
                        traceback.print_exc()  # Print full traceback for debugging
                    finally:
                        is_authenticating = False
                        current_login_text = login_text_default

        screen.fill(DARK_GREY)
        
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        
        title = title_font.render("Welcome to SpotiSnake!", True, BLACK)
        screen.blit(title, (width//2 - title.get_width()//2, height//4))
        
        if is_authenticating:
            button_color = DARK_BLUE # active and inactive colour
        else:
            button_color = LIGHT_BLUE
            
        pygame.draw.rect(screen, button_color, login_button)
        text_surf = font.render(current_login_text, True, BLACK)
        text_rect = text_surf.get_rect(center=login_button.center)
        screen.blit(text_surf, text_rect)
        
        instructions = [
            "Click to login with Spotify",
            "Browser will open for log-in",
            "Return here after log-in",
            "NOTE: Spotify Premium needed"
        ]
        y_offset = height//2 + 50
        small_font = pygame.font.SysFont("Press Start 2P", 20)
        for instruction in instructions:
            text = small_font.render(instruction, True, WHITE)
            screen.blit(text, (width//2 - text.get_width()//2, y_offset))
            y_offset += 40
            
        if error_message and time.time() - error_timer < 5:
            error_surf = small_font.render(error_message, True, RED)
            screen.blit(error_surf, (width//2 - error_surf.get_width()//2, height - 50))

        pygame.display.flip()
        clock.tick(30)

def play_track_sync(track_uri, position_ms):
    """Synchronously plays a specific track on Spotify. Returns True on success."""
    global sp, cached_device_id
    if not sp:
        return False
    
    device_to_use = get_spotify_device(sp) 
    if not device_to_use:
        return False

    try:
        sp.start_playback(
            device_id=device_to_use,
            uris=[track_uri],
            position_ms=position_ms
        )
        return True
    except spotipy.exceptions.SpotifyException:
        cached_device_id = None # Clear cache on certain errors like 403/404
        return False
    except Exception:
        traceback.print_exc() # Keep traceback for actual errors
        return False

def play_uri_with_details(track_uri, position_ms=0):
    """Plays a track and returns (success_bool, track_name, track_artist). Blocking."""
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
    except Exception:
        pass # Silently fail on fetching details, return default error names

    played_successfully = play_track_sync(track_uri, position_ms)
    
    return played_successfully, track_name, track_artist

async def play_random_track_from_album(album_uri, song_info_updater_callback):
    """Asynchronously plays a random track from an album and updates UI via callback."""
    global sp
    if not sp:
        song_info_updater_callback("N/A", "Spotify Not Init", False) # Inform UI
        return
    
    track_name, track_artist, is_easter_egg_track_selected, played_successfully = "Error", "Unknown", False, False

    try:
        results = await asyncio.to_thread(sp.album_tracks, album_uri, limit=50) 
        tracks = results.get('items')
        if not tracks:
            track_name, track_artist = "No Tracks In Album", "N/A"
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
        # Check if the selected track is the Easter egg track
        is_easter_egg_track_selected = (chosen_track_uri == EASTER_EGG_TRACK_URI)
        
        played_successfully = await asyncio.to_thread(play_track_sync, chosen_track_uri, position_ms) 
        if played_successfully:
            song_info_updater_callback(track_name, track_artist, is_easter_egg_track_selected)
        else:
            song_info_updater_callback(track_name, f"(Failed: {track_artist})", False)

    except Exception:
        song_info_updater_callback("Error During Playback", "Album Track Error", False)

def cleanup():
    """Cleans up Spotify session without removing auth token."""
    global cached_device_id
    try:
        if sp:
            # Be more aggressive about stopping music
            try:
                sp.pause_playback()
            except Exception:
                pass
            # Try again in case the first call didn't work
            try:
                sp.pause_playback()
            except Exception:
                pass
            # Give Spotify a moment to actually stop
            time.sleep(0.3)
    except Exception:
        pass
    finally:
        cached_device_id = None
        # Don't remove .cache file to maintain authentication

def search_album(query):
    """Searches Spotify for albums matching the query. Returns a list of album details."""
    global sp
    if not sp:
        return []
        
    try:
        results = sp.search(q=query, type='album', limit=5)
        if not results or 'albums' not in results:
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
        return album_info
    except Exception:
        return []

def download_and_resize_album_cover(url, target_width, target_height):
    """Downloads an image from a URL and resizes it to target dimensions."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        img_data = BytesIO(response.content)
        image = pygame.image.load(img_data)
        image = pygame.transform.scale(image, (target_width, target_height))
        return image
    except Exception:
        return None

async def get_album_search_input(screen, font):
    """Displays album search UI, handles input, plays background track, returns selected album or sentinel."""
    global sp
    if not sp:
        return None
    
    async def music_task_wrapper():
        """Plays background music during album search."""
        await asyncio.to_thread(play_track_sync, SEARCH_TRACK_URI, 3000)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(music_task_wrapper()) # Use the wrapper
    except RuntimeError:
        pass # Occurs if no event loop is running, though get_album_search_input is async
    except Exception:
        traceback.print_exc()

    try:
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
    except Exception:
        traceback.print_exc()
        return USER_ABORT_GAME_FROM_SEARCH

    def draw_search_results_local():
        """Draws the album search results list onto the screen."""
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
                    if sp: 
                        sp.pause_playback()
                        time.sleep(0.2)
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
                        if sp: 
                            sp.pause_playback()
                            time.sleep(0.2)
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
                            search_results = search_album(text)
                            album_covers.clear()
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                        if not text:
                            search_results = []
                            album_covers.clear()
                    else:
                        text += event.unicode
        
        screen.fill((30, 30, 30))

        # Draw background
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
        
        await asyncio.sleep(0)
