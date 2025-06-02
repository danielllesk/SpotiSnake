width = 600
height = 600

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (0, 0, 139)
LIGHT_GREY = (40,40,40)
DARK_GREY = (30,30,30)

SNAKE_SPEED = 10  # How often the snake moves
GRID_SIZE = 30  # Size for snake movement
ALBUM_GRID_SIZE = 60  # Size for album pieces

# Spotify API credentials
SPOTIFY_CLIENT_ID = "defd35be86e24389ad40e4f29d9fee68"  
SPOTIFY_CLIENT_SECRET = "9d636af19f3f4fc6909bfff710da8b11"  
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

EASTER_EGG_TRACK_URI = "spotify:track:2H30WL3exSctlDC9GyRbD4" #shhhh
WINNING_TRACK_URI = "spotify:track:7ccI9cStQbQdystvc6TvxD" # We are the champions by queen
SEARCH_TRACK_URI = "spotify:track:2XmGbXuxrmfp3inzEuQhE1" # Zatar by MF DOOM
START_MENU_URI = "spotify:track:2x7H4djW0LiFf1C1wzUDo9" # White Willow Bark by MF DOOM

USER_QUIT_ALBUM_SEARCH = "USER_QUIT_ALBUM_SEARCH"
USER_ABORT_GAME_FROM_SEARCH = "USER_ABORT_GAME_FROM_SEARCH"

OUTLINE_COLOR = BLACK
OUTLINE_THICKNESS = 2 

button_width = width // 3        
button_height = height // 14      
button_x = (width - button_width) // 2 

play_button_y = height // 3       
quit_button_y = play_button_y + button_height + (height // 30) 

sp = None
cached_device_id = None