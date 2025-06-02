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

# Defines what my application can do with the spotify account
SCOPES = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-email",
    "user-read-private"
]

sp = None
cached_device_id = None

def get_spotify_device(spotify_instance):
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
            # Prefer active device, otherwise take the first one
            active_device = next((d for d in devices['devices'] if d.get('is_active')), None)
            if active_device:
                cached_device_id = active_device['id']
            else:
                cached_device_id = devices['devices'][0]['id']
        except Exception:
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
        # user = spotify_instance.current_user() # User info not directly used beyond connection check
        if get_spotify_device(spotify_instance) is None:
            return None
            
        return spotify_instance
    except Exception:
        return None

def show_login_screen(screen, font):
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
                    except Exception:
                        error_message = "Login error. Try again."
                        error_timer = time.time()
                    finally:
                        is_authenticating = False
                        current_login_text = login_text_default

        screen.fill(DARK_GREY)
        
        title = title_font.render("Welcome to SpotiSnake!", True, LIGHT_BLUE)
        screen.blit(title, (width//2 - title.get_width()//2, height//4))
        
        if is_authenticating:
            button_color = DARK_BLUE
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
    """Synchronous function to play a track. Returns success_bool."""
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
        return False

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
    except Exception:
        pass # Silently fail on fetching details, return default error names

    played_successfully = play_track_sync(track_uri, position_ms)
    
    return played_successfully, track_name, track_artist

async def play_random_track_from_album(album_uri, song_info_updater_callback):
    """Plays a random track asynchronously and calls a callback with track details."""
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
        is_easter_egg_track_selected = (chosen_track_uri == EASTER_EGG_TRACK_URI)
        
        played_successfully = await asyncio.to_thread(play_track_sync, chosen_track_uri, position_ms) 
        if played_successfully:
            song_info_updater_callback(track_name, track_artist, is_easter_egg_track_selected)
        else:
            song_info_updater_callback(track_name, f"(Failed: {track_artist})", False)

    except Exception:
        song_info_updater_callback("Error During Playback", "Album Track Error", False)

def cleanup():
    global cached_device_id
    try:
        if sp:
            try:
                current_playback = sp.current_playback()
                if current_playback and current_playback.get('is_playing'):
                    sp.pause_playback()
            except Exception:
                pass 
    except Exception:
        pass
    finally:
        cached_device_id = None # Clear cached device ID on cleanup

def search_album(query):
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
    global sp
    if not sp:
        return None

    SEARCH_TRACK_URI = "spotify:track:2XmGbXuxrmfp3inzEuQhE1"
    SEARCH_TRACK_START_MS = 3000
    async def play_search_screen_track_task():
        active_device_id = None
        try:
            active_device_id = await asyncio.to_thread(get_spotify_device, sp)
        except Exception:
            return
        if active_device_id:
            try:
                await asyncio.to_thread(
                    sp.start_playback,
                    device_id=active_device_id,
                    uris=[SEARCH_TRACK_URI],
                    position_ms=SEARCH_TRACK_START_MS
                )
            except Exception:
                pass 
        else:
            pass # No device, no print

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(play_search_screen_track_task())
    except RuntimeError:
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
    quit_button_rect_local = pygame.Rect(20, height - 70, 250, 50)
    quit_button_font = pygame.font.SysFont("Press Start 2P", 20)

    def draw_search_results_local():
        if search_results:
            pygame.draw.rect(screen, WHITE, results_area)
            y_offset = results_area.y + 10
            for album_idx, album in enumerate(search_results):
                result_rect = pygame.Rect(results_area.x + 5, y_offset, results_area.width - 10, 70)
                if result_rect.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(screen, LIGHT_GREY, result_rect)
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
                name_font = pygame.font.SysFont('corbel', 18)
                name_surf = name_font.render(album['name'], True, BLACK)
                screen.blit(name_surf, (text_start_x, result_rect.y + 10))
                artist_font = pygame.font.SysFont('corbel', 16)
                artist_surf = artist_font.render(album['artist'], True, DARK_GREY)
                screen.blit(artist_surf, (text_start_x, result_rect.y + 35))
                y_offset += 80
        elif text:
            no_results_surf = font.render("No results. Press Enter to search.", True, WHITE)
            screen.blit(no_results_surf, (results_area.x + 10, results_area.y + 10))
        else:
            no_results_surf = font.render("Type to search. Press Enter.", True, WHITE)
            screen.blit(no_results_surf, (results_area.x + 10, results_area.y + 10))

    search_input_clock = pygame.time.Clock()

    while True:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return USER_QUIT_ALBUM_SEARCH
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                else:
                    active = False
                color = color_active if active else color_inactive
                if quit_button_rect_local.collidepoint(mouse_pos):
                    return USER_QUIT_ALBUM_SEARCH
                if search_results:
                    y_offset = results_area.y + 10
                    for album in search_results:
                        result_rect = pygame.Rect(results_area.x + 5, y_offset, results_area.width - 10, 70)
                        if result_rect.collidepoint(event.pos):
                            return album
                        y_offset += 80
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
        label_font = pygame.font.SysFont("Press Start 2P", 25)
        label = label_font.render("Search for an album:", True, WHITE)
        screen.blit(label, (input_box.x, input_box.y - 40))
        txt_surface = font.render(text, True, color)
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        pygame.draw.rect(screen, color, input_box, 2)
        draw_search_results_local()
        pygame.draw.rect(screen, LIGHT_BLUE, quit_button_rect_local)
        quit_text_surf = quit_button_font.render("QUIT", True, BLACK)
        quit_text_rect = quit_text_surf.get_rect(center=quit_button_rect_local.center)
        screen.blit(quit_text_surf, quit_text_rect)
        pygame.display.flip()
        
        await asyncio.sleep(0.001)
        search_input_clock.tick(30)