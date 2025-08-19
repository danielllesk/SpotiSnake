import pygame
import time
import random
import asyncio
import traceback
from spotipy_handling import (
    get_album_search_input, download_and_resize_album_cover, download_and_resize_album_cover_async,
    play_random_track_from_album, play_uri_with_details, safe_pause_playback, play_track_via_backend
)
from shared_constants import * 
from ui import start_menu, main_menu, quit_game_async

def render_text_with_outline(text_str, font, main_color, outline_color, thickness):
    """Renders text with a specified outline color and thickness."""
    outline_surfaces = []
    positions = [
        (-thickness, -thickness), ( thickness, -thickness), (-thickness,  thickness), ( thickness,  thickness),
        (-thickness, 0), (thickness, 0), (0, -thickness), (0, thickness)
    ]
    for dx, dy in positions:
        text_surface_outline = font.render(text_str, True, outline_color)
        outline_surfaces.append((text_surface_outline, (dx, dy)))

    # Render the main text
    text_surface_main = font.render(text_str, True, main_color)
    
    final_width = text_surface_main.get_width() + 2 * thickness
    final_height = text_surface_main.get_height() + 2 * thickness

    # Create a new surface with transparency for the combined text and outline
    final_surface = pygame.Surface((final_width, final_height), pygame.SRCALPHA)

    for surf, (dx, dy) in outline_surfaces:
        final_surface.blit(surf, (thickness + dx, thickness + dy))
    
    final_surface.blit(text_surface_main, (thickness, thickness))
    
    return final_surface

def cut_image_into_pieces(image_surface, piece_width, piece_height):
    """Divides a Pygame surface into a grid of smaller pieces (subsurfaces)."""
    pieces = {}
    for row in range(0, image_surface.get_height(), piece_height):
        for col in range(0, image_surface.get_width(), piece_width):
            rect = pygame.Rect(col, row, piece_width, piece_height)
            piece = image_surface.subsurface(rect).copy()
            grid_pos = (col // piece_width, row // piece_height)
            pieces[grid_pos] = piece
    return pieces  # {(x, y): surface, ...}

async def start_game(screen):
    """Initializes and runs the main SpotiSnake game loop, including setup and event handling."""
    print("DEBUG: snake_logic.py - start_game called")
    pygame.display.set_caption('SpotiSnake')

    album_result = None
    test_font_object = None

    try:
        test_font_object = pygame.font.SysFont('corbel', 20)
        print("DEBUG: snake_logic.py - Font loaded successfully")
    except Exception as e:
        print(f"DEBUG: snake_logic.py - Font loading failed: {e}")
        traceback.print_exc()
        await asyncio.sleep(1)
        try:
            fallback_font = pygame.font.SysFont('sans', 20) 
            print("DEBUG: snake_logic.py - Using fallback font")
            album_result = await get_album_search_input(screen, fallback_font)
        except Exception as e:
            print(f"DEBUG: snake_logic.py - Fallback font also failed: {e}")
            traceback.print_exc()
            await start_menu()
            return
    else:
        try:
            print("DEBUG: snake_logic.py - Getting album search input")
            album_result = await get_album_search_input(screen, test_font_object)
            print(f"DEBUG: snake_logic.py - Album search result: {album_result}")
        except Exception as e:
            print(f"DEBUG: snake_logic.py - Album search failed: {e}")
            traceback.print_exc()
            await start_menu()
            return

    # Extra debug: ensure album_result is valid
    if album_result == USER_ABORT_GAME_FROM_SEARCH:
        print("DEBUG: snake_logic.py - User aborted from search (album_result == USER_ABORT_GAME_FROM_SEARCH)")
        await quit_game_async()
        return
    
    if album_result == "BACK_TO_MENU":
        print("DEBUG: snake_logic.py - User chose back to menu (album_result == BACK_TO_MENU)")
        # Play start menu music when returning to menu
        print("DEBUG: snake_logic.py - Playing start menu music on return")
        try:
            await play_track_via_backend(START_MENU_URI, 0)
            print("DEBUG: snake_logic.py - Start menu music started on return")
        except Exception as e:
            print(f"DEBUG: snake_logic.py - Failed to start menu music on return: {e}")
        await main_menu()
        return
    
    if album_result == "LOGIN_REQUESTED":
        print("DEBUG: snake_logic.py - User requested login (album_result == LOGIN_REQUESTED)")
        await start_menu()
        return
    
    if not album_result:
        print("DEBUG: snake_logic.py - No album result (album_result is None or False)")
        # Instead of quitting, loop back to album search
        print("DEBUG: snake_logic.py - Restarting album search UI due to no album result")
        await start_game(screen)
        return

    # Handle the case where image_url might be None or missing
    image_url = album_result.get('image_url')
    if image_url is None and 'images' in album_result and album_result['images']:
        image_url = album_result['images'][0].get('url')
    
    album_cover_surface = await download_and_resize_album_cover_async(image_url, width, height)
    if album_cover_surface is None:
        print("DEBUG: snake_logic.py - Failed to load album cover")
        # Instead of quitting, loop back to album search
        await start_game(screen)
        return

    song_display_state = {
        "name": "Initializing...",
        "artist": "",
        "easter_egg_primed": False
    }

    def update_song_display_from_callback(track_name, track_artist, is_ee_primed):
        """Callback function to update the displayed song name, artist, and Easter egg status."""
        nonlocal song_display_state
        song_display_state["name"] = track_name
        song_display_state["artist"] = track_artist
        song_display_state["easter_egg_primed"] = is_ee_primed
        print(f"DEBUG: snake_logic.py - Song updated: {track_name} by {track_artist}")

    song_display_state["name"] = "Loading first game song..."
    song_display_state["artist"] = ""
    print("DEBUG: snake_logic.py - Starting first track")
    
    # Clear any existing playback before starting new album
    print("DEBUG: snake_logic.py - Clearing existing playback before new album")
    try:
        from spotipy_handling import safe_pause_playback
        await safe_pause_playback()
        await asyncio.sleep(0.5)  # Give Spotify time to stop
        print("DEBUG: snake_logic.py - Existing playback cleared")
    except Exception as e:
        print(f"DEBUG: snake_logic.py - Error clearing playback: {e}")
    
    # Get album tracks and play a random one
    from spotipy_handling import play_random_track_from_album
    print(f"DEBUG: snake_logic.py - Playing random track from album: {album_result['uri']}")
    await play_random_track_from_album(album_result['uri'], update_song_display_from_callback)
    print("DEBUG: snake_logic.py - First track started")

    album_pieces = cut_image_into_pieces(album_cover_surface, ALBUM_GRID_SIZE, ALBUM_GRID_SIZE)
    revealed_pieces = set()
    total_album_pieces = (width // ALBUM_GRID_SIZE) * (height // ALBUM_GRID_SIZE)
    print(f"DEBUG: snake_logic.py - Album cut into {len(album_pieces)} pieces")
    print(f"DEBUG: snake_logic.py - Album cover surface size: {album_cover_surface.get_size()}")
    print(f"DEBUG: snake_logic.py - ALBUM_GRID_SIZE: {ALBUM_GRID_SIZE}")
    print(f"DEBUG: snake_logic.py - Total album pieces expected: {total_album_pieces}")
    print(f"DEBUG: snake_logic.py - Album pieces keys: {list(album_pieces.keys())[:5]}...")  # Show first 5 keys

    snake_pos = [width // 2, height // 2]
    snake_body = [[snake_pos[0] - i * GRID_SIZE, snake_pos[1]] for i in range(5)]
    direction = 'RIGHT'
    change_to = direction
    score = 0

    def random_fruit_pos():
        """Generates a valid random position for a new fruit, avoiding snake body and revealed areas."""
        while True:
            pos = [random.randrange(0, width // GRID_SIZE) * GRID_SIZE,
                   random.randrange(0, height // GRID_SIZE) * GRID_SIZE]
            valid_pos = True
            fruit_on_album_grid_col = pos[0] // ALBUM_GRID_SIZE
            fruit_on_album_grid_row = pos[1] // ALBUM_GRID_SIZE
            if (fruit_on_album_grid_col, fruit_on_album_grid_row) in revealed_pieces:
                valid_pos = False
            
            if valid_pos:
                if list(pos) not in snake_body:
                    return pos

    fruit_pos = random_fruit_pos()
    fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)

    running = True
    last_pulse_time = time.monotonic()
    pulse_interval = 0.5
    pulse_on = False

    print("DEBUG: snake_logic.py - Starting main game loop")
    while running:
        current_time = time.monotonic()
        if current_time - last_pulse_time > pulse_interval:
            pulse_on = not pulse_on
            last_pulse_time = current_time
        pulse = 5 if pulse_on else 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("DEBUG: snake_logic.py - QUIT event in game loop")
                await quit_game_async()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP and direction != 'DOWN':
                    change_to = 'UP'
                elif event.key == pygame.K_DOWN and direction != 'UP':
                    change_to = 'DOWN'
                elif event.key == pygame.K_LEFT and direction != 'RIGHT':
                    change_to = 'LEFT'
                elif event.key == pygame.K_RIGHT and direction != 'LEFT':
                    change_to = 'RIGHT'

        direction = change_to
        if direction == 'UP':
            snake_pos[1] -= GRID_SIZE
        elif direction == 'DOWN':
            snake_pos[1] += GRID_SIZE
        elif direction == 'LEFT':
            snake_pos[0] -= GRID_SIZE
        elif direction == 'RIGHT':
            snake_pos[0] += GRID_SIZE

        for i in range(len(snake_body)-1, 0, -1):
            snake_body[i] = snake_body[i-1]
        snake_body[0] = list(snake_pos)

        if snake_pos == fruit_pos:
            score += 10
            print(f"DEBUG: snake_logic.py - Fruit eaten, score: {score}")
            if fruit_album_grid not in revealed_pieces:
                revealed_pieces.add(fruit_album_grid)
                print(f"DEBUG: snake_logic.py - Revealed piece {fruit_album_grid}")

            if song_display_state["easter_egg_primed"]:
                print("DEBUG: snake_logic.py - Easter egg triggered!")
                await trigger_easter_egg_sequence(screen, album_pieces, song_display_state["name"], song_display_state["artist"])
                return

            if len(revealed_pieces) >= total_album_pieces:
                print("DEBUG: snake_logic.py - All pieces revealed, winning!")
                await winning_screen(screen, score, album_pieces)
                return

            fruit_pos = random_fruit_pos()
            fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)
            
            if score > 0 and score % 50 == 0:
                print(f"DEBUG: snake_logic.py - Score milestone reached: {score}, changing song")
                song_display_state["name"] = "Changing song..."
                song_display_state["artist"] = ""
                # Update display immediately, then play track in background
                asyncio.create_task(play_random_track_from_album(album_result['uri'], update_song_display_from_callback))

        if (snake_pos[0] < 0 or snake_pos[0] >= width or
            snake_pos[1] < 0 or snake_pos[1] >= height or
            snake_pos in snake_body[1:]):
            print(f"DEBUG: snake_logic.py - Game over, final score: {score}")
            await game_over(screen, score)
            return
        elif score > 990 and len(revealed_pieces) >= total_album_pieces:
            print("DEBUG: snake_logic.py - Winning condition met!")
            await winning_screen(screen, score, album_pieces)
            return

        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(LIGHT_GREY)

        for pos in revealed_pieces:
            px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
            screen.blit(album_pieces[pos], (px, py))

        for block in snake_body:
            pygame.draw.rect(screen, GREEN, pygame.Rect(block[0], block[1], GRID_SIZE, GRID_SIZE))

        if fruit_album_grid in album_pieces:
            is_fruit_on_revealed_area = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE) in revealed_pieces
            if not is_fruit_on_revealed_area:
                screen.blit(pygame.transform.scale(album_pieces[fruit_album_grid], (GRID_SIZE, GRID_SIZE)), 
                           (fruit_pos[0] - pulse//2, fruit_pos[1] - pulse//2))
        else: 
            pygame.draw.rect(screen, WHITE, 
                           pygame.Rect(fruit_pos[0] - pulse//2, fruit_pos[1] - pulse//2, 
                                     GRID_SIZE + pulse, GRID_SIZE + pulse))

        show_score(screen, score)
        show_song(screen, song_display_state["name"], song_display_state["artist"])
        pygame.display.update()
        await asyncio.sleep(1/SNAKE_SPEED)

def show_score(screen, score):
    """Displays the current game score on the screen with an outline."""
    font = pygame.font.SysFont('Press Start 2P', 20) 
    score_surface = render_text_with_outline(f'Score: {score}', font, WHITE, OUTLINE_COLOR, OUTLINE_THICKNESS)
    screen.blit(score_surface, (10, 10))

def show_song(screen, track_name, track_artist):
    """Displays the currently playing song's name and artist on the screen."""
    if track_name == "N/A":
        display_text = "Song: Loading..."
    elif track_name == "No Tracks" or track_name == "Error":
        display_text = f"Song: {track_name} ({track_artist})"
    else:
        display_text = f"Playing: {track_name} - {track_artist}"
    
    font = pygame.font.SysFont('Press Start 2P', 16)
    song_surface = render_text_with_outline(display_text, font, WHITE, OUTLINE_COLOR, OUTLINE_THICKNESS)
    song_display_y = 35
    screen.blit(song_surface, (10, song_display_y))

async def winning_screen(screen, score, album_pieces):
    """Displays the winning screen, plays a victory song, and shows New Game button."""
    print("DEBUG: snake_logic.py - winning_screen called")
    print("DEBUG: snake_logic.py - Playing winning track")
    await play_track_via_backend(WINNING_TRACK_URI, 33000)
    
    font = pygame.font.SysFont('Press Start 2P', 45)
    button_font = pygame.font.SysFont('Press Start 2P', 25)
    button_rect = pygame.Rect(width // 2 - 100, height // 2 + 100, 200, 50)
    
    # Remove countdown and auto-restart. Wait for user to click NEW GAME.
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    await start_menu()
                    return

        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(LIGHT_GREY)
        
        for row in range(height // ALBUM_GRID_SIZE):
            for col in range(width // ALBUM_GRID_SIZE):
                pos = (col, row)
                if pos in album_pieces:
                    px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
                    screen.blit(album_pieces[pos], (px, py))
        
            msg1_surf = render_text_with_outline("YOU THE GOAT!", font, GREEN, OUTLINE_COLOR, OUTLINE_THICKNESS)
            msg2_surf = render_text_with_outline(f"Score: {score}", font, GREEN, OUTLINE_COLOR, OUTLINE_THICKNESS)
            screen.blit(msg1_surf, (width//2 - msg1_surf.get_width()//2, height//2 - 80))
            screen.blit(msg2_surf, (width//2 - msg2_surf.get_width()//2, height//2 + 20))
        
        # Draw New Game button
        mouse_pos = pygame.mouse.get_pos()
        if button_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, DARK_BLUE, button_rect)
        else:
            pygame.draw.rect(screen, LIGHT_BLUE, button_rect)
        
        button_text = button_font.render("NEW GAME", True, BLACK)
        button_text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, button_text_rect)
        
        pygame.display.flip()
        await asyncio.sleep(1/60)

async def trigger_easter_egg_sequence(screen, album_pieces, prev_track_name, prev_track_artist):
    """Handles the Easter egg event: plays a special song and shows a message."""
    print("DEBUG: snake_logic.py - trigger_easter_egg_sequence called")

    played_ee_successfully = await play_track_via_backend(EASTER_EGG_TRACK_URI, 176000)
    
    if not played_ee_successfully:
        print("DEBUG: snake_logic.py - Easter egg track failed to play")
        pass

    easter_egg_start_time = time.monotonic()
    while time.monotonic() - easter_egg_start_time < 3:
        for event in pygame.event.get(): 
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        for row in range(height // ALBUM_GRID_SIZE):
            for col in range(width // ALBUM_GRID_SIZE):
                pos = (col, row)
                if pos in album_pieces:
                    px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
                    screen.blit(album_pieces[pos], (px, py))
        pygame.display.flip()
        await asyncio.sleep(1/30)
        
    special_message_font = pygame.font.SysFont('Press Start 2P', 30)
    button_font = pygame.font.SysFont('Press Start 2P', 25)
    message_line0_text = "A thank you from the creator: Daniel Eskandar"
    message_line1_text = "Thank you for playing my game! I love your music taste"
    message_line2a_text = "Send me your win and get a prize (@danielllesk)"
    message_line2b_text = "PS: I need a job refer me to your friends"
    msg_surf0 = render_text_with_outline(message_line0_text, special_message_font, LIGHT_BLUE, OUTLINE_COLOR, OUTLINE_THICKNESS)
    msg_surf1 = render_text_with_outline(message_line1_text, special_message_font, LIGHT_BLUE, OUTLINE_COLOR, OUTLINE_THICKNESS)
    msg_surf2a = render_text_with_outline(message_line2a_text, special_message_font, LIGHT_BLUE, OUTLINE_COLOR, OUTLINE_THICKNESS)
    msg_surf2b = render_text_with_outline(message_line2b_text, special_message_font, LIGHT_BLUE, OUTLINE_COLOR, OUTLINE_THICKNESS)
    
    msg_rect0 = msg_surf0.get_rect(center=(width // 2, height // 2 - 120))
    msg_rect1 = msg_surf1.get_rect(center=(width // 2, height // 2 - 70)) 
    msg_rect2a = msg_surf2a.get_rect(center=(width // 2, height // 2 - 20)) 
    msg_rect2b = msg_surf2b.get_rect(center=(width // 2, height // 2 + 30)) 
    
    button_text = "Back to Start Menu"
    button_w, button_h = 400, 50
    button_x, button_y = width // 2 - button_w // 2, height // 2 + 80 
    button_rect = pygame.Rect(button_x, button_y, button_w, button_h)
    message_loop = True
    while message_loop:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return 
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    await start_menu()
                    return 
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        screen.blit(msg_surf0, msg_rect0)
        screen.blit(msg_surf1, msg_rect1)
        screen.blit(msg_surf2a, msg_rect2a)
        screen.blit(msg_surf2b, msg_rect2b)
        pygame.draw.rect(screen, LIGHT_BLUE, button_rect)
        btn_text_surf = button_font.render(button_text, True, BLACK)
        btn_text_rect = btn_text_surf.get_rect(center=button_rect.center)
        screen.blit(btn_text_surf, btn_text_rect)
        pygame.display.flip()
        await asyncio.sleep(1/30)

async def game_over(screen, score):
    """Displays the game over message and returns to the start menu after a delay."""
    print(f"DEBUG: snake_logic.py - game_over called with score: {score}")
    game_over_font = pygame.font.SysFont('Press Start 2P', 40)
    new_game_font = pygame.font.SysFont('Press Start 2P', 25)
    
    # Show game over message for 2 seconds
    start_time = time.monotonic()
    while time.monotonic() - start_time < 2:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
        
        screen.fill(BLACK)
        
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(LIGHT_GREY)
        
        msg_surface = render_text_with_outline(f'Game Over! Score: {score}', game_over_font, RED, OUTLINE_COLOR, OUTLINE_THICKNESS)
        rect = msg_surface.get_rect(center=(width // 2, height // 2))
        screen.blit(msg_surface, rect)
        pygame.display.flip()
        await asyncio.sleep(1/60)
    
    # Show "New Game" button
    button_rect = pygame.Rect(width // 2 - 100, height // 2 + 50, 200, 50)
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    # Go directly to album search instead of start menu
                    await start_game(screen)
                    return
        
        screen.fill(BLACK)
        
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(LIGHT_GREY)
        
        msg_surface = render_text_with_outline(f'Game Over! Score: {score}', game_over_font, RED, OUTLINE_COLOR, OUTLINE_THICKNESS)
        rect = msg_surface.get_rect(center=(width // 2, height // 2))
        screen.blit(msg_surface, rect)
        
        # Draw New Game button
        mouse_pos = pygame.mouse.get_pos()
        if button_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, DARK_BLUE, button_rect)
        else:
            pygame.draw.rect(screen, LIGHT_BLUE, button_rect)
        
        button_text = new_game_font.render("NEW GAME", True, BLACK)
        button_text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, button_text_rect)
        
        pygame.display.flip()
        await asyncio.sleep(1/60)