print("UI MODULE LOADED")
print("DEBUG: ui.py - Starting UI module initialization")

import pygame
print("DEBUG: ui.py - Importing pygame")
pygame.init()
print("DEBUG: ui.py - Pygame initialized in ui module")
pygame.font.init()
print("DEBUG: ui.py - Pygame font initialized in ui module")
import asyncio
import sys
import os
import time
print("DEBUG: ui.py - Importing shared_constants")
from shared_constants import *
print("DEBUG: ui.py - Importing spotipy_handling functions")
from spotipy_handling import (
    get_album_search_input, cleanup, get_spotify_device, safe_pause_playback, backend_login, check_authenticated, play_uri_with_details, play_track_via_backend
)
print("DEBUG: ui.py - All imports completed successfully")

print("DEBUG: ui.py - Setting up pygame display")
screen = pygame.display.set_mode((width, height))
print(f"DEBUG: ui.py - Display set to {width}x{height}")
pygame.display.set_caption("SpotiSnake - Start Menu")
print("DEBUG: ui.py - Window caption set")
font = pygame.font.SysFont("Press Start 2P", 25)
print("DEBUG: ui.py - Font initialized")

async def quit_game_async(dummy_arg=None):
    """Handles game shutdown: pauses Spotify, cleans up, and exits properly for PyInstaller."""
    print("DEBUG: ui.py - quit_game_async called")
    try:
        print("DEBUG: ui.py - Attempting to pause playback")
        await safe_pause_playback()
        print("DEBUG: ui.py - Playback paused successfully")
        # Give Spotify a moment to actually stop the music
        await asyncio.sleep(0.5)
        print("DEBUG: ui.py - Sleep completed after pause")
    except Exception as e:
        print(f"DEBUG: ui.py - Exception during pause: {e}")
        pass
    
    print("DEBUG: ui.py - Calling cleanup")
    await cleanup()
    print("DEBUG: ui.py - Cleanup completed")
    
    # Proper exit for PyInstaller
    try:
        print("DEBUG: ui.py - Quitting pygame")
        pygame.quit()
        print("DEBUG: ui.py - Pygame quit successfully")
    except Exception as e:
        print(f"DEBUG: ui.py - Exception during pygame quit: {e}")
        pass
    
    # Force exit if running as executable
    if getattr(sys, 'frozen', False):
        print("DEBUG: ui.py - Running as frozen executable, using os._exit(0)")
        os._exit(0)
    else:
        print("DEBUG: ui.py - Running as script, using sys.exit(0)")
        sys.exit(0)

async def back_to_menu():
    """Returns to the start menu instead of quitting."""
    print("DEBUG: ui.py - back_to_menu called")
    try:
        print("DEBUG: ui.py - Attempting to pause playback in back_to_menu")
        await safe_pause_playback()
        print("DEBUG: ui.py - Playback paused successfully in back_to_menu")
    except Exception as e:
        print(f"DEBUG: ui.py - Exception during pause in back_to_menu: {e}")
        pass
    print("DEBUG: ui.py - back_to_menu completed")
    # Just return to menu - no need to quit pygame

async def login_screen():
    """Displays the Spotify login screen and handles the authentication flow."""
    print("DEBUG: ui.py - login_screen called")
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

    print("DEBUG: ui.py - Starting login screen loop")
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if login_button.collidepoint(event.pos) and not is_authenticating:
                    print("DEBUG: ui.py - Login button clicked")
                    is_authenticating = True
                    current_login_text = "Opening login..."
                    # Draw UI update for logging in
                    pygame.draw.rect(screen, DARK_BLUE, login_button)
                    text_surf_auth = font.render(current_login_text, True, BLACK)
                    text_rect_auth = text_surf_auth.get_rect(center=login_button.center)
                    screen.blit(text_surf_auth, text_rect_auth)
                    pygame.display.flip()
                    try:
                        print("DEBUG: ui.py - Initiating backend login")
                        backend_login()
                        print("DEBUG: ui.py - Backend login initiated")
                        
                        # Now wait until backend session is actually authenticated
                        print("DEBUG: ui.py - Waiting for backend authentication (/me)")
                        wait_title = small_font.render("Complete login in the opened tab...", True, WHITE)
                        waiting = True
                        last_check = 0
                        start_time = time.time()
                        max_wait_time = 60  # 60 seconds timeout
                        while waiting:
                            # Check for timeout
                            if time.time() - start_time > max_wait_time:
                                print("DEBUG: ui.py - Authentication timeout after 60 seconds")
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
                                    print(f"DEBUG: ui.py - Auth check result: {authed}")
                                    if authed:
                                        print("DEBUG: ui.py - Authentication confirmed by backend")
                                        return True
                                except Exception as ce:
                                    print(f"DEBUG: ui.py - Auth check error: {ce}")
                            await asyncio.sleep(0.1)
                    except Exception as e:
                        print(f"DEBUG: ui.py - Login error: {e}")
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
    print("DEBUG: ui.py - main_menu called (no auth check)")
    clock = pygame.time.Clock()
    

    
    # Show message about music in browser
    browser_mode = False
    try:
        from spotipy_handling import is_pyodide
        browser_mode = is_pyodide()
        if browser_mode:
            print("DEBUG: ui.py - Browser environment detected, music will be manual")
    except Exception as e:
        print(f"DEBUG: ui.py - Could not check environment: {e}")
    
    running = True
    button_play_text = "PLAY GAME"
    print(f"DEBUG: ui.py - Play button text set to: {button_play_text}")

    button_width = 200
    button_height = 50
    button_x = width // 2 - button_width // 2
    play_button_y = height // 1.5 - button_height // 1.5
    print(f"DEBUG: ui.py - Button dimensions: {button_width}x{button_height}, position: ({button_x}, {play_button_y})")

    print("DEBUG: ui.py - Importing snake_logic")
    from snake_logic import start_game
    print("DEBUG: ui.py - snake_logic imported successfully")

    print("DEBUG: ui.py - Entering main menu loop")
    button_clicked = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("DEBUG: ui.py - QUIT event received")
                await quit_game_async()
                return
            if event.type == pygame.MOUSEBUTTONDOWN and not button_clicked:
                mouse_pos = pygame.mouse.get_pos()
                play_button_rect = pygame.Rect(button_x, play_button_y, button_width, button_height)
                if play_button_rect.collidepoint(mouse_pos):
                    print("DEBUG: ui.py - Play button clicked!")
                    button_clicked = True
                    pygame.time.delay(200)
                    running = False
                    print("DEBUG: ui.py - About to call start_game")
                    await start_game(screen)
                    print("DEBUG: ui.py - start_game completed")
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
    print("DEBUG: ui.py - start_menu called")
    clock = pygame.time.Clock()
    
    # Check if already authenticated
    print("DEBUG: ui.py - Checking if already authenticated")
    is_authenticated = await check_authenticated()
    if not is_authenticated:
        print("DEBUG: ui.py - Not authenticated, showing login screen")
        login_success = await login_screen()
        if not login_success:
            print("DEBUG: ui.py - Login failed, exiting")
            await quit_game_async()
            return
        print("DEBUG: ui.py - Login successful")
    else:
        print("DEBUG: ui.py - Already authenticated, proceeding to main menu")
    
    print("DEBUG: ui.py - Proceeding to main menu")
    
    # Play background music only after successful login
    print("DEBUG: ui.py - Playing background music after login")
    try:
        await play_track_via_backend(START_MENU_URI, 0)
        print("DEBUG: ui.py - Background music started after login")
    except Exception as e:
        print(f"DEBUG: ui.py - Failed to start background music: {e}")
    
    # Always show main menu, even if already authenticated
    print("DEBUG: ui.py - Showing main menu")
    await main_menu()

async def main():
    """Main asynchronous entry point for the application UI (intended to be called from main.py)."""
    print("DEBUG: ui.py - main() function called")
    await start_menu()
    print("DEBUG: ui.py - main() function completed")