import pygame
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from shared_constants import *
import requests
from io import BytesIO
import random
import time

clock = pygame.time.Clock()
pygame.init()

# Define the required scopes for playback
SCOPES = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-email",
    "user-read-private"
]

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
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # Test the connection
        user = sp.current_user()
        print(f"Successfully connected to Spotify as {user['display_name']}!")
        return sp
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
                            error_message = "Login failed. Please try again."
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

# Initialize sp variable
sp = None

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
        response = requests.get(url, verify=False)
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

    def draw_button(text, x, y, w, h, inactive_color, active_color):
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        button_font = pygame.font.SysFont("Press Start 2P", 25)
        if x < mouse[0] < x + w and y < mouse[1] < y + h:
            pygame.draw.rect(screen, active_color, (x, y, w, h))
            if click[0] == 1:
                return True
        else:
            pygame.draw.rect(screen, inactive_color, (x, y, w, h))
        text_surf = button_font.render(text, True, BLACK)
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
                name_font = pygame.font.SysFont('times new roman', 20)  # Changed to Times New Roman
                name_surf = name_font.render(album['name'], True, BLACK)
                screen.blit(name_surf, (text_start_x, result_rect.y + 10))
                artist_font = pygame.font.SysFont('times new roman', 20)  # Already Times New Roman
                artist_surf = artist_font.render(album['artist'], True, DARK_BLUE)
                screen.blit(artist_surf, (text_start_x, result_rect.y + 40))
                y_offset += 80
        else:
            # Draw "No results" message if search_results is empty
            no_results_surf = font.render("No results found, click enter to search", True, WHITE)
            screen.blit(no_results_surf, (results_area.x + 10, results_area.y + 10))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try:
                    sp.pause_playback()
                except:
                    pass
                pygame.quit()
                return None
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
                    active = False
                    color = color_inactive
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        if text:
                            print(f"Searching for: {text}")  # Debug print
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
        screen.blit(label, (input_box.x, input_box.y - 30))
        txt_surface = font.render(text, True, color)
        width = max(400, txt_surface.get_width() + 10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        pygame.draw.rect(screen, color, input_box, 2)
        draw_search_results()
        
        # Draw quit button at bottom left
        quit_button_x = 20  # 20 pixels from left edge
        quit_button_y = height - button_height - 20  # 20 pixels from bottom
        if draw_button("Quit", quit_button_x, quit_button_y, button_width, button_height, LIGHT_BLUE, DARK_BLUE):
            try:
                sp.pause_playback()
            except:
                pass
            pygame.quit()
            return None
            
        pygame.display.flip()
        clock.tick(30)

def play_random_track_from_album(album_uri):
    try:
        # First, check for available devices
        devices = sp.devices()
        if not devices or not devices['devices']:
            print("No Spotify devices found. Please open Spotify on your device.")
            return False

        # Get all tracks from the album
        results = sp.album_tracks(album_uri)
        tracks = results['items']
        
        # If there are more tracks, get them all
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
            
        if not tracks:
            return False
            
        # Select a random track
        track = random.choice(tracks)
        track_uri = track['uri']
        
        # Get track duration in milliseconds
        track_info = sp.track(track_uri)
        duration_ms = track_info['duration_ms']
        
        # Calculate a random start position (at least 30 seconds before the end)
        max_start = duration_ms - 30000  # 30 seconds before end
        if max_start > 0:
            start_position = random.randint(0, max_start)
        else:
            start_position = 0

        # Try to transfer playback to the first available device
        try:
            sp.transfer_playback(devices['devices'][0]['id'], force_play=True)
        except Exception as e:
            print(f"Error transferring playback: {e}")
            
        # Start playback
        sp.start_playback(
            device_id=devices['devices'][0]['id'],
            uris=[track_uri],
            position_ms=start_position
        )
        return True
    except Exception as e:
        print(f"Error playing track: {e}")
        return False
