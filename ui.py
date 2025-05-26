import pygame
import sys
from shared_constants import *
from spotipy_handling import show_login_screen

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
    try:
        sp.pause_playback()
    except:
        pass
    pygame.quit()
    sys.exit()

def start_menu():
    running = True
    play_clicked = False
    
    # Show login screen and get Spotify instance
    global sp
    sp = show_login_screen(screen, font)
    if not sp:
        quit_game(0)
        return
    
    # Start background music after successful login
    try:
        devices = sp.devices()
        if devices and devices['devices']:
            sp.start_playback(
                device_id=devices['devices'][0]['id'],
                uris=["spotify:track:2x7H4djW0LiFf1C1wzUDo9"],  # Background music track
                position_ms=0
            )
    except Exception as e:
        print(f"Error starting playback: {e}")
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game(0)
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse = pygame.mouse.get_pos()
                if button_x < mouse[0] < button_x + button_width and play_button_y < mouse[1] < play_button_y + button_height:
                    play_clicked = True
                    running = False
        
        screen.fill(DARK_GREY)
        title_text = font.render("Welcome to SpotiSnake", True, LIGHT_BLUE)
        title_rect = title_text.get_rect(center=(width // 2, 100))
        screen.blit(title_text, title_rect)
        
        # Draw buttons
        draw_button("Play", button_x, play_button_y, button_width, button_height, LIGHT_BLUE, DARK_BLUE, lambda _: None, None)
        draw_button("Quit", button_x, quit_button_y, button_width, button_height, LIGHT_BLUE, DARK_BLUE, quit_game, 0)
        
        pygame.display.update()
        clock.tick(60)
    
    if play_clicked:
        from snake_logic import start_game
        try:
            # Change music for gameplay
            devices = sp.devices()
            if devices and devices['devices']:
                sp.start_playback(
                    device_id=devices['devices'][0]['id'],
                    uris=["spotify:track:5twQjBMvQyEMekV5pvVVnI"],  # Gameplay music track
                    position_ms=3000
                )
        except Exception as e:
            print(f"Error changing music: {e}")
        start_game(screen)