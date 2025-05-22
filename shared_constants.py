width = 600
height = 600

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (0, 0, 139)

SNAKE_SPEED = 17
GRID_SIZE = 10  # Each cell is 10x10 pixels

SPOTIFY_CLIENT_ID = "defd35be86e24389ad40e4f29d9fee68"
SPOTIFY_CLIENT_SECRET = "9d636af19f3f4fc6909bfff710da8b11"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

button_width = width // 3        
button_height = height // 14      
button_x = (width - button_width) // 2 

play_button_y = height // 3       
quit_button_y = play_button_y + button_height + (height // 30) 