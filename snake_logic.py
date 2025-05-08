import pygame
import time
import random

pygame.init()

width, height = 720, 720
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

def start_game(on_game_over):
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption('SpotiSnake')
    clock = pygame.time.Clock()

    snake_speed = 17
    snake_pos = [360, 360]
    snake_body = [[360, 360], [350, 360], [340, 360]]
    direction = 'RIGHT'
    change_to = direction
    score = 0

    fruit_pos = [random.randrange(1, (width // 10)) * 10, random.randrange(1, (height // 10)) * 10]
    fruit_spawn = True

    def show_score():
        font = pygame.font.SysFont('times new roman', 20)
        score_surface = font.render('Score : ' + str(score), True, WHITE)
        screen.blit(score_surface, (10, 10))

    def game_over():
        font = pygame.font.SysFont('times new roman', 50)
        msg = font.render('Your Score is : ' + str(score), True, RED)
        rect = msg.get_rect(center=(width // 2, height // 2))
        screen.blit(msg, rect)
        pygame.display.flip()
        time.sleep(2)
        on_game_over

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
            game_over()
            return

        show_score()
        pygame.display.update()
        clock.tick(snake_speed)
