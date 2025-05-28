import pygame
import time
import random
import math
from spotipy_handling import (
    get_album_search_input, download_and_resize_album_cover, 
    play_random_track_from_album, sp, play_specific_track
)
from shared_constants import *
from ui import start_menu

pygame.init()

OUTLINE_COLOR = BLACK
OUTLINE_THICKNESS = 2 # You can adjust this for a thicker/thinner outline

def render_text_with_outline(text_str, font, main_color, outline_color, thickness):
    # Render the outline text (multiple times for a thicker effect if desired)
    # For a simple outline, rendering at 4 diagonal and 4 cardinal points is common.
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
    
    # Determine the size of the final surface
    # Find max width and height considering the main text and all outline parts
    # Initial width/height is from the main text
    final_width = text_surface_main.get_width() + 2 * thickness
    final_height = text_surface_main.get_height() + 2 * thickness

    # Create a new surface with transparency for the combined text and outline
    final_surface = pygame.Surface((final_width, final_height), pygame.SRCALPHA)

    # Blit outline surfaces first, offset by thickness to center them
    for surf, (dx, dy) in outline_surfaces:
        final_surface.blit(surf, (thickness + dx, thickness + dy))
    
    # Blit the main text on top, offset by thickness
    final_surface.blit(text_surface_main, (thickness, thickness))
    
    return final_surface

def cut_image_into_pieces(image_surface, piece_width, piece_height):
    pieces = {}
    for row in range(0, image_surface.get_height(), piece_height):
        for col in range(0, image_surface.get_width(), piece_width):
            rect = pygame.Rect(col, row, piece_width, piece_height)
            piece = image_surface.subsurface(rect).copy()
            grid_pos = (col // piece_width, row // piece_height)
            pieces[grid_pos] = piece
    return pieces  # {(x, y): surface, ...}

def start_game(screen):
    pygame.display.set_caption('SpotiSnake')
    clock = pygame.time.Clock()

    # Album selection and cover processing
    album_result = get_album_search_input(screen, pygame.font.SysFont('corbel', 20))
    if not album_result:
        start_menu()
        return

    print(f"Selected album: {album_result['name']} by {album_result['artist']}")
    album_cover_surface = download_and_resize_album_cover(album_result['image_url'], width, height)
    if album_cover_surface is None:
        print("Failed to download or resize album cover.")
        start_menu()
        return

    # Variable to track if the *next* fruit eaten should trigger the Easter Egg
    easter_egg_primed = False 

    # Play first track
    played_successfully, track_was_easter_egg = play_random_track_from_album(album_result['uri'])
    if played_successfully and track_was_easter_egg:
        easter_egg_primed = True
        print("Easter Egg primed by initial track!")

    album_pieces = cut_image_into_pieces(album_cover_surface, ALBUM_GRID_SIZE, ALBUM_GRID_SIZE)
    revealed_pieces = set()

    # Calculate total number of album pieces to win
    total_album_pieces = (width // ALBUM_GRID_SIZE) * (height // ALBUM_GRID_SIZE)

    # Snake game setup
    snake_pos = [width // 2, height // 2]
    snake_body = [[snake_pos[0] - i * GRID_SIZE, snake_pos[1]] for i in range(5)]
    direction = 'RIGHT'
    change_to = direction
    score = 0

    def random_fruit_pos():
        # This function assumes there's at least one valid spot left.
        # The main game logic now prevents calling this if all spots are filled.
        while True:
            pos = [random.randrange(0, width // GRID_SIZE) * GRID_SIZE,
                   random.randrange(0, height // GRID_SIZE) * GRID_SIZE]
            valid_pos = True
            # Check if this new fruit position would be on an already revealed album piece
            # Convert fruit's top-left to album grid coordinates
            fruit_on_album_grid_col = pos[0] // ALBUM_GRID_SIZE
            fruit_on_album_grid_row = pos[1] // ALBUM_GRID_SIZE
            if (fruit_on_album_grid_col, fruit_on_album_grid_row) in revealed_pieces:
                valid_pos = False
            
            if valid_pos:
                # Additionally, ensure snake body doesn't currently occupy the fruit spawn
                # This is a basic check; more sophisticated checks might be needed if GRID_SIZE != ALBUM_GRID_SIZE
                if list(pos) not in snake_body:
                    return pos

    fruit_pos = random_fruit_pos()
    fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)

    running = True

    while running:
        # Simple pulsing effect
        pulse = 5 if int(time.time() * 2) % 2 == 0 else 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try: 
                    if sp: sp.pause_playback()
                except Exception as e: print(f"Error pausing on quit: {e}")
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

        # Update snake body positions
        for i in range(len(snake_body)-1, 0, -1):
            snake_body[i] = snake_body[i-1]
        snake_body[0] = list(snake_pos)

        if snake_pos == fruit_pos:
            score += 10
            # The fruit_album_grid is the piece that this fruit was "on"
            # Ensure this piece is not already revealed if fruit can spawn on revealed pieces
            # However, random_fruit_pos should ideally prevent spawning on revealed pieces.
            # For safety, let's use the fruit_album_grid calculated when fruit was spawned.
            if fruit_album_grid not in revealed_pieces:
                revealed_pieces.add(fruit_album_grid)

            if easter_egg_primed:
                trigger_easter_egg_sequence(screen, album_pieces)
                return

            # Check for win condition (all pieces revealed)
            if len(revealed_pieces) >= total_album_pieces: # Use >= for safety
                try: 
                    if sp: sp.pause_playback()
                except Exception as e: print(f"Error pausing before win screen: {e}")
                winning_screen(screen, score, album_pieces)
                return

            # If not won, and not easter egg, generate new fruit and continue
            fruit_pos = random_fruit_pos()
            fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)
            
            if score > 0 and score % 50 == 0:
                played_successfully, track_was_easter_egg = play_random_track_from_album(album_result['uri'])
                if played_successfully and track_was_easter_egg:
                    easter_egg_primed = True
                    print("Easter Egg primed by subsequent track!")
                else:
                    easter_egg_primed = False
            elif not played_successfully and not easter_egg_primed: # if play failed & not already primed
                easter_egg_primed = False

        # Game over by collision or boundary
        if (snake_pos[0] < 0 or snake_pos[0] >= width or
            snake_pos[1] < 0 or snake_pos[1] >= height or
            snake_pos in snake_body[1:]):
            try: 
                if sp: sp.pause_playback()
            except Exception as e: print(f"Error pausing on game over: {e}")
            game_over(screen, score)
            return
        elif score > 990 and len(revealed_pieces) >= total_album_pieces:
            try: 
                if sp: sp.pause_playback()
            except Exception as e: print(f"Error pausing before win screen (score): {e}")
            winning_screen(screen, score, album_pieces)
            return

        # Draw everything
        screen.fill(LIGHT_GREY)

        # Draw revealed album pieces
        for pos in revealed_pieces:
            px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
            screen.blit(album_pieces[pos], (px, py))

        # Draw snake
        for block in snake_body:
            pygame.draw.rect(screen, GREEN, pygame.Rect(block[0], block[1], GRID_SIZE, GRID_SIZE))

        # Drawing fruit: ensure fruit_album_grid is valid and piece exists
        if fruit_album_grid in album_pieces:
            # Check if the current fruit position would be on an already revealed piece.
            # This logic is slightly complex as fruit can be smaller than album piece.
            # The random_fruit_pos should ideally handle this.
            # We can simplify drawing if random_fruit_pos guarantees it's on an unrevealed piece.
            is_fruit_on_revealed_area = False
            fruit_col_on_album_grid = fruit_pos[0] // ALBUM_GRID_SIZE
            fruit_row_on_album_grid = fruit_pos[1] // ALBUM_GRID_SIZE
            if (fruit_col_on_album_grid, fruit_row_on_album_grid) in revealed_pieces:
                is_fruit_on_revealed_area = True

            if not is_fruit_on_revealed_area:
                screen.blit(pygame.transform.scale(album_pieces[fruit_album_grid], (GRID_SIZE, GRID_SIZE)), 
                           (fruit_pos[0] - pulse//2, fruit_pos[1] - pulse//2))
        else: # Fallback if fruit_album_grid isn't in album_pieces (shouldn't happen with good random_fruit_pos)
            pygame.draw.rect(screen, WHITE, 
                           pygame.Rect(fruit_pos[0] - pulse//2, 
                                     fruit_pos[1] - pulse//2, 
                                     GRID_SIZE + pulse, GRID_SIZE + pulse))

        show_score(screen, score)
        pygame.display.update()
        clock.tick(SNAKE_SPEED)

def show_score(screen, score):
    font = pygame.font.SysFont('Press Start 2P', 35)
    score_surface = render_text_with_outline(f'Score: {score}', font, WHITE, OUTLINE_COLOR, OUTLINE_THICKNESS)
    screen.blit(score_surface, (10, 10))

def winning_screen(screen, score, album_pieces):
    #  album art for 8 seconds (changed from 5)
    start_time = time.time()
    WINNING_SCREEN_DURATION = 8 # Changed from 5
    COUNTDOWN_START_TIME = 3 # Start countdown in the last N seconds

    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Press Start 2P', 45)
    # Pause is called before entering this screen
    while time.time() - start_time < WINNING_SCREEN_DURATION:
        screen.fill(BLACK)
        for row in range(height // ALBUM_GRID_SIZE):
            for col in range(width // ALBUM_GRID_SIZE):
                pos = (col, row)
                if pos in album_pieces:
                    px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
                    screen.blit(album_pieces[pos], (px, py))
        
        elapsed_time = time.time() - start_time
        # Show winning message for first (WINNING_SCREEN_DURATION - COUNTDOWN_START_TIME) seconds
        if elapsed_time < (WINNING_SCREEN_DURATION - COUNTDOWN_START_TIME):
            msg1_surf = render_text_with_outline("YOU THE GOAT!", font, GREEN, OUTLINE_COLOR, OUTLINE_THICKNESS)
            msg2_surf = render_text_with_outline(f"Score: {score}", font, GREEN, OUTLINE_COLOR, OUTLINE_THICKNESS)
            screen.blit(msg1_surf, (width//2 - msg1_surf.get_width()//2, height//2 - 80))
            screen.blit(msg2_surf, (width//2 - msg2_surf.get_width()//2, height//2 + 20))
        else:
            # Show countdown for last COUNTDOWN_START_TIME seconds
            countdown = int(WINNING_SCREEN_DURATION - elapsed_time)
            if countdown < 0: countdown = 0 # Ensure countdown doesn't go negative
            countdown_surface = render_text_with_outline(f"Menu in {countdown}...", font, WHITE, OUTLINE_COLOR, OUTLINE_THICKNESS)
            screen.blit(countdown_surface, (width//2 - countdown_surface.get_width()//2, height//2))
        
        pygame.display.flip()
        clock.tick(60)
    start_menu()

def trigger_easter_egg_sequence(screen, album_pieces):
    print("Easter Egg Triggered!")
    play_specific_track(EASTER_EGG_TRACK_URI)
    easter_egg_start_time = time.time()
    clock = pygame.time.Clock()
    while time.time() - easter_egg_start_time < 3:
        screen.fill(BLACK)
        for row in range(height // ALBUM_GRID_SIZE):
            for col in range(width // ALBUM_GRID_SIZE):
                pos = (col, row)
                if pos in album_pieces:
                    px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
                    screen.blit(album_pieces[pos], (px, py))
        pygame.display.flip()
        clock.tick(30)
        
    special_message_font = pygame.font.SysFont('Press Start 2P', 30)
    button_font = pygame.font.SysFont('Press Start 2P', 25)
    
    message_line1 = "Congrats! You found the"
    message_line2 = "ME! - Danny"

    msg_surf1 = render_text_with_outline(message_line1, special_message_font, LIGHT_BLUE, OUTLINE_COLOR, OUTLINE_THICKNESS)
    msg_surf2 = render_text_with_outline(message_line2, special_message_font, LIGHT_BLUE, OUTLINE_COLOR, OUTLINE_THICKNESS)
    
    msg_rect1 = msg_surf1.get_rect(center=(width // 2, height // 2 - 50))
    msg_rect2 = msg_surf2.get_rect(center=(width // 2, height // 2))

    button_text = "Back to Start Menu"
    button_w = 400 # Renamed from button_width to avoid conflict with global if any
    button_h = 50  # Renamed from button_height
    button_x = width // 2 - button_w // 2
    button_y = height // 2 + 100
    button_rect = pygame.Rect(button_x, button_y, button_w, button_h)
    message_loop = True
    while message_loop:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try: 
                    if sp: sp.pause_playback()
                except Exception as e: print(f"Error pausing on Easter Egg quit: {e}")
                pygame.quit()
                return 
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    # The Easter egg song is short; letting it play out or be cut by next screen
                    start_menu() 
                    return 
        screen.fill(BLACK) 
        screen.blit(msg_surf1, msg_rect1)
        screen.blit(msg_surf2, msg_rect2)

        pygame.draw.rect(screen, LIGHT_BLUE, button_rect)
        # Button text usually doesn't need outline if on solid background, but can be added if needed
        btn_text_surf = button_font.render(button_text, True, BLACK)
        btn_text_rect = btn_text_surf.get_rect(center=button_rect.center)
        screen.blit(btn_text_surf, btn_text_rect)

        pygame.display.flip()
        clock.tick(30)

def game_over(screen, score):
    game_over_font = pygame.font.SysFont('Press Start 2P', 40) # Example of using consistent font
    msg_surface = render_text_with_outline(f'Game Over! Score: {score}', game_over_font, RED, OUTLINE_COLOR, OUTLINE_THICKNESS)
    rect = msg_surface.get_rect(center=(width // 2, height // 2))
    screen.blit(msg_surface, rect)
    pygame.display.flip()
    time.sleep(2)
    start_menu()