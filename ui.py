import pygame
pygame.init()
pygame.font.init()
import asyncio
import sys
import os
from shared_constants import *
from spotipy_handling import show_login_screen, cleanup, get_spotify_device

screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("SpotiSnake - Start Menu")
font = pygame.font.SysFont("Press Start 2P", 25)

def draw_button(text, x, y, w, h, inactive_color, active_color, action=None, action_arg=None, is_async_action=False):
    """Draws a clickable button and executes an action if clicked."""
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    
    button_rect = pygame.Rect(x, y, w, h)
    hovered = button_rect.collidepoint(mouse)

    if hovered:
        pygame.draw.rect(screen, active_color, button_rect)
        if click[0] == 1 and action:
            pygame.time.delay(200)
            if is_async_action:
                asyncio.create_task(action(action_arg) if action_arg is not None else action())
            else:
                if action_arg is not None:
                    action(action_arg)
                else:
                    action()
            return True
    else:
        pygame.draw.rect(screen, inactive_color, button_rect)
        
    text_surf = font.render(text, True, BLACK)
    text_rect = text_surf.get_rect(center=button_rect.center)
    screen.blit(text_surf, text_rect)
    return False

async def quit_game_async(dummy_arg=None):
    """Handles game shutdown: pauses Spotify, cleans up, and exits properly for PyInstaller."""
    try:
        if sp: 
            sp.pause_playback()
            # Give Spotify a moment to actually stop the music
            await asyncio.sleep(0.5)
    except Exception:
        pass
    
    cleanup()
    
    # Proper exit for PyInstaller
    try:
        pygame.quit()
    except:
        pass
    
    # Force exit if running as executable
    if getattr(sys, 'frozen', False):
        os._exit(0)
    else:
        sys.exit(0)

async def back_to_menu():
    """Returns to the start menu instead of quitting."""
    try:
        if sp: 
            sp.pause_playback()
    except Exception:
        pass
    # Just return to menu - no need to quit pygame

async def start_menu():
    """Displays the start menu, handles login, and starts the game or quits."""
    global sp
    running = True
    if not sp:
        temp_sp = show_login_screen(screen, font)
        if not temp_sp:
            await quit_game_async()
            return
        sp = temp_sp
    
    if sp:
        try:
            active_device_id = await asyncio.to_thread(get_spotify_device, sp)
            if active_device_id:
                await asyncio.to_thread(
                    sp.start_playback,
                    device_id=active_device_id,
                    uris=[START_MENU_URI],
                    position_ms=0
                )
        except Exception:
            pass

    button_play_text = "Play"

    button_width = 200
    button_height = 50
    button_x = width // 2 - button_width // 2
    play_button_y = height // 1.5 - button_height // 1.5

    from snake_logic import start_game

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
        
        if start_menu_bg:
            screen.blit(start_menu_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()
        
        play_button_rect = pygame.Rect(button_x, play_button_y, button_width, button_height)
        play_hovered = play_button_rect.collidepoint(mouse_pos)

        if play_hovered:
            pygame.draw.rect(screen, DARK_BLUE, play_button_rect)
            if mouse_click[0] == 1:
                pygame.time.delay(200)
                running = False
                await start_game(screen)
                break
        else:
            pygame.draw.rect(screen, LIGHT_BLUE, play_button_rect)
        
        play_text_surf = font.render(button_play_text, True, BLACK)
        play_text_rect = play_text_surf.get_rect(center=play_button_rect.center)
        screen.blit(play_text_surf, play_text_rect)

        pygame.display.update()
        await asyncio.sleep(1/60)

async def main():
    """Main asynchronous entry point for the application UI (intended to be called from main.py)."""
    await start_menu()