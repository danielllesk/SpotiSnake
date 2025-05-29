import pygame
import sys
import asyncio
from shared_constants import *
from spotipy_handling import show_login_screen, sp, cleanup

pygame.init()
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("SpotiSnake - Start Menu")
font = pygame.font.SysFont("Press Start 2P", 25)

def draw_button(text, x, y, w, h, inactive_color, active_color, action=None, action_arg=None, is_async_action=False):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    if x < mouse[0] < x + w and y < mouse[1] < y + h:
        pygame.draw.rect(screen, active_color, (x, y, w, h))
        if click[0] == 1 and action:
            if is_async_action:
                asyncio.create_task(action(action_arg))
            else:
                action(action_arg)
            return True
    else:
        pygame.draw.rect(screen, inactive_color, (x, y, w, h))
    text_surf = font.render(text, True, BLACK)
    text_rect = text_surf.get_rect(center=(x + w // 2, y + h // 2))
    screen.blit(text_surf, text_rect)
    return False

async def quit_game_async(n):
    print("Quit game called")
    try:
        if sp: sp.pause_playback()
    except Exception as e:
        print(f"Error pausing playback on quit: {e}")
    cleanup()
    pygame.quit()
    sys.exit()

async def start_menu():
    global sp
    running = True
    play_clicked = False

    if not sp:
        sp = show_login_screen(screen, font)
        if not sp:
            await quit_game_async(0)
            return
    
    try:
        devices = sp.devices()
        if devices and devices['devices']:
            sp.start_playback(
                device_id=devices['devices'][0]['id'],
                uris=["spotify:track:2x7H4djW0LiFf1C1wzUDo9"],
                position_ms=0
            )
    except Exception as e:
        print(f"Error starting menu playback: {e}")
    
    button_play_text = "Play"
    button_quit_text = "Quit"

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async(0)
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_x < pygame.mouse.get_pos()[0] < button_x + button_width and \
                   play_button_y < pygame.mouse.get_pos()[1] < play_button_y + button_height:
                    play_clicked = True
                    running = False
                elif button_x < pygame.mouse.get_pos()[0] < button_x + button_width and \
                     quit_button_y < pygame.mouse.get_pos()[1] < quit_button_y + button_height:
                    await quit_game_async(0)
                    return
        
        screen.fill(DARK_GREY)
        title_font = pygame.font.SysFont("Press Start 2P", 45)
        title_text = title_font.render("SpotiSnake", True, LIGHT_BLUE)
        title_rect = title_text.get_rect(center=(width // 2, 100))
        screen.blit(title_text, title_rect)
        
        mouse_pos = pygame.mouse.get_pos()
        
        play_button_rect = pygame.Rect(button_x, play_button_y, button_width, button_height)
        if play_button_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, DARK_BLUE, play_button_rect)
        else:
            pygame.draw.rect(screen, LIGHT_BLUE, play_button_rect)
        play_text_surf = font.render(button_play_text, True, BLACK)
        play_text_rect = play_text_surf.get_rect(center=play_button_rect.center)
        screen.blit(play_text_surf, play_text_rect)

        quit_button_rect = pygame.Rect(button_x, quit_button_y, button_width, button_height)
        if quit_button_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, DARK_BLUE, quit_button_rect)
        else:
            pygame.draw.rect(screen, LIGHT_BLUE, quit_button_rect)
        quit_text_surf = font.render(button_quit_text, True, BLACK)
        quit_text_rect = quit_text_surf.get_rect(center=quit_button_rect.center)
        screen.blit(quit_text_surf, quit_text_rect)
        
        pygame.display.update()
        await asyncio.sleep(1/60)
    
    if play_clicked:
        from snake_logic import start_game
        await start_game(screen)

async def main():
    await start_menu()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Application exiting...")
    finally:
        cleanup()