import pygame
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from shared_constants import *
clock = pygame.time.Clock()
import requests
from io import BytesIO
from urllib.request import urlopen

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-library-read"
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
            # Get the album art URL (using smallest size for performance)
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
def get_album_art(url):
    try:
        response = requests.get(url, verify=False)  # Note: This is less secure
        response.raise_for_status()
        img_data = BytesIO(response.content)
        image = pygame.image.load(img_data)
        return pygame.transform.scale(image, (40, 40))
    except Exception as e:
        print(f"Error loading album art: {e}")
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
    album_covers = {}  # Cache for album covers

    def draw_search_results():
        if search_results:
            pygame.draw.rect(screen, WHITE, results_area)
            y_offset = results_area.y + 10
            
            for album in search_results:
                # Create a button-like area for each result
                result_rect = pygame.Rect(results_area.x + 5, y_offset, results_area.width - 10, 60)
                
                # Highlight on hover
                if result_rect.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(screen, LIGHT_BLUE, result_rect)
                else:
                    pygame.draw.rect(screen, WHITE, result_rect)
                pygame.draw.rect(screen, DARK_BLUE, result_rect, 1)

                # Load album cover if not already loaded
                if album['image_url'] and album['uri'] not in album_covers:
                    album_covers[album['uri']] = get_album_art(album['image_url'])

                # Draw album cover
                if album['uri'] in album_covers and album_covers[album['uri']]:
                    screen.blit(album_covers[album['uri']], 
                              (result_rect.x + 10, result_rect.y + 10))
                    text_start_x = result_rect.x + 60  # Start text after the album cover
                else:
                    text_start_x = result_rect.x + 10

                # Draw album name
                name_surf = font.render(album['name'], True, BLACK)
                screen.blit(name_surf, (text_start_x, result_rect.y + 10))

                # Draw artist name in smaller font
                artist_font = pygame.font.SysFont('times new roman', int(font.get_height() * 0.8))
                artist_surf = artist_font.render(album['artist'], True, DARK_BLUE)
                screen.blit(artist_surf, (text_start_x, result_rect.y + 35))

                y_offset += 70  # Increased space between results to accommodate cover art

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
                            album_covers.clear()  # Clear cached covers
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                        if not text:
                            search_results = []
                            album_covers.clear()
                    else:
                        text += event.unicode

        screen.fill((30, 30, 30))

        # Draw search box label
        label = font.render("Search for an album:", True, WHITE)
        screen.blit(label, (input_box.x, input_box.y - 30))

        # Draw input box
        txt_surface = font.render(text, True, color)
        width = max(400, txt_surface.get_width() + 10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        pygame.draw.rect(screen, color, input_box, 2)

        # Draw search results with album covers
        draw_search_results()

        pygame.display.flip()
        clock.tick(30)

