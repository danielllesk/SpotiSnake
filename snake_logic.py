import pygame
import time
import random
import asyncio
import traceback
from spotipy_handling import (
    get_album_search_input, download_and_resize_album_cover, 
    play_random_track_from_album, play_uri_with_details
)
from shared_constants import * 
from ui import start_menu, quit_game_async

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
    pygame.display.set_caption('SpotiSnake')

    album_result = None
    test_font_object = None

    try:
        test_font_object = pygame.font.SysFont('corbel', 20)
    except Exception:
        traceback.print_exc()
        await asyncio.sleep(1)
        try:
            fallback_font = pygame.font.SysFont('sans', 20) 
            album_result = await get_album_search_input(screen, fallback_font)
        except Exception:
            traceback.print_exc()
            await start_menu()
            return
    else:
        try:
            album_result = await get_album_search_input(screen, test_font_object)
        except Exception:
            traceback.print_exc()
            await start_menu()
            return

    if album_result == USER_ABORT_GAME_FROM_SEARCH:
        await quit_game_async()
        return
    
    if album_result == "BACK_TO_MENU":
        await start_menu()
        return
    
    if not album_result:
        await quit_game_async()
        return

    album_cover_surface = download_and_resize_album_cover(album_result['image_url'], width, height)
    if album_cover_surface is None:
        await start_menu()
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

    song_display_state["name"] = "Loading first game song..."
    song_display_state["artist"] = ""
    asyncio.create_task(play_random_track_from_album(album_result['uri'], update_song_display_from_callback))

    album_pieces = cut_image_into_pieces(album_cover_surface, ALBUM_GRID_SIZE, ALBUM_GRID_SIZE)
    revealed_pieces = set()
    total_album_pieces = (width // ALBUM_GRID_SIZE) * (height // ALBUM_GRID_SIZE)

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

    while running:
        current_time = time.monotonic()
        if current_time - last_pulse_time > pulse_interval:
            pulse_on = not pulse_on
            last_pulse_time = current_time
        pulse = 5 if pulse_on else 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try: 
                    if sp: sp.pause_playback()
                except Exception:
                    pass
                pygame.quit()
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
            if fruit_album_grid not in revealed_pieces:
                revealed_pieces.add(fruit_album_grid)

            if song_display_state["easter_egg_primed"]:
                await trigger_easter_egg_sequence(screen, album_pieces, song_display_state["name"], song_display_state["artist"])
                return

            if len(revealed_pieces) >= total_album_pieces:
                try: 
                    if sp: sp.pause_playback()
                except Exception:
                    pass
                await winning_screen(screen, score, album_pieces)
                return

            fruit_pos = random_fruit_pos()
            fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)
            
            if score > 0 and score % 50 == 0:
                song_display_state["name"] = "Changing song..."
                song_display_state["artist"] = ""
                asyncio.create_task(play_random_track_from_album(album_result['uri'], update_song_display_from_callback))

        if (snake_pos[0] < 0 or snake_pos[0] >= width or
            snake_pos[1] < 0 or snake_pos[1] >= height or
            snake_pos in snake_body[1:]):
            try: 
                if sp: sp.pause_playback()
            except Exception:
                pass
            await game_over(screen, score)
            return
        elif score > 990 and len(revealed_pieces) >= total_album_pieces:
            try: 
                if sp: sp.pause_playback()
            except Exception:
                pass
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
    start_time = time.monotonic()
    WINNING_SCREEN_DURATION = 8
    COUNTDOWN_START_TIME = 3
    
    _, _, _ = await asyncio.to_thread(
        play_uri_with_details, 
        WINNING_TRACK_URI, 
        33000
    )
    
    font = pygame.font.SysFont('Press Start 2P', 45)
    button_font = pygame.font.SysFont('Press Start 2P', 25)
    button_rect = pygame.Rect(width // 2 - 100, height // 2 + 100, 200, 50)
    
    while time.monotonic() - start_time < WINNING_SCREEN_DURATION:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try: 
                    if sp: sp.pause_playback()
                except Exception:
                    pass
                pygame.quit()
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
        
        elapsed_time = time.monotonic() - start_time
        if elapsed_time < (WINNING_SCREEN_DURATION - COUNTDOWN_START_TIME):
            msg1_surf = render_text_with_outline("YOU THE GOAT!", font, GREEN, OUTLINE_COLOR, OUTLINE_THICKNESS)
            msg2_surf = render_text_with_outline(f"Score: {score}", font, GREEN, OUTLINE_COLOR, OUTLINE_THICKNESS)
            screen.blit(msg1_surf, (width//2 - msg1_surf.get_width()//2, height//2 - 80))
            screen.blit(msg2_surf, (width//2 - msg2_surf.get_width()//2, height//2 + 20))
        else:
            countdown = int(WINNING_SCREEN_DURATION - elapsed_time)
            if countdown < 0: countdown = 0 
            countdown_surface = render_text_with_outline(f"New Game in {countdown}...", font, WHITE, OUTLINE_COLOR, OUTLINE_THICKNESS)
            screen.blit(countdown_surface, (width//2 - countdown_surface.get_width()//2, height//2))
        
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
    
    # Auto-start new game after countdown
    await start_menu()

async def trigger_easter_egg_sequence(screen, album_pieces, prev_track_name, prev_track_artist):
    """Handles the Easter egg event: plays a special song and shows a message."""

    played_ee_successfully, _, _ = await asyncio.to_thread(
        play_uri_with_details, 
        EASTER_EGG_TRACK_URI, 
        176000
    )
    
    if not played_ee_successfully:
        pass

    easter_egg_start_time = time.monotonic()
    while time.monotonic() - easter_egg_start_time < 3:
        for event in pygame.event.get(): 
            if event.type == pygame.QUIT:
                try: 
                    if sp: sp.pause_playback()
                except Exception:
                    pass
                pygame.quit()
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
    message_line0_text = "A thank you from the creator:"
    message_line1_text = "I love your music taste and thank you for playing my game"
    message_line2a_text = "But if you used the code to find the song you're a cheater"
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
                try: 
                    if sp: sp.pause_playback()
                except Exception:
                    pass
                pygame.quit()
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
                    await start_menu()
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