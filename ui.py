import pygame
import sys
from shared_constants import *

pygame.init()
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("SpotiSnake - Start Menu")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Corbel", 36)

def draw_button(text, x, y, w, h, inactive_color, active_color, action=None, action_arg=None):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    if x < mouse[0] < x + w and y < mouse[1] < y + h:
        pygame.draw.rect(screen, active_color, (x, y, w, h))
        if click[0] == 1 and action:
            action(action_arg)
    else:
        pygame.draw.rect(screen, inactive_color, (x, y, w, h))
    text_surf = font.render(text, True, BLACK)
    text_rect = text_surf.get_rect(center=(x + w // 2, y + h // 2))
    screen.blit(text_surf, text_rect)

def quit_game(n):
    pygame.quit()
    sys.exit()

def start_menu():
    running = True
    play_clicked = False
    while running:
        screen.fill(WHITE)
        title_text = font.render("Welcome to SpotiSnake", True, DARK_BLUE)
        title_rect = title_text.get_rect(center=(width // 2, 100))
        screen.blit(title_text, title_rect)
        draw_button("Play", button_x, play_button_y, button_width, button_height, LIGHT_BLUE, DARK_BLUE, lambda _: None, None)
        draw_button("Quit", button_x, quit_button_y, button_width, button_height, LIGHT_BLUE, DARK_BLUE, quit_game, 0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse = pygame.mouse.get_pos()
                if button_x < mouse[0] < play_button_y + button_x and button_width < mouse[1] < button_height + button_width:
                    play_clicked = True
                    running = False
        pygame.display.update()
        clock.tick(60)
    if play_clicked:
        from snake_logic import start_game
        start_game(screen)