import pygame
import time
import random
import math
from spotipy_handling import get_album_search_input, download_and_resize_album_cover, play_random_track_from_album, sp, play_specific_track
from shared_constants import *
from ui import start_menu

pygame.init()

def cut_image_into_pieces(image_surface, piece_width, piece_height):
    pieces = {}
    for row in range(0, image_surface.get_height(), piece_height):
        for col in range(0, image_surface.get_width(), piece_width):
            rect = pygame.Rect(col, row, piece_width, piece_height)
            piece = image_surface.subsurface(rect).copy()
            grid_pos = (col // piece_width, row // piece_height)
            pieces[grid_pos] = piece
    return pieces  # {(x, y): surface, ...}

def start_game(on_game_over):
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption('SpotiSnake')
    clock = pygame.time.Clock()

    # Album selection and cover processing
    album_result = get_album_search_input(screen, pygame.font.SysFont('corbel', 20))
    if not album_result:
        on_game_over() # Go back to start menu if album selection is cancelled
        return

    print(f"Selected album: {album_result['name']} by {album_result['artist']}")
    album_cover_surface = download_and_resize_album_cover(album_result['image_url'], width, height)
    if album_cover_surface is None:
        print("Failed to download or resize album cover.")
        on_game_over() # Go back to start menu
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

    # Snake game setup
    snake_pos = [width // 2, height // 2]
    snake_body = [[snake_pos[0] - i * GRID_SIZE, snake_pos[1]] for i in range(5)]
    direction = 'RIGHT'
    change_to = direction
    score = 0

    def random_fruit_pos():
        while True:
            pos = [random.randrange(0, width // GRID_SIZE) * GRID_SIZE,
                   random.randrange(0, height // GRID_SIZE) * GRID_SIZE]
            # Check if position overlaps with any revealed piece
            valid_pos = True
            for revealed_pos in revealed_pieces:
                px, py = revealed_pos[0] * ALBUM_GRID_SIZE, revealed_pos[1] * ALBUM_GRID_SIZE
                if (abs(pos[0] - px) < ALBUM_GRID_SIZE and 
                    abs(pos[1] - py) < ALBUM_GRID_SIZE):
                    valid_pos = False
                    break
            if valid_pos:
                return pos

    fruit_pos = random_fruit_pos()
    # Calculate album grid position for the fruit
    fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)

    running = True

    while running:
        # Simple pulsing effect
        pulse = 5 if int(time.time() * 2) % 2 == 0 else 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try:
                    if sp: sp.pause_playback()
                except: pass
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
            revealed_pieces.add(fruit_album_grid)

            if easter_egg_primed:
                trigger_easter_egg_sequence(screen, album_pieces, on_game_over)
                return # Exit game loop

            fruit_pos = random_fruit_pos()
            fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)
            
            if score > 0 and score % 50 == 0:
                played_successfully, track_was_easter_egg = play_random_track_from_album(album_result['uri'])
                if played_successfully and track_was_easter_egg:
                    easter_egg_primed = True
                    print("Easter Egg primed by subsequent track!")
                else:
                    easter_egg_primed = False # Reset if a non-EE track plays
            elif not played_successfully: # If initial or subsequent play failed, reset
                 easter_egg_primed = False

        # Game over conditions
        if (snake_pos[0] < 0 or snake_pos[0] >= width or
            snake_pos[1] < 0 or snake_pos[1] >= height or
            snake_pos in snake_body[1:]):
            # Stop music before game over
            try:
                if sp: sp.pause_playback()
            except: pass
            game_over(screen, score)
            return
        elif score > 990:  # Changed from == to >= to ensure it triggers
            # Stop music before winning screen
            try:
                if sp: sp.pause_playback()
            except: pass
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

        # Draw fruit as album piece
        fruit_pos_valid = True
        for pos in revealed_pieces:
            px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
            # Check if fruit position overlaps with any revealed piece
            if (abs(fruit_pos[0] - px) < ALBUM_GRID_SIZE and 
                abs(fruit_pos[1] - py) < ALBUM_GRID_SIZE):
                fruit_pos_valid = False
                break

        if fruit_pos_valid:
            if fruit_album_grid in album_pieces:
                screen.blit(pygame.transform.scale(album_pieces[fruit_album_grid], (GRID_SIZE, GRID_SIZE)), 
                           (fruit_pos[0] - pulse//2, fruit_pos[1] - pulse//2))
            else:
                pygame.draw.rect(screen, WHITE, 
                               pygame.Rect(fruit_pos[0] - pulse//2, 
                                         fruit_pos[1] - pulse//2, 
                                         GRID_SIZE + pulse, GRID_SIZE + pulse))

        show_score(screen, score)
        pygame.display.update()
        clock.tick(SNAKE_SPEED)

def show_score(screen, score):
    font = pygame.font.SysFont('Press Start 2P', 35)
    score_surface = font.render(f'Score: {score}', True, WHITE)
    screen.blit(score_surface, (10, 10))

def winning_screen(screen, score, album_pieces):
    #  album art for 5 seconds
    start_time = time.time()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Press Start 2P', 45)
    # Consider pausing game music and playing a specific winning track if desired
    # play_specific_track("spotify:track:YOUR_WINNING_TRACK_URI") 
    # For now, it seems to play the easter egg track on winning screen, which might be unintentional
    # If you want the easter egg track only for the easter egg, remove or change this line:
    # sp.start_playback(sp.devices['devices'][0]['id'], ["spotify:track:4UQMOPSUVJVicIQzjAcRRZ"], 0)
    # Let's assume for now we want to pause any game music and not start a new one here.
    try:
        if sp: sp.pause_playback() 
    except: pass

    while time.time() - start_time < 5:
        screen.fill(BLACK)
        
        # Draw all album pieces
        for row in range(height // ALBUM_GRID_SIZE):
            for col in range(width // ALBUM_GRID_SIZE):
                pos = (col, row)
                if pos in album_pieces:
                    px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
                    screen.blit(album_pieces[pos], (px, py))
        
        # Show winning message for first 3 seconds
        if time.time() - start_time < 3:
            # Split message into two lines for better fit
            msg1 = font.render("YOU THE GOAT!", True, GREEN)
            msg2 = font.render(f"Score: {score}", True, GREEN)
            screen.blit(msg1, (width//2 - msg1.get_width()//2, height//2 - 80))
            screen.blit(msg2, (width//2 - msg2.get_width()//2, height//2 + 20))
        else:
            # Show countdown for last 2 seconds
            countdown = int(5 - (time.time() - start_time))
            countdown_surface = font.render(f"Menu in {countdown}...", True, WHITE)
            screen.blit(countdown_surface, (width//2 - countdown_surface.get_width()//2, height//2))
        
        pygame.display.flip()
        clock.tick(60)  # Cap at 60 FPS
    
    start_menu()

def trigger_easter_egg_sequence(screen, album_pieces, on_game_over_callback):
    """Handles the Easter Egg sequence: play song, show album, show message, show button."""
    print("Easter Egg Triggered!")
    play_specific_track(EASTER_EGG_TRACK_URI)

    # Display full album art for 3 seconds
    easter_egg_start_time = time.time()
    clock = pygame.time.Clock()

    while time.time() - easter_egg_start_time < 3:
        screen.fill(BLACK) # Background
        for row in range(height // ALBUM_GRID_SIZE):
            for col in range(width // ALBUM_GRID_SIZE):
                pos = (col, row)
                if pos in album_pieces:
                    px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
                    screen.blit(album_pieces[pos], (px, py))
        pygame.display.flip()
        clock.tick(30)

    # Display special message and button
    special_message_font = pygame.font.SysFont('Press Start 2P', 30) # Adjusted font size
    button_font = pygame.font.SysFont('Press Start 2P', 25)
    
    message_line1 = "Congrats! You found the"
    message_line2 = "ME! - Danny" # Your special message

    msg_surf1 = special_message_font.render(message_line1, True, LIGHT_BLUE)
    msg_surf2 = special_message_font.render(message_line2, True, LIGHT_BLUE)
    
    msg_rect1 = msg_surf1.get_rect(center=(width // 2, height // 2 - 50))
    msg_rect2 = msg_surf2.get_rect(center=(width // 2, height // 2))

    button_text = "Back to Start Menu"
    button_width = 400
    button_height = 50
    button_x = width // 2 - button_width // 2
    button_y = height // 2 + 100
    button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

    message_loop = True
    while message_loop:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try:
                    if sp: sp.pause_playback()
                except: pass
                pygame.quit()
                return # Return from trigger_easter_egg_sequence if window is closed
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    start_menu() # This calls start_menu()
                    return # Exit trigger_easter_egg_sequence immediately
                           # This ensures start_menu() takes full control without this loop continuing

        screen.fill(BLACK) # Background
        screen.blit(msg_surf1, msg_rect1)
        screen.blit(msg_surf2, msg_rect2)

        # Draw button
        pygame.draw.rect(screen, LIGHT_BLUE, button_rect)
        btn_text_surf = button_font.render(button_text, True, BLACK)
        btn_text_rect = btn_text_surf.get_rect(center=button_rect.center)
        screen.blit(btn_text_surf, btn_text_rect)

        pygame.display.flip()
        clock.tick(30)

def game_over(screen, score):
    font = pygame.font.SysFont('times new roman', 45)
    msg = font.render(f'Game Over! Score: {score}', True, RED)
    rect = msg.get_rect(center=(width // 2, height // 2))
    screen.blit(msg, rect)
    pygame.display.flip()
    time.sleep(2)
    start_menu()