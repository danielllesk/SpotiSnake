import pygame
import asyncio
import sys
import os
import time
from shared_constants import *
from spotipy_handling import check_authenticated, backend_login, play_track_via_backend, safe_pause_playback, cleanup

pygame.init()
pygame.font.init()

# Set up display
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption('SpotiSnake')
font = pygame.font.SysFont('Press Start 2P', 30)

async def quit_game_async():
    try:
        await safe_pause_playback()
        await asyncio.sleep(0.2)
    except Exception as e:
        pass
    
    try:
        await cleanup()
    except Exception as e:
        pass
    
    try:
        pygame.quit()
    except Exception as e:
        pass
    
    # Force exit if running as executable
    if getattr(sys, 'frozen', False):
        os._exit(0)
    else:
        sys.exit(0)

async def back_to_menu():
    try:
        await safe_pause_playback()
    except Exception as e:
        pass

async def login_screen():
    """Displays the Spotify login screen and handles the authentication flow."""
    clock = pygame.time.Clock()
    login_button = pygame.Rect(width//2 - 150, height//2 - 25, 300, 50)
    login_text_default = "Login with Spotify"
    current_login_text = login_text_default
    error_message = None
    error_timer = 0
    is_authenticating = False
    title_font = pygame.font.SysFont("Press Start 2P", 55)
    small_font = pygame.font.SysFont("Press Start 2P", 20)
    instructions = [
        "Click to login with Spotify",
        "Browser will open for log-in", 
        "Return here after log-in",
        "NOTE: Spotify Premium needed",
        "IMPORTANT: Open Spotify app and start playing music",
        "This is required for the game to work!"
    ]

    # Force a full redraw and clear event queue to fix first-load issues
    pygame.event.clear()
    if game_bg:
        screen.blit(game_bg, (0, 0))
    else:
        screen.fill(DARK_GREY)
    title = title_font.render("Welcome to SpotiSnake!", True, BLACK)
    screen.blit(title, (width//2 - title.get_width()//2, height//4))
    button_color = LIGHT_BLUE
    pygame.draw.rect(screen, button_color, login_button)
    text_surf = font.render(current_login_text, True, BLACK)
    text_rect = text_surf.get_rect(center=login_button.center)
    screen.blit(text_surf, text_rect)
    y_offset = height//2 + 50
    for instruction in instructions:
        text = small_font.render(instruction, True, WHITE)
        screen.blit(text, (width//2 - text.get_width()//2, y_offset))
        y_offset += 40
    pygame.display.flip()
    clock.tick(30)
    await asyncio.sleep(0)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if login_button.collidepoint(event.pos) and not is_authenticating:
                    is_authenticating = True
                    current_login_text = "Opening login..."
                    # Draw UI update for logging in
                    pygame.draw.rect(screen, DARK_BLUE, login_button)
                    text_surf_auth = font.render(current_login_text, True, BLACK)
                    text_rect_auth = text_surf_auth.get_rect(center=login_button.center)
                    screen.blit(text_surf_auth, text_rect_auth)
                    pygame.display.flip()
                    try:
                        backend_login()
                        
                        # Now wait until backend session is actually authenticated
                        wait_title = small_font.render("Complete login in the opened tab...", True, WHITE)
                        waiting = True
                        last_check = 0
                        start_time = time.time()
                        max_wait_time = 60  # 60 seconds timeout
                        while waiting:
                            # Check for timeout
                            if time.time() - start_time > max_wait_time:
                                error_message = "Login timeout. Please try again."
                                error_timer = time.time()
                                return False
                            # Process quit events while waiting
                            for ev in pygame.event.get():
                                if ev.type == pygame.QUIT:
                                    await quit_game_async()
                                    return False
                            # Redraw background and hints
                            if game_bg:
                                screen.blit(game_bg, (0, 0))
                            else:
                                screen.fill(DARK_GREY)
                            screen.blit(wait_title, (width//2 - wait_title.get_width()//2, height//2 - 10))
                            hint = small_font.render("Return here after confirming login", True, WHITE)
                            screen.blit(hint, (width//2 - hint.get_width()//2, height//2 + 20))
                            pygame.display.flip()
                            # Throttle checks
                            now = time.time()
                            if now - last_check > 0.5:
                                last_check = now
                                try:
                                    authed = await check_authenticated()
                                    if authed:
                                        return True
                                except Exception as ce:
                                    pass
                            await asyncio.sleep(0.1)
                    except Exception as e:
                        error_message = f"Login error: {str(e)}"
                        error_timer = time.time()
                    finally:
                        is_authenticating = False
                        current_login_text = login_text_default
        # Always draw the background and UI before any authentication logic
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        # Draw title
        title = title_font.render("Welcome to SpotiSnake!", True, BLACK)
        screen.blit(title, (width//2 - title.get_width()//2, height//4))
        # Draw login button
        button_color = DARK_BLUE if is_authenticating else LIGHT_BLUE
        pygame.draw.rect(screen, button_color, login_button)
        text_surf = font.render(current_login_text, True, BLACK)
        text_rect = text_surf.get_rect(center=login_button.center)
        screen.blit(text_surf, text_rect)
        # Draw instructions
        y_offset = height//2 + 50
        for instruction in instructions:
            text = small_font.render(instruction, True, WHITE)
            screen.blit(text, (width//2 - text.get_width()//2, y_offset))
            y_offset += 40
        # Draw error message if any
        if error_message and time.time() - error_timer < 5:
            error_surf = small_font.render(error_message, True, RED)
            screen.blit(error_surf, (width//2 - error_surf.get_width()//2, height - 50))
        pygame.display.flip()
        clock.tick(30)
        await asyncio.sleep(0)

async def main_menu():
    """Displays the main menu without checking authentication."""
    clock = pygame.time.Clock()
    
    # Check if we're in a browser environment for music handling
    try:
        import js
        is_browser = hasattr(js, 'window')
    except:
        is_browser = False
    
    if is_browser:
        pass  # Browser environment detected, music will be manual
    
    running = True
    button_play_text = "PLAY GAME"

    button_width = 200
    button_height = 50
    button_x = width // 2 - button_width // 2
    play_button_y = height // 1.5 - button_height // 1.5

    from snake_logic import start_game

    button_clicked = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            if event.type == pygame.MOUSEBUTTONDOWN and not button_clicked:
                mouse_pos = pygame.mouse.get_pos()
                play_button_rect = pygame.Rect(button_x, play_button_y, button_width, button_height)
                if play_button_rect.collidepoint(mouse_pos):
                    button_clicked = True
                    pygame.time.delay(200)
                    running = False
                    await start_game(screen)
                    break
        
        # Draw background
        if start_menu_bg:
            screen.blit(start_menu_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        
        # Draw the play button
        mouse_pos = pygame.mouse.get_pos()
        play_button_rect = pygame.Rect(button_x, play_button_y, button_width, button_height)
        play_hovered = play_button_rect.collidepoint(mouse_pos)

        if play_hovered:
            pygame.draw.rect(screen, DARK_BLUE, play_button_rect)
        else:
            pygame.draw.rect(screen, LIGHT_BLUE, play_button_rect)
        
        play_text_surf = font.render(button_play_text, True, BLACK)
        play_text_rect = play_text_surf.get_rect(center=play_button_rect.center)
        screen.blit(play_text_surf, play_text_rect)

        pygame.display.update()
        clock.tick(60)
        await asyncio.sleep(0)

async def start_menu():
    """Displays the start menu, handles login, and starts the game or quits."""
    clock = pygame.time.Clock()
    
    # Check if already authenticated
    is_authenticated = await check_authenticated()
    # Force login screen every time to avoid authentication/cookie issues
    is_authenticated = False
    if not is_authenticated:
        login_success = await login_screen()
        if not login_success:
            await quit_game_async()
            return
    
    # Play background music only after successful login
    try:
        await play_track_via_backend(START_MENU_URI, 0)
    except Exception as e:
        pass
    
    # Always show main menu, even if already authenticated
    await main_menu()

async def main():
    """Main asynchronous entry point for the application UI (intended to be called from main.py)."""
    await start_menu()