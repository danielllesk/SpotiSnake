# Spotify credentials
SPOTIFY_CLIENT_ID = "aa7df0779c82489f849692b1754f1449"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8000/callback"
SPOTIFY_AUTH_SCOPE = "user-modify-playback-state user-read-playback-state user-read-email user-read-private"
sp = None
cached_device_id = None

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

button_width = width // 3        
button_height = height // 14      
button_x = (width - button_width) // 2 

play_button_y = height // 3       
quit_button_y = play_button_y + button_height + (height // 30)