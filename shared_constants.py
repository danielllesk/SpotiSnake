import pygame
import os
import sys
import time

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if not pygame.get_init():
    pygame.init()

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
SNAKE_SPEED = 10  # How often the snake moves
GRID_SIZE = 30  # Size for snake movement
ALBUM_GRID_SIZE = 60  # Size for album pieces

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

# Game backgrounds (load by filename only for browser compatibility)
print("DEBUG: shared_constants.py - Starting to load background images")

def load_image_simple(filename):
    """Load an image with simple error handling"""
    try:
        print(f"DEBUG: shared_constants.py - Loading {filename}")
        image = pygame.image.load(filename)
        image = pygame.transform.scale(image, (width, height))
        print(f"DEBUG: shared_constants.py - {filename} loaded successfully")
        return image
    except Exception as e:
        print(f"DEBUG: shared_constants.py - Failed to load {filename}: {e}")
        return None

# Load images with simple error handling
game_bg = load_image_simple('background.png')
start_menu_bg = load_image_simple('SpotipyStart.png')