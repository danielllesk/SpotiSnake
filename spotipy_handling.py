import pygame
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from shared_constants import *
import requests
from io import BytesIO
import random

clock = pygame.time.Clock()
pygame.init()

# Define the required scopes for playback
SCOPES = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-email",
    "user-read-private"
]

# Create Spotify client with playback scopes
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=" ".join(SCOPES),
    open_browser=True
))

def search_album(query):
    try:
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
    input_box = pygame.Rect(100, 100, 400, 50)
    results_area = pygame.Rect(100, 160, 400, 300)
    color_inactive = DARK_BLUE
    color_active = LIGHT_BLUE
    color = color_inactive
    active = False
    text = ''
    search_results = []
    album_covers = {}

    def draw_search_results():
        if search_results:
            pygame.draw.rect(screen, WHITE, results_area)
            y_offset = results_area.y + 10
            for album in search_results:
                result_rect = pygame.Rect(results_area.x + 5, y_offset, results_area.width - 10, 60)
                if result_rect.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(screen, LIGHT_BLUE, result_rect)
                else:
                    pygame.draw.rect(screen, WHITE, result_rect)
                pygame.draw.rect(screen, DARK_BLUE, result_rect, 1)
                if album['image_url'] and album['uri'] not in album_covers:
                    album_covers[album['uri']] = download_and_resize_album_cover(album['image_url'], 40, 40)
                if album['uri'] in album_covers and album_covers[album['uri']]:
                    screen.blit(album_covers[album['uri']], (result_rect.x + 10, result_rect.y + 10))
                    text_start_x = result_rect.x + 60
                else:
                    text_start_x = result_rect.x + 10
                name_surf = font.render(album['name'], True, BLACK)
                screen.blit(name_surf, (text_start_x, result_rect.y + 10))
                artist_font = pygame.font.SysFont('times new roman', int(font.get_height() * 0.8))
                artist_surf = artist_font.render(album['artist'], True, DARK_BLUE)
                screen.blit(artist_surf, (text_start_x, result_rect.y + 35))
                y_offset += 70

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                    color = color_active if active else color_inactive
                elif search_results:
                    y_offset = results_area.y + 10
                    for album in search_results:
                        result_rect = pygame.Rect(results_area.x + 5, y_offset, results_area.width - 10, 60)
                        if result_rect.collidepoint(event.pos):
                            return album
                        y_offset += 70
                else:
                    active = False
                    color = color_inactive
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
        label = font.render("Search for an album:", True, WHITE)
        screen.blit(label, (input_box.x, input_box.y - 30))
        txt_surface = font.render(text, True, color)
        width = max(400, txt_surface.get_width() + 10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        pygame.draw.rect(screen, color, input_box, 2)
        draw_search_results()
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
