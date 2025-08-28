import pygame
import asyncio
import random
import time
from shared_constants import *
from ui import start_menu, quit_game_async

def render_text_with_outline(text, font, color, outline_color, outline_thickness):
    """Render text with an outline effect."""
    text_surface = font.render(text, True, color)
    
    outline_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
    outline_surface.fill((0, 0, 0, 0))
    
    for dx in range(-outline_thickness, outline_thickness + 1):
        for dy in range(-outline_thickness, outline_thickness + 1):
            if dx != 0 or dy != 0:
                outline_surface.blit(font.render(text, True, outline_color), (dx, dy))
    
    result_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
    result_surface.blit(outline_surface, (0, 0))
    result_surface.blit(text_surface, (0, 0))
    
    return result_surface

def cut_album_into_pieces(album_cover_surface, grid_size):
    """Cut album cover into grid pieces for the snake game."""
    pieces = {}
    width, height = album_cover_surface.get_size()
    
    for row in range(height // grid_size):
        for col in range(width // grid_size):
            piece_surface = pygame.Surface((grid_size, grid_size))
            piece_surface.blit(album_cover_surface, (0, 0), 
                              (col * grid_size, row * grid_size, grid_size, grid_size))
            pieces[(col, row)] = piece_surface
    
    return pieces

async def start_game(screen):
    """Main game entry point - handles album selection and starts the game."""
    from spotipy_handling import get_album_search_input, play_track_via_backend
    
    try:
        album_result = await get_album_search_input(screen)
    except Exception as e:
        album_result = None
    
    if album_result == USER_ABORT_GAME_FROM_SEARCH:
        await start_menu()
        return
    
    if album_result == "BACK_TO_MENU":
        try:
            await play_track_via_backend(START_MENU_URI, 0)
        except Exception as e:
            pass
        await start_menu()
        return
    
    if album_result == "LOGIN_REQUESTED":
        await start_menu()
        return
    
    if not album_result:
        await start_game(screen)
        return

    image_url = album_result.get('image_url')
    if image_url is None and 'images' in album_result and album_result['images']:
        image_url = album_result['images'][0].get('url')
    
    album_cover_surface = await download_and_resize_album_cover_async(image_url, width, height)
    if album_cover_surface is None:
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

    from spotipy_handling import show_loading_screen
    await show_loading_screen(screen, f"Loading {album_result['name']}...", 1.5)

    song_display_state["name"] = "Loading first game song..."
    song_display_state["artist"] = ""
    
    try:
        from spotipy_handling import safe_pause_playback
        await safe_pause_playback()
        await asyncio.sleep(0.5)
    except Exception as e:
        pass
    
    try:
        import js
        if hasattr(js.window, 'first_song_played'):
            delattr(js.window, 'first_song_played')
    except Exception as e:
        pass
    
    from spotipy_handling import play_random_track_from_album, verify_album_playability
    
    await asyncio.sleep(0.5)
    
    album_playable = await verify_album_playability(album_result['uri'])
    if not album_playable:
        await show_loading_screen(screen, f"Error: Cannot play {album_result['name']}", 2.0)
        await show_loading_screen(screen, "Returning to album search...", 1.0)
        await start_game(screen)
        return
    
    await play_random_track_from_album(album_result['uri'], update_song_display_from_callback)
    
    await asyncio.sleep(1.5)
    
    failed_states = [
        "Loading first game song...", 
        "Error", 
        "No Tracks", 
        "Authentication Required",
        "Failed to Start",
        "Album Error",
        "Error Loading Album"
    ]
    
    if song_display_state["name"] in failed_states:
        if "Authentication Required" in song_display_state["name"]:
            await show_loading_screen(screen, "Authentication expired. Please login again.", 2.0)
            await show_loading_screen(screen, "Returning to login...", 1.0)
            await start_menu()
            return
        else:
            await show_loading_screen(screen, "Error: Failed to start music", 2.0)
            await show_loading_screen(screen, "Returning to album search...", 1.0)
            await start_game(screen)
            return
    
    await start_game_with_album(screen, album_result)

async def start_game_with_album(screen, album_result):
    """Starts the actual snake game with the selected album."""
    from spotipy_handling import download_and_resize_album_cover_async, play_random_track_from_album
    
    image_url = album_result.get('image_url')
    if image_url is None and 'images' in album_result and album_result['images']:
        image_url = album_result['images'][0].get('url')
    
    album_cover_surface = await download_and_resize_album_cover_async(image_url, width, height)
    if album_cover_surface is None:
        await start_game(screen)
        return

    song_display_state = {
        "name": "Initializing...",
        "artist": "",
        "easter_egg_primed": False
    }

    def update_song_display_from_callback(track_name, track_artist, is_ee_primed):
        nonlocal song_display_state
        song_display_state["name"] = track_name
        song_display_state["artist"] = track_artist
        song_display_state["easter_egg_primed"] = is_ee_primed

    album_pieces = cut_album_into_pieces(album_cover_surface, ALBUM_GRID_SIZE)
    total_album_pieces = (width // ALBUM_GRID_SIZE) * (height // ALBUM_GRID_SIZE)
    revealed_pieces = set()
    
    snake_pos = [width // 2, height // 2]
    snake_body = [[width // 2, height // 2], [width // 2 - GRID_SIZE, height // 2], [width // 2 - 2 * GRID_SIZE, height // 2]]
    direction = [GRID_SIZE, 0]
    
    clock = pygame.time.Clock()
    score = 0
    fruit_pos = [random.randint(0, (width - GRID_SIZE) // GRID_SIZE) * GRID_SIZE,
                 random.randint(0, (height - GRID_SIZE) // GRID_SIZE) * GRID_SIZE]
    
    current_speed = SNAKE_SPEED
    speed_increment = 1.0
    max_speed = 25
    
    last_song_change_score = 0
    song_change_threshold = 5
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and direction[0] == 0:
            direction = [-GRID_SIZE, 0]
        elif keys[pygame.K_RIGHT] and direction[0] == 0:
            direction = [GRID_SIZE, 0]
        elif keys[pygame.K_UP] and direction[1] == 0:
            direction = [0, -GRID_SIZE]
        elif keys[pygame.K_DOWN] and direction[1] == 0:
            direction = [0, GRID_SIZE]
        
        snake_pos[0] += direction[0]
        snake_pos[1] += direction[1]
        
        if (snake_pos[0] < 0 or snake_pos[0] >= width or 
            snake_pos[1] < 0 or snake_pos[1] >= height or 
            snake_pos in snake_body[1:]):
            await game_over(screen, score)
            return
        
        snake_body.insert(0, list(snake_pos))
        
        if snake_pos == fruit_pos:
            score += 1
            fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)
            revealed_pieces.add(fruit_album_grid)
            
            if song_display_state["easter_egg_primed"] and len(revealed_pieces) >= total_album_pieces * 0.8:
                await trigger_easter_egg_sequence(screen, album_pieces, song_display_state)
                await winning_screen(screen, album_result)
                return
            
            if len(revealed_pieces) >= total_album_pieces:
                await winning_screen(screen, album_result)
                return
            
            if score - last_song_change_score >= song_change_threshold:
                current_speed = min(current_speed + speed_increment, max_speed)
                last_song_change_score = score
                
                try:
                    await play_random_track_from_album(album_result['uri'], update_song_display_from_callback)
                except Exception as e:
                    pass
            
            fruit_pos = [random.randint(0, (width - GRID_SIZE) // GRID_SIZE) * GRID_SIZE,
                        random.randint(0, (height - GRID_SIZE) // GRID_SIZE) * GRID_SIZE]
        else:
            snake_body.pop()
        
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        
        for row in range(height // ALBUM_GRID_SIZE):
            for col in range(width // ALBUM_GRID_SIZE):
                pos = (col, row)
                if pos in revealed_pieces:
                    px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
                    screen.blit(album_pieces[pos], (px, py))
        
        for segment in snake_body:
            pygame.draw.rect(screen, GREEN, [segment[0], segment[1], GRID_SIZE, GRID_SIZE])
        
        if fruit_image:
            screen.blit(fruit_image, (fruit_pos[0], fruit_pos[1]))
        else:
            pygame.draw.rect(screen, RED, [fruit_pos[0], fruit_pos[1], GRID_SIZE, GRID_SIZE])
        
        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        song_text = font.render(f"Now Playing: {song_display_state['name']}", True, WHITE)
        screen.blit(song_text, (10, 40))
        
        artist_text = font.render(f"Artist: {song_display_state['artist']}", True, WHITE)
        screen.blit(artist_text, (10, 70))
        
        pygame.display.update()
        clock.tick(current_speed)
        await asyncio.sleep(0)

async def game_over(screen, score):
    """Displays the game over screen."""
    clock = pygame.time.Clock()
    
    await asyncio.sleep(2)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                retry_button_rect = pygame.Rect(width // 2 - 200, height // 2 + 50, 180, 50)
                new_game_button_rect = pygame.Rect(width // 2 + 20, height // 2 + 50, 180, 50)
                
                if retry_button_rect.collidepoint(mouse_pos):
                    await start_game(screen)
                    return
                elif new_game_button_rect.collidepoint(mouse_pos):
                    await start_game(screen)
                    return
        
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        
        game_over_text = font.render("GAME OVER", True, RED)
        score_text = font.render(f"Final Score: {score}", True, WHITE)
        
        screen.blit(game_over_text, (width // 2 - game_over_text.get_width() // 2, height // 2 - 50))
        screen.blit(score_text, (width // 2 - score_text.get_width() // 2, height // 2 - 20))
        
        retry_button_rect = pygame.Rect(width // 2 - 200, height // 2 + 50, 180, 50)
        new_game_button_rect = pygame.Rect(width // 2 + 20, height // 2 + 50, 180, 50)
        
        pygame.draw.rect(screen, LIGHT_BLUE, retry_button_rect)
        pygame.draw.rect(screen, LIGHT_BLUE, new_game_button_rect)
        
        retry_text = font.render("Retry Album", True, BLACK)
        new_game_text = font.render("New Game", True, BLACK)
        
        screen.blit(retry_text, (retry_button_rect.centerx - retry_text.get_width() // 2, retry_button_rect.centery - retry_text.get_height() // 2))
        screen.blit(new_game_text, (new_game_button_rect.centerx - new_game_text.get_width() // 2, new_game_button_rect.centery - new_game_text.get_height() // 2))
        
        pygame.display.update()
        clock.tick(30)
        await asyncio.sleep(0)

async def winning_screen(screen, album_result):
    """Displays the winning screen with easter egg."""
    from spotipy_handling import play_track_via_backend
    
    try:
        await play_track_via_backend(WINNING_TRACK_URI, 0)
    except Exception as e:
        pass
    
    clock = pygame.time.Clock()
    
    await asyncio.sleep(3)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                button_rect = pygame.Rect(width // 2 - 200, height // 2 + 100, 400, 50)
                if button_rect.collidepoint(mouse_pos):
                    await start_menu()
                    return
        
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        
        win_text = font.render("YOU WIN!", True, GREEN)
        screen.blit(win_text, (width // 2 - win_text.get_width() // 2, height // 2 - 50))
        
        button_rect = pygame.Rect(width // 2 - 200, height // 2 + 100, 400, 50)
        pygame.draw.rect(screen, LIGHT_BLUE, button_rect)
        
        button_text = font.render("Back to Start Menu", True, BLACK)
        screen.blit(button_text, (button_rect.centerx - button_text.get_width() // 2, button_rect.centery - button_text.get_height() // 2))
        
        pygame.display.update()
        clock.tick(30)
        await asyncio.sleep(0)

async def trigger_easter_egg_sequence(screen, album_pieces, song_display_state):
    """Triggers the easter egg sequence when conditions are met."""
    from spotipy_handling import play_track_via_backend
    
    prev_track_name = song_display_state["name"]
    prev_track_artist = song_display_state["artist"]
    
    try:
        await play_track_via_backend(EASTER_EGG_TRACK_URI, 176000)
    except Exception as e:
        pass
    
    easter_egg_start_time = time.monotonic()
    while time.monotonic() - easter_egg_start_time < 3:
        for event in pygame.event.get(): 
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
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

async def restart_game_with_album(screen, album_result):
    """Restarts the game with the same album without going through the search screen."""
    
    try:
        from spotipy_handling import safe_pause_playback
        await safe_pause_playback()
        await asyncio.sleep(0.5)
    except Exception as e:
        pass
    
    try:
        import js
        if hasattr(js.window, 'first_song_played'):
            delattr(js.window, 'first_song_played')
    except Exception as e:
        pass
    
    await start_game_with_album(screen, album_result)

async def start_game_with_album(screen, album_result):
    """Starts the game with a specific album (used for retry functionality)."""
    
    image_url = album_result.get('image_url')
    if image_url is None and 'images' in album_result and album_result['images']:
        image_url = album_result['images'][0].get('url')
    
    album_cover_surface = await download_and_resize_album_cover_async(image_url, width, height)
    if album_cover_surface is None:
        await start_game(screen)
        return

    song_display_state = {
        "name": "Initializing...",
        "artist": "",
        "easter_egg_primed": False
    }

    def update_song_display_from_callback(track_name, track_artist, is_ee_primed):
        nonlocal song_display_state
        song_display_state["name"] = track_name
        song_display_state["artist"] = track_artist
        song_display_state["easter_egg_primed"] = is_ee_primed

    album_pieces = cut_album_into_pieces(album_cover_surface, ALBUM_GRID_SIZE)
    total_album_pieces = (width // ALBUM_GRID_SIZE) * (height // ALBUM_GRID_SIZE)
    revealed_pieces = set()
    
    snake_pos = [width // 2, height // 2]
    snake_body = [[width // 2, height // 2], [width // 2 - GRID_SIZE, height // 2], [width // 2 - 2 * GRID_SIZE, height // 2]]
    direction = [GRID_SIZE, 0]
    
    clock = pygame.time.Clock()
    score = 0
    fruit_pos = [random.randint(0, (width - GRID_SIZE) // GRID_SIZE) * GRID_SIZE,
                 random.randint(0, (height - GRID_SIZE) // GRID_SIZE) * GRID_SIZE]
    
    current_speed = SNAKE_SPEED
    speed_increment = 1.0
    max_speed = 25
    
    last_song_change_score = 0
    song_change_threshold = 5
    
    try:
        await play_random_track_from_album(album_result['uri'], update_song_display_from_callback)
    except Exception as e:
        pass
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and direction[0] == 0:
            direction = [-GRID_SIZE, 0]
        elif keys[pygame.K_RIGHT] and direction[0] == 0:
            direction = [GRID_SIZE, 0]
        elif keys[pygame.K_UP] and direction[1] == 0:
            direction = [0, -GRID_SIZE]
        elif keys[pygame.K_DOWN] and direction[1] == 0:
            direction = [0, GRID_SIZE]
        
        snake_pos[0] += direction[0]
        snake_pos[1] += direction[1]
        
        if (snake_pos[0] < 0 or snake_pos[0] >= width or 
            snake_pos[1] < 0 or snake_pos[1] >= height or 
            snake_pos in snake_body[1:]):
            await game_over(screen, score)
            return
        
        snake_body.insert(0, list(snake_pos))
        
        if snake_pos == fruit_pos:
            score += 1
            fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)
            revealed_pieces.add(fruit_album_grid)
            
            if song_display_state["easter_egg_primed"] and len(revealed_pieces) >= total_album_pieces * 0.8:
                await trigger_easter_egg_sequence(screen, album_pieces, song_display_state)
                await winning_screen(screen, album_result)
                return
            
            if len(revealed_pieces) >= total_album_pieces:
                await winning_screen(screen, album_result)
                return
            
            if score - last_song_change_score >= song_change_threshold:
                current_speed = min(current_speed + speed_increment, max_speed)
                last_song_change_score = score
                
                try:
                    await play_random_track_from_album(album_result['uri'], update_song_display_from_callback)
                except Exception as e:
                    pass
            
            fruit_pos = [random.randint(0, (width - GRID_SIZE) // GRID_SIZE) * GRID_SIZE,
                        random.randint(0, (height - GRID_SIZE) // GRID_SIZE) * GRID_SIZE]
        else:
            snake_body.pop()
        
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        
        for row in range(height // ALBUM_GRID_SIZE):
            for col in range(width // ALBUM_GRID_SIZE):
                pos = (col, row)
                if pos in revealed_pieces:
                    px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
                    screen.blit(album_pieces[pos], (px, py))
        
        for segment in snake_body:
            pygame.draw.rect(screen, GREEN, [segment[0], segment[1], GRID_SIZE, GRID_SIZE])
        
        if fruit_image:
            screen.blit(fruit_image, (fruit_pos[0], fruit_pos[1]))
        else:
            pygame.draw.rect(screen, RED, [fruit_pos[0], fruit_pos[1], GRID_SIZE, GRID_SIZE])
        
        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        song_text = font.render(f"Now Playing: {song_display_state['name']}", True, WHITE)
        screen.blit(song_text, (10, 40))
        
        artist_text = font.render(f"Artist: {song_display_state['artist']}", True, WHITE)
        screen.blit(artist_text, (10, 70))
        
        pygame.display.update()
        clock.tick(current_speed)
        await asyncio.sleep(0)