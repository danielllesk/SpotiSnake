import pygame
import sys
from snake_logic import start_game

pygame.init()

width, height = 720, 720
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("SpotiSnake - Start Menu")
clock = pygame.time.Clock()

WHITE = (255, 255, 255)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (0, 0, 139)
BLACK = (0, 0, 0)

font = pygame.font.SysFont("Corbel", 36)


def draw_button(text, x, y, w, h, inactive_color, active_color, action=None):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()

    if x < mouse[0] < x + w and y < mouse[1] < y + h:
        pygame.draw.rect(screen, active_color, (x, y, w, h))
        if click[0] == 1 and action:
            action()
    else:
        pygame.draw.rect(screen, inactive_color, (x, y, w, h))

    text_surf = font.render(text, True, BLACK)
    text_rect = text_surf.get_rect(center=(x + w // 2, y + h // 2))
    screen.blit(text_surf, text_rect)


def quit_game():
    pygame.quit()
    sys.exit()


def start_menu():
    running = True
    while running:
        screen.fill(WHITE)

        title_text = font.render("Welcome to SpotiSnake", True, DARK_BLUE)
        title_rect = title_text.get_rect(center=(width // 2, 100))
        screen.blit(title_text, title_rect)

        draw_button("Play", 260, 200, 200, 50, LIGHT_BLUE, DARK_BLUE, lambda: start_game(start_menu))
        draw_button("Quit", 260, 280, 200, 50, LIGHT_BLUE, DARK_BLUE, quit_game)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        pygame.display.update()
        clock.tick(60)

    quit_game()
