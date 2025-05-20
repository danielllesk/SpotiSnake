import pygame
import time
import random
from spotipy_handling import search_album, get_album_search_input
from shared_constants import *
import requests
from io import BytesIO

pygame.init()

def start_game():
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption('SpotiSnake')
    clock = pygame.time.Clock()

    snake_pos = [360, 360]
    snake_body = [[360, 360], [350, 360], [340, 360]]
    direction = 'RIGHT'
    change_to = direction
    score = 0

    fruit_pos = [random.randrange(1, (width // 10)) * 10, random.randrange(1, (height // 10)) * 10]
    fruit_spawn = True

    album_result = get_album_search_input(screen, pygame.font.SysFont('times new roman', 20))
    if album_result:
        print(f"Selected album: {album_result['name']} by {album_result['artist']}")

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
                snake_pos[1] -= 10
            elif direction == 'DOWN':
                snake_pos[1] += 10
            elif direction == 'LEFT':
                snake_pos[0] -= 10
            elif direction == 'RIGHT':
                snake_pos[0] += 10

            snake_body.insert(0, list(snake_pos))

            if snake_pos == fruit_pos:
                score += 10
                fruit_spawn = False
            else:
                snake_body.pop()

            if not fruit_spawn:
                fruit_pos = [random.randrange(1, (width // 10)) * 10, random.randrange(1, (height // 10)) * 10]
            fruit_spawn = True

            screen.fill(BLACK)

            for block in snake_body:
                pygame.draw.rect(screen, GREEN, pygame.Rect(block[0], block[1], 10, 10))
            pygame.draw.rect(screen, WHITE, pygame.Rect(fruit_pos[0], fruit_pos[1], 10, 10))

            if (snake_pos[0] < 0 or snake_pos[0] >= width or
                snake_pos[1] < 0 or snake_pos[1] >= height or
                snake_pos in snake_body[1:]):
                game_over(screen, score)
                return

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
    start_game()

def download_and_resize_album_cover(url, target_width, target_height):
    try:
        response = requests.get(url, verify=False)  # For dev, set verify=True for production
        response.raise_for_status()
        img_data = BytesIO(response.content)
        image = pygame.image.load(img_data)
        # Resize to fit the game area
        image = pygame.transform.scale(image, (target_width, target_height))
        return image
    except Exception as e:
        print(f"Error downloading or resizing album art: {e}")
        return None