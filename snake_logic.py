import pygame
import time
import random
import math
from spotipy_handling import get_album_search_input, download_and_resize_album_cover, play_random_track_from_album
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
    start_time = time.time()

    # Album selection and cover processing
    album_result = get_album_search_input(screen, pygame.font.SysFont('times new roman', 20))
    if not album_result:
        return

    print(f"Selected album: {album_result['name']} by {album_result['artist']}")
    album_cover_surface = download_and_resize_album_cover(album_result['image_url'], width, height)
    if album_cover_surface is None:
        print("Failed to download or resize album cover.")
        return

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
    # Calculate both snake grid and album grid positions
    fruit_snake_grid = (fruit_pos[0] // GRID_SIZE, fruit_pos[1] // GRID_SIZE)
    fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)

    running = True

    while running:
        # Simple pulsing effect
        pulse = 5 if int(time.time() * 2) % 2 == 0 else 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
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
            fruit_pos = random_fruit_pos()
            fruit_snake_grid = (fruit_pos[0] // GRID_SIZE, fruit_pos[1] // GRID_SIZE)
            fruit_album_grid = (fruit_pos[0] // ALBUM_GRID_SIZE, fruit_pos[1] // ALBUM_GRID_SIZE)
            
            # Play new track every 5 pieces of fruit
            if score == 0 or score % 50 == 0:
                play_random_track_from_album(album_result['uri'])

        # Game over conditions
        if (snake_pos[0] < 0 or snake_pos[0] >= width or
            snake_pos[1] < 0 or snake_pos[1] >= height or
            snake_pos in snake_body[1:]):
            game_over(screen, score)
            return
        elif score == 1000:
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
    font = pygame.font.SysFont('times new roman', 20)
    score_surface = font.render('Score : ' + str(score), True, WHITE)
    screen.blit(score_surface, (10, 10))

def winning_screen(screen, score, album_pieces):
    # Show album art for 5 seconds
    start_time = time.time()
    clock = pygame.time.Clock()
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
            font = pygame.font.SysFont('times new roman', 50)
            score_surface = font.render("YOU THE GOAT!\nYour Score is: " + str(score), True, GREEN)
            screen.blit(score_surface, (width//2 - score_surface.get_width()//2, height//2 - score_surface.get_height()//2))
        else:
            # Show countdown for last 2 seconds
            font = pygame.font.SysFont('times new roman', 50)
            countdown = int(5 - (time.time() - start_time))
            countdown_surface = font.render(f"Returning to menu in {countdown}...", True, WHITE)
            screen.blit(countdown_surface, (width//2 - countdown_surface.get_width()//2, height//2))
        
        pygame.display.flip()
        clock.tick(60)  # Cap at 60 FPS
    
    start_menu()

def game_over(screen, score):
    font = pygame.font.SysFont('times new roman', 50)
    msg = font.render('Your Score is : ' + str(score), True, RED)
    rect = msg.get_rect(center=(width // 2, height // 2))
    screen.blit(msg, rect)
    pygame.display.flip()
    time.sleep(2)
    start_menu()