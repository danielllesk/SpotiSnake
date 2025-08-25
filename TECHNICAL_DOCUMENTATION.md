# SpotiSnake: Complete Technical Guide

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture Overview](#system-architecture-overview)
3. [Core Technologies Explained](#core-technologies-explained)
4. [Authentication Flow Deep Dive](#authentication-flow-deep-dive)
5. [Music Integration System](#music-integration-system)
6. [Game Mechanics & Logic](#game-mechanics--logic)
7. [Web Browser Compatibility](#web-browser-compatibility)
8. [Error Handling & User Experience](#error-handling--user-experience)
9. [Performance & Optimization](#performance--optimization)

---

## Introduction

This document provides a comprehensive technical overview of SpotiSnake, explaining how each component works in detail. Whether you're a developer, or simply curious about how the game functions, this guide breaks down technical concepts into understandable explanations.

**What is SpotiSnake?**
SpotiSnake is a web-based Snake game that integrates with Spotify's music service. Players search for albums, and as they collect pieces of the album cover, the game plays different tracks from that album. It's built using Python (Pygame) and runs in web browsers using Pygbag and Pyodide.

---

## System Architecture Overview

```
┌─────────────────────────────────────┐
│           Web Browser               │  ← User Interface
├─────────────────────────────────────┤
│         Pyodide (Python)            │  ← Game Logic
├─────────────────────────────────────┤
│         Flask Backend               │  ← Spotify API Calls
└─────────────────────────────────────┘
```

**Layer 1: Web Browser**
- What it does: Displays the game and handles user interactions
- Technology: HTML5 Canvas, JavaScript
- Why it's needed: Browsers can't run Python directly

**Journey Note:** In hindsight, I would rebuild this game using JavaScript because using Python in a web browser is difficult, but you live and learn, I guess.

**Layer 2: Pyodide (Python)**
- What it does: Runs the actual Python game code
- Technology: Pyodide & Pygbag (Python compiled to WebAssembly)
- Why it's needed: Allows Python code to run in browsers

**Layer 3: Flask Backend**
- What it does: Communicates with Spotify's servers
- Technology: Flask (Python web framework)
- Why it's needed: Handles authentication and API calls that browsers can't do directly

### Why This Setup?

Web browsers have security restrictions that prevent them from directly accessing external services like Spotify. This three-layer system allows us to:
1. Run Python game code in the browser (Layer 2)
2. Communicate with Spotify through a secure backend (Layer 3)
3. Display everything to the user (Layer 1)
---

## Core Technologies Explained

### Pyodide: Python in the Browser

**What is Pyodide?**
Pyodide is a technology that compiles Python code into WASM, which browsers can understand and execute. Sorta like a translator that converts Python instructions into a language the browser can understand.

**How it Works:**
1. Python code is compiled into WASM 'bytecode'
2. The browser loads this bytecode and executes it
3. Pyodide provides Python libraries and runtime environment
4. The game runs as if it were native Python, but in the browser

**Why I Used It:**
- Allows us to use Pygame (a Python game library) in the browser
- Maintains the power and flexibility of Python
- Enables complex game logic that would be difficult in JavaScript

### Pygame: Game Development Framework

**What is Pygame?**
Pygame is a Python library specifically designed for game development. It provides tools for:
- Drawing graphics on screen
- Handling user input (keyboard, mouse)
- Playing sounds and music
- Managing game loops and timing
**Journey Note:** I used Pygame instead of other languages/technologies because it seemed very simple in the tutorial and made debugging very easy. However, using Pygame, the Spotify API, and Pyodide together (a bunch of technologies that aren't necessarily designed to work together) opened up a world of new problems.
**Key Pygame Concepts:**

**Surface Objects:**
```python
# A surface is like a digital canvas where you draw things
screen = pygame.display.set_mode((600, 600))  # Creates a 600x600 pixel canvas
```

**Game Loop:**
```python
# The game loop runs continuously, updating the game state
while running:
    # Handle events (key presses, mouse clicks)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Update game logic (move snake, check collisions)
    update_game()
    
    # Draw everything to the screen
    draw_game()
    
    # Wait a short time before next frame
    pygame.time.Clock().tick(60)  # 60 frames per second
```

### Flask: Web Backend Framework

**What is Flask?**
Flask is a web framework for Python that creates web servers. In SpotiSnake, it acts as a bridge between the game and Spotify's servers.

**How Flask Works:**
1. Receives requests from the game (running in the browser)
2. Processes these requests (authentication, API calls)
3. Sends responses back to the game
4. Handles security and session management

**Journey Note:** This was my first time using Flask and I have to say it was very easy to work with - I give it a 10/10!

**Key Flask Concepts:**

**Routes:**
```python
@app.route('/play', methods=['POST'])
def play_track():
    # This function runs when the game sends a request to /play
    return jsonify({'status': 'success'})
```

**Session Management:**
```python
# Sessions store user data between requests
session['token_info'] = spotify_token  # Store authentication token
```

### Asynchronous Programming (async/await)

**What is Asynchronous Programming?**
Asynchronous programming allows the game to perform multiple tasks simultaneously without freezing the user interface. 

**Journey Note:** Without async, the game ran very slow, so I searched up some methods on how to make the game run faster and spent days and hours reading documentation and implementing something called multithreading. Only to find out after fully implementing it that WASM doesn't support multithreading and I had to revert to async.

**Why It's Important:**
- Prevents the game from freezing while waiting for network requests
- Allows smooth gameplay even when loading data
- Enables responsive user interface

**How It Works:**
```python
async def load_album_data():
    # This function can "pause" and let other code run
    await asyncio.sleep(0.1)  # Wait 0.1 seconds
    # Then continue executing
    return album_data

# Using the async function
async def main():
    album_data = await load_album_data()  # Wait for data to load
    # Game continues running smoothly while waiting
```

---

## Authentication Flow Deep Dive

### The Spotify OAuth Process

**OAuth?**
Open Authorization is a security protocol that allows applications to access user data without storing passwords. 

**The Complete Authentication Process:**

#### Step 1: User Initiates Login
```python
def backend_login():
    # Creates a unique URL for the user to visit
    auth_url = sp_oauth.get_authorize_url()
    # Opens this URL in the user's browser
    webbrowser.open(auth_url)
```

**What Happens:**
1. Game creates a unique authorization URL
2. User's browser opens Spotify's login page
3. User enters their Spotify credentials
4. Spotify verifies the credentials

#### Step 2: Spotify Redirects with Authorization Code
```python
@app.route('/callback')
def callback():
    # Spotify sends us back a temporary code
    code = request.args.get('code')
    # We exchange this code for access tokens
    token_info = sp_oauth.get_access_token(code)
    # Store tokens securely in session
    session['token_info'] = token_info
```

**What Happens:**
1. Spotify redirects user back to our server
2. Server receives a temporary authorization code
3. Server exchanges code for access tokens
4. Tokens are stored securely in the session

#### Step 3: Session Management
```python
def get_spotify():
    # Check if user has valid tokens
    token_info = session.get('token_info')
    if not token_info:
        return None  # User needs to login
    
    # Create Spotify client with user's tokens
    sp = spotipy.Spotify(auth=token_info['access_token'])
    return sp
```

**What Happens:**
1. Game checks if user has valid authentication
2. If valid, creates Spotify client with user's permissions
3. If invalid, prompts user to login again

### Callback Handling Explained

**Callback?**
A callback is a function that runs when a specific event occurs. In our authentication system, callbacks handle the response from Spotify after the user logs in.

**The Callback Function Breakdown:**
```python
@app.route('/callback')
def callback():
    # 1. Extract the authorization code from Spotify's response
    code = request.args.get('code')
    
    # 2. Exchange the code for access tokens
    token_info = sp_oauth.get_access_token(code)
    
    # 3. Store tokens securely
    session['token_info'] = token_info
    
    # 4. Redirect user back to the game
    return redirect('/')
```

### Session Management Deep Dive

**What is a Session?**
A session is a way to store user-specific data on the server that persists across multiple requests. Like a locker at a gym, you get a key (session ID) and can store/retrieve your belongings (user data).

**How Sessions Work:**
```python
# Configure session settings
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Store data in session
session['token_info'] = {
    'access_token': 'user_access_token',
    'refresh_token': 'user_refresh_token',
    'expires_at': 1234567890
}

# Retrieve data from session
token_info = session.get('token_info')
```
---

## Music Integration System

### How Spotify API Integration Works

**Spotify's API Structure:**
```
Game → Flask Backend → Spotify API → Spotify Servers
```
**Journey Note:** The main inspiration for this project was because I wanted to use the Spotify API in some way possible. It was just something that I thought I would enjoy working with, and I did.

**Key API Endpoints I Use:**

#### 1. Album Search
```python
def search_albums(query):
    # Search Spotify's database for albums
    results = sp.search(q=query, type='album', limit=5)
    return results['albums']['items']
```

**What This Does:**
- Takes user's search query (e.g., "Drake Views")
- Searches Spotify's database for matching albums
- Returns top 5 results with album information

#### 2. Album Tracks
```python
def get_album_tracks(album_id):
    # Get all tracks from a specific album
    # sp means spotipy, spotifys python API
    tracks = sp.album_tracks(album_id, limit=50)
    return tracks['items']
```

**What This Does:**
- Takes an album ID (unique identifier)
- Retrieves all tracks from that album
- Returns track information (name, artist, duration, etc.)

#### 3. Playback Control
```python
def play_track(track_uri, position_ms=0):
    # Start playing a specific track
    sp.start_playback(uris=[track_uri], position_ms=position_ms)
```

**What This Does:**
- Takes a track URI (unique identifier)
- Starts playback of that track
- Can specify starting position (e.g., start at 30 seconds)

### Track Selection and Randomization

**How Random Track Selection Works:**
```python
def select_random_track(tracks):
    # Choose a random track from the album
    track = random.choice(tracks)
    
    # Calculate random starting position
    duration_ms = track['duration_ms']
    max_position = max(0, duration_ms - 30000)  # 30 seconds before end
    position_ms = random.randint(0, max_position)
    
    return track, position_ms
```

**The Randomization Process:**
1. **Track Selection**: Randomly choose one track from the album
2. **Position Calculation**: Pick a random starting point in the track
3. **Duration Consideration**: Avoid starting too close to the end
4. **Playback Initiation**: Start playing from the calculated position

**Why Random Starting Positions?**
- Prevents players from always hearing the same part of songs
- Creates variety in the gaming experience
- Makes each playthrough more fun man

### Album Cover Integration

**How Album Covers Work:**
```python
def download_album_cover(image_url, width, height):
    # Download image from Spotify's servers
    response = requests.get(image_url)
    image_data = response.content
    
    # Convert to Pygame surface
    image_surface = pygame.image.load(io.BytesIO(image_data))
    
    # Resize to fit game requirements
    resized_surface = pygame.transform.scale(image_surface, (width, height))
    
    return resized_surface
```

**The Cover Processing Pipeline:**
1. **Download**: Fetch image from Spotify's CDN (Content Delivery Network)
2. **Convert**: Transform image data into Pygame-compatible format
3. **Resize**: Scale image to appropriate size for the game
4. **Grid Division**: Split image into small pieces for the snake game
5. **Display**: Show pieces as collectible items in the game

**Grid Division Process:**
```python
def create_album_pieces(album_surface, grid_size=60):
    # Divide album cover into 10x10 grid (100 pieces)
    pieces = {}
    
    for row in range(10):
        for col in range(10):
            # Extract small section of the image
            piece_rect = pygame.Rect(col * grid_size, row * grid_size, 
                                   grid_size, grid_size)
            piece_surface = album_surface.subsurface(piece_rect)
            pieces[(row, col)] = piece_surface
    
    return pieces
```
**Journey Note:** Other than CORS (which you'll read about in a second), making the albums appear on the search screen took the longest out of any possible feature. I had to figure out how to cache the images, resize them, and make sure they're placed in the right location. Saying it now doesn't make it seem that difficult, but trust me, it took a long time.

---

## Game Mechanics & Logic

### Snake Game Fundamentals

**What is the Snake Game?**
The classic Snake game involves controlling a snake that grows longer as it eats food. In SpotiSnake, the food is pieces of album covers, and the snake reveals the complete album cover as it collects pieces.

**Core Game Components:**

#### 1. Snake Representation
```python
class Snake:
    def __init__(self):
        # Snake starts as a list of positions
        self.body = [[300, 300], [270, 300], [240, 300], 
                    [210, 300], [180, 300]]
        self.direction = 'RIGHT'
        self.grow = False
```

**How the Snake Works:**
- **Body**: List of coordinate pairs representing each segment
- **Direction**: Current movement direction (UP, DOWN, LEFT, RIGHT)
- **Growth**: Flag indicating if snake should grow after eating

#### 2. Movement System
```python
def move_snake(snake):
    # Get current head position
    head = snake.body[0].copy()
    
    # Calculate new head position based on direction
    if snake.direction == 'UP':
        head[1] -= 30
    elif snake.direction == 'DOWN':
        head[1] += 30
    elif snake.direction == 'LEFT':
        head[0] -= 30
    elif snake.direction == 'RIGHT':
        head[0] += 30
    
    # Add new head to front of body
    snake.body.insert(0, head)
    
    # Remove tail unless growing
    if not snake.grow:
        snake.body.pop()
    else:
        snake.grow = False
```

**Movement Logic:**
1. **Head Calculation**: Determine new head position based on direction
2. **Body Update**: Add new head to front of snake body
3. **Tail Management**: Remove tail segment (unless growing)
4. **Growth Handling**: Keep tail if snake just ate food

#### 3. Collision Detection
```python
def check_collisions(snake, fruit_pos, revealed_pieces):
    # Check wall collisions
    head = snake.body[0]
    if (head[0] < 0 or head[0] >= 600 or 
        head[1] < 0 or head[1] >= 600):
        return 'WALL_COLLISION'
    
    # Check self collision
    if head in snake.body[1:]:
        return 'SELF_COLLISION'
    
    # Check fruit collision
    if head == fruit_pos:
        return 'FRUIT_COLLISION'
    
    return 'NO_COLLISION'
```

**Collision Types:**
- **Wall Collision**: Snake hits the game boundaries
- **Self Collision**: Snake hits its own body
- **Fruit Collision**: Snake eats a piece of album cover
- **No Collision**: Snake continues moving normally

### Progressive Difficulty System

**How Difficulty Increases:**
```python
def update_difficulty(score, base_speed=10):
    # Increase speed every 50 points
    speed_increment = score // 50
    current_speed = base_speed + speed_increment
    
    return current_speed
```

**Difficulty Progression:**
- **Score 0-49**: Base speed (10)
- **Score 50-99**: Speed 11
- **Score 100-149**: Speed 12
- **And so on...**

**Why Progressive Difficulty?**
- Keeps the game challenging as players improve
- Prevents the game from becoming too easy
- Creates a sense of progression and achievement

**Journey Note:** I demoed the game to friends before this feature and their main complaint was that it was too easy because the snake moved too slow.

### Album Piece Collection System

**How Piece Collection Works:**
```python
def collect_album_piece(snake, fruit_pos, album_pieces, revealed_pieces):
    # Determine which piece the snake ate
    grid_x = fruit_pos[0] // 60
    grid_y = fruit_pos[1] // 60
    
    # Add piece to revealed collection
    revealed_pieces.add((grid_x, grid_y))
    
    # Check if we should change songs (every 5 pieces)
    if len(revealed_pieces) % 5 == 0:
        return 'CHANGE_SONG'
    
    return 'CONTINUE'
```

**Collection Logic:**
1. **Position Calculation**: Convert screen coordinates to grid coordinates
2. **Piece Tracking**: Add collected piece to revealed set
3. **Song Change Check**: Trigger song change every 5 pieces
4. **Visual Update**: Update the displayed album cover

---

## Web Browser Compatibility

### Cross-Origin Resource Sharing (CORS) 😡

**CORS**
CORS is a security feature implemented by web browsers that controls which websites can access resources from other websites. 

**Why CORS Matters:**
- Browsers block requests between different domains by default
- Our game (running on localhost) needs to communicate with our backend (on render.com)
- CORS headers tell the browser this communication is allowed

**How CORS is handled:**
```python
def add_cors_headers(response):
    # Allow requests from any origin (for development)
    response.headers['Access-Control-Allow-Origin'] = '*'
    
    # Allow specific HTTP methods
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    
    # Allow specific headers
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    # Allow credentials (cookies, sessions)
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    return response
```

**CORS Headers Explained:**
- **Access-Control-Allow-Origin**: Which websites can make requests
- **Access-Control-Allow-Methods**: Which HTTP methods are allowed
- **Access-Control-Allow-Headers**: Which headers can be sent
- **Access-Control-Allow-Credentials**: Whether cookies/sessions are allowed

**Journey Note:** Man, I had never heard of CORS before this project, but trust me, now I do. Figuring out how to fix this feature took up a month of my time, super frustrating. The solution was to route all API calls through the Flask backend, which then makes the requests to Spotify on behalf of the browser, instead of direct JS calls. This simple mistake was just because I was unfamiliar with how the backend was supposed to work. 

### JavaScript 

**How Python Communicates with JavaScript:**
```python
import js

# Execute JavaScript code from Python
js.eval('''
    fetch("/api/endpoint", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({data: "example"})
    })
    .then(response => response.json())
    .then(data => {
        window.result = data;
    });
''')

# Access JavaScript variables from Python
if hasattr(js.window, 'result'):
    result = js.window.result
```

**Key JavaScript Functions I Used:**

#### 1. Fetch API
```javascript
fetch(url, options)
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error(error));
```

**What Fetch Does:**
- Makes HTTP requests to servers
- Handles responses asynchronously
- Supports modern web standards

#### 2. sendBeacon API
```javascript
navigator.sendBeacon(url, data);
```

**What sendBeacon Does:**
- Sends data to server without waiting for response
- Continues working even when page is closing
- Perfect for analytics and cleanup operations

**Journey Note:** This was a funny name to me, not sure why

**Why Use sendBeacon:**
- When user closes the browser tab, we need to pause music
- sendBeacon ensures this request gets sent even during page unload
- Regular fetch requests might be cancelled when page closes

#### 3. Page Visibility API
```javascript
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden (user switched tabs)
        pauseMusic();
    }
});
```

**What Page Visibility API Does:**
- Detects when user switches between browser tabs
- Allows us to pause music when user isn't looking at the game
- Improves user experience and saves resources

### Browser Storage and Caching

**How We Cache Data:**
```python
def cache_album_tracks(album_id, tracks):
    # Store tracks in browser's memory
    cache_data = {
        'tracks': tracks,
        'timestamp': time.time()
    }
    
    # Convert to JSON for storage
    cache_json = json.dumps(cache_data)
    
    # Store in JavaScript window object
    setattr(js.window, f'album_tracks_{album_id}', cache_json)
```

**Caching Benefits:**
- **Faster Loading**: Don't need to fetch data again
- **Reduced API Calls**: Save on Spotify API rate limits
- **Better Performance**: Game responds faster
- **Offline Capability**: Can work with cached data

---

## Error Handling & User Experience

### Error Management

**Error Handling Strategy:**

#### 1. Graceful Degradation
```python
def play_music_with_fallback(track_uri):
    try:
        # Try to play the specific track
        result = play_track(track_uri)
        if result:
            return "Playing: " + track_name
    except Exception as e:
        # If that fails, try playing the album
        try:
            result = play_album(album_uri)
            if result:
                return "Playing Album (Limited Info)"
        except Exception as e2:
            # If everything fails, show error
            return "Music Unavailable"
```

**Degradation Levels:**
1. **Best Case**: Play specific track with full information
2. **Good Case**: Play album with limited track info
3. **Acceptable Case**: Show error but game continues
4. **Worst Case**: Game continues without music 

#### 2. Retry Mechanisms
```python
async def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = await fetch(url)
            if response.ok:
                return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

**Retry Strategy:**
- **Immediate Retry**: Try again right away
- **Exponential Backoff**: Wait longer between each retry
- **Maximum Attempts**: Don't retry forever
- **Different Endpoints**: Try alternative methods if available

#### 3. User-Friendly Error Messages

**Before (Technical):**
```
"API Fallback Error: 500 Internal Server Error"
```

**After (User-Friendly):**
```
"Playing Album" / "Random Track (Limited Info)"
```

**Error Message Categories:**
- **Network Issues**: "Connection Problem" / "Try Again"
- **Authentication**: "Login Required" / "Please Login"
- **API Limits**: "Service Busy" / "Try Later"
- **General Errors**: "Something Went Wrong" / "Try Again"

### Loading States and User Feedback

**How Loading States Work:**
```python
def show_loading_screen(screen, message, duration):
    # Display loading message
    font = pygame.font.SysFont('Arial', 24)
    text = font.render(message, True, WHITE)
    text_rect = text.get_rect(center=(300, 300))
    
    # Show loading screen
    screen.fill(BLACK)
    screen.blit(text, text_rect)
    pygame.display.flip()
    
    # Wait for specified duration
    pygame.time.wait(int(duration * 1000))
```
**Journey Note:** This also took surprisingly long because I was unsure on how to track if there were results currently displaying or the API was still searching.

**Loading State Benefits:**
- **User Awareness**: Users know something is happening
- **Perceived Performance**: Appears faster even if it's not
- **Error Prevention**: Users don't think the app is broken
- **Professional Feel**: Makes the app feel more polished

## Performance & Optimization

### Memory Management

**How We Manage Memory:**
```python
def cleanup_resources():
    # Clear unused album covers
    for album_id in list(album_covers.keys()):
        if not is_album_in_use(album_id):
            del album_covers[album_id]
    
    # Clear old cache entries
    current_time = time.time()
    for cache_key in list(cache.keys()):
        if current_time - cache[cache_key]['timestamp'] > 3600:  # 1 hour
            del cache[cache_key]
```

**Memory Optimization Strategies:**
1. **Image Caching**: Store album covers in memory for reuse
2. **Cache Expiration**: Remove old data automatically
3. **Resource Cleanup**: Free memory when not needed
4. **Lazy Loading**: Load resources only when needed

### Network Optimization

**Network Usage:**
```python
def optimize_api_calls():
    # Batch multiple requests together
    # Cache responses to avoid duplicate calls
    # Use compression for large responses
    # Implement request queuing
```

**Network Optimization Techniques:**
1. **Request Batching**: Combine multiple API calls
2. **Response Caching**: Store API responses locally
3. **Compression**: Reduce data transfer size
4. **Connection Pooling**: Reuse network connections
5. **Request Queuing**: Manage API rate limits

### Rendering Optimization

**Optimize Graphics:**
```python
def optimize_rendering():
    # Only redraw changed areas
    # Use sprite sheets for multiple images
    # Implement frame rate limiting
    # Use hardware acceleration when available
```

**Rendering Optimization Techniques:**
1. **Dirty Rectangle Rendering**: Only update changed screen areas
2. **Sprite Batching**: Group similar graphics operations
3. **Frame Rate Control**: Limit frames per second to save resources
4. **Texture Atlases**: Combine multiple images into one texture

### Asynchronous Operations

**How Asynchronous Operations Improve Performance:**
```python
async def load_game_resources():
    # Load multiple resources simultaneously
    tasks = [
        load_album_covers(),
        load_music_tracks(),
        load_game_assets()
    ]
    
    # Wait for all resources to load
    results = await asyncio.gather(*tasks)
    return results
```

**Asynchronous Benefits:**
- **Parallel Processing**: Multiple tasks run simultaneously
- **Non-Blocking**: UI remains responsive during operations
- **Better Resource Utilization**: CPU and network used efficiently
- **Improved User Experience**: Faster loading times

---

### Future Enhancements

**Planned Improvements:**

#### 1. Performance Optimizations
- **WebAssembly Optimization**: Improve Python to WASM compilation
- **Asset Compression**: Reduce file sizes for faster loading
- **Caching Strategy**: Implement better caching
- **Lazy Loading**: Load resources only when needed

#### 2. Feature Enhancements
- **Multiplayer Support**: Allow multiple players to compete
- **Custom Playlists**: Let users create custom game playlists
- **Achievement System**: Add achievements and leaderboards
- **Mobile Support**: Optimize for mobile devices
- **Album Specific Questions:** if the user dies they get asked questions about the album and if they answer right they continue their game

#### 3. User Experience Improvements
- **Better Error Messages**: More helpful and actionable error messages
- **Loading Animations**: More engaging loading screens
- **Sound Effects**: Add game sound effects
- **Visual Effects**: Add particle effects and animations

---

## Conclusion

Thank you for taking the time to play my game, or at least look through these documents! This project took a whole summer term to complete, and I spent hours learning brand new technologies to create something unique that I personally enjoy and hope you do too.

**Journey Note:** This was my first major project combining multiple technologies I had never used before. The learning curve was steep, but the satisfaction of seeing everything work together was wild tbh. From the initial concept to the final product, every bug fix and feature addition taught me something new about web development, API integration, and game design.

If there are any changes or fixes you'd like to suggest, I'm open to it! Or if you want to contribute to the project, I'm also open to that too. This has been an amazing learning experience, and I'm excited to see where it goes from here.
---
