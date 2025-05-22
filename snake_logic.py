import pygame
import time
import random
from spotipy_handling import get_album_search_input, download_and_resize_album_cover
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
    album_result = get_album_search_input(screen, pygame.font.SysFont('times new roman', 20))
    if not album_result:
        return

    print(f"Selected album: {album_result['name']} by {album_result['artist']}")
    album_cover_surface = download_and_resize_album_cover(album_result['image_url'], width, height)
    if album_cover_surface is None:
        print("Failed to download or resize album cover.")
        return

    album_pieces = cut_image_into_pieces(album_cover_surface, GRID_SIZE, GRID_SIZE)
    revealed_pieces = set()

    # Snake game setup
    snake_length = 5  # Fixed length
    snake_pos = [width // 2, height // 2]
    snake_body = [[snake_pos[0] - i * GRID_SIZE, snake_pos[1]] for i in range(snake_length)]
    direction = 'RIGHT'
    change_to = direction
    score = 0

    def random_fruit_pos():
        return [random.randrange(0, width // GRID_SIZE) * GRID_SIZE,
                random.randrange(0, height // GRID_SIZE) * GRID_SIZE]

    fruit_pos = random_fruit_pos()
    fruit_grid_pos = (fruit_pos[0] // GRID_SIZE, fruit_pos[1] // GRID_SIZE)

    running = True

    while running:
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

        snake_body.insert(0, list(snake_pos))

        if len(snake_body) > snake_length:
            snake_body.pop()

        if snake_pos == fruit_pos:
            score += 10
            revealed_pieces.add(fruit_grid_pos)
            fruit_pos = random_fruit_pos()
            fruit_grid_pos = (fruit_pos[0] // GRID_SIZE, fruit_pos[1] // GRID_SIZE)


        # Game over conditions
        if (snake_pos[0] < 0 or snake_pos[0] >= width or
            snake_pos[1] < 0 or snake_pos[1] >= height or
            snake_pos in snake_body[1:]):
            game_over(screen, score)
            return

        # Draw background
        screen.fill(BLACK)

        # Draw revealed album pieces
        for pos in revealed_pieces:
            px, py = pos[0] * GRID_SIZE, pos[1] * GRID_SIZE
            screen.blit(album_pieces[pos], (px, py))

        # Draw snake
        for block in snake_body:
            pygame.draw.rect(screen, GREEN, pygame.Rect(block[0], block[1], GRID_SIZE, GRID_SIZE))

        # Draw fruit as album piece
        if fruit_grid_pos in album_pieces:
            screen.blit(album_pieces[fruit_grid_pos], (fruit_pos[0], fruit_pos[1]))
        else:
            pygame.draw.rect(screen, WHITE, pygame.Rect(fruit_pos[0], fruit_pos[1], GRID_SIZE, GRID_SIZE))

        show_score(screen, score)
        pygame.display.update()
        clock.tick(SNAKE_SPEED)

def show_score(screen, score):
    font = pygame.font.SysFont('times new roman', 20)
    score_surface = font.render('Score : ' + str(score), True, WHITE)
    screen.blit(score_surface, (10, 10))

def game_over(screen, score):
    font = pygame.font.SysFont('times new roman', 50)
    msg = font.render('Your Score is : ' + str(score), True, RED)
    rect = msg.get_rect(center=(width // 2, height // 2))
    screen.blit(msg, rect)
    pygame.display.flip()
    time.sleep(2)
    start_menu()