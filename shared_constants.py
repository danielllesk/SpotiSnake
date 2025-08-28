# Check if we're running in a backend context (no display)
import os
import sys

def is_backend_context():
    """Check if we're running in a backend context"""
    import inspect
    try:
        frame = inspect.currentframe()
        while frame:
            if 'backend' in str(frame.f_globals.get('__file__', '')):
                return True
            frame = frame.f_back
    except:
        pass
    
    return (os.environ.get('FLASK_APP') or 
            'backend' in sys.argv or 
            any('backend' in arg for arg in sys.argv))

# Only import pygame if we're not in a backend context
if not is_backend_context():
    try:
        import pygame
        import time

        def resource_path(relative_path):
            try:
                base_path = sys._MEIPASS
            except AttributeError:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        if not pygame.get_init():
            pygame.init()
    except (ImportError, AttributeError):
        pass
else:
    pygame = None

# Spotify credentials
SPOTIFY_CLIENT_ID = "aa7df0779c82489f849692b1754f1449" 
SPOTIFY_REDIRECT_URI = "https://spotisnake.onrender.com/callback"
SPOTIFY_AUTH_SCOPE = "user-modify-playback-state user-read-playback-state user-read-email user-read-private"

# Game dimensions
width = 600
height = 600

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (0, 0, 139)
LIGHT_GREY = (40,40,40)
DARK_GREY = (30,30,30)

# Game settings
SNAKE_SPEED = 10
GRID_SIZE = 30
ALBUM_GRID_SIZE = 60

# Speed progression settings
SPEED_INCREMENT = 1.0
MAX_SPEED = 25

# Spotify track URIs
EASTER_EGG_TRACK_URI = "spotify:track:2H30WL3exSctlDC9GyRbD4" #shhhh
WINNING_TRACK_URI = "spotify:track:7ccI9cStQbQdystvc6TvxD" # We are the champions by queen
SEARCH_TRACK_URI = "spotify:track:2XmGbXuxrmfp3inzEuQhE1" # Zatar by MF DOOM
START_MENU_URI = "spotify:track:2x7H4djW0LiFf1C1wzUDo9" # White Willow Bark by MF DOOM

# Game states
USER_QUIT_ALBUM_SEARCH = "USER_QUIT_ALBUM_SEARCH"
USER_ABORT_GAME_FROM_SEARCH = "USER_ABORT_GAME_FROM_SEARCH"

# UI settings
OUTLINE_COLOR = BLACK
OUTLINE_THICKNESS = 2

def load_image_simple(filename):
    """Load an image with simple error handling"""
    if pygame is None:
        return None
    try:
        image = pygame.image.load(filename)
        image = pygame.transform.scale(image, (width, height))
        return image
    except Exception:
        return None

def load_fruit_image():
    """Load the custom fruit image for the game"""
    if pygame is None:
        return None
    try:
        fruit_image = pygame.image.load("fruit.png")
        fruit_image = pygame.transform.scale(fruit_image, (GRID_SIZE, GRID_SIZE))
        return fruit_image
    except Exception:
        return None

# Load images
game_bg = load_image_simple('background.png')
start_menu_bg = load_image_simple('SpotipyStart.png')
fruit_image = load_fruit_image()