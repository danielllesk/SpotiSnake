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
    get_album_search_input, cleanup, get_spotify_device, safe_pause_playback, backend_login, check_authenticated, play_uri_with_details
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
    
    # Show a waking up message if backend is slow
    waking_up_backend = False
    backend_checked = False
    backend_check_start = time.time()
    
    def check_backend():
        nonlocal waking_up_backend, backend_checked
        # Start a timer for slow response
        import threading
        def show_wakeup_message():
            nonlocal waking_up_backend
            waking_up_backend = True
        timer = threading.Timer(2.0, show_wakeup_message)
        timer.start()
        try:
            result = check_authenticated()
            timer.cancel()
            backend_checked = True
            waking_up_backend = False
            return result
        except Exception:
            timer.cancel()
            waking_up_backend = False
            backend_checked = True
            return False
    
    # Check if already authenticated
    print("DEBUG: ui.py - Checking if already authenticated")
    already_authenticated = await asyncio.to_thread(check_backend)
    if already_authenticated:
        print("DEBUG: ui.py - Already authenticated, skipping login")
        return True
    
    login_button = pygame.Rect(width//2 - 150, height//2 - 25, 300, 50)
    login_text_default = "Login with Spotify"
    current_login_text = login_text_default
    error_message = None
    error_timer = 0
    is_authenticating = False
    
    title_font = pygame.font.SysFont("Press Start 2P", 55)
    
    print("DEBUG: ui.py - Entering login screen loop")
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("DEBUG: ui.py - QUIT event in login screen")
                await quit_game_async()
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if login_button.collidepoint(event.pos) and not is_authenticating:
                    print("DEBUG: ui.py - Login button clicked")
                    is_authenticating = True
                    current_login_text = "Logging in..."
                    pygame.draw.rect(screen, DARK_BLUE, login_button)
                    text_surf_auth = font.render(current_login_text, True, BLACK)
                    text_rect_auth = text_surf_auth.get_rect(center=login_button.center)
                    screen.blit(text_surf_auth, text_rect_auth)
                    pygame.display.flip()

                    try:
                        print("DEBUG: ui.py - Initiating backend login")
                        backend_login()
                        print("DEBUG: ui.py - Backend login initiated")
                        
                        # Wait for authentication to complete
                        auth_success = False
                        for _ in range(30):  # Wait up to 30 seconds
                            await asyncio.sleep(1)
                            if check_authenticated():
                                print("DEBUG: ui.py - Authentication successful")
                                auth_success = True
                                break
                        if auth_success:
                            return True
                        else:
                            error_message = "Login failed. Ensure Spotify is open & Premium."
                            error_timer = time.time()
                    except Exception as e:
                        print(f"DEBUG: ui.py - Login error: {e}")
                        error_message = f"Login error: {str(e)}"
                        error_timer = time.time()
                    finally:
                        is_authenticating = False
                        current_login_text = login_text_default

        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        
        # Draw title
        title = title_font.render("Welcome to SpotiSnake!", True, BLACK)
        screen.blit(title, (width//2 - title.get_width()//2, height//4))
        
        # Draw login button
        if is_authenticating:
            button_color = DARK_BLUE
        else:
            button_color = LIGHT_BLUE
            
        pygame.draw.rect(screen, button_color, login_button)
        text_surf = font.render(current_login_text, True, BLACK)
        text_rect = text_surf.get_rect(center=login_button.center)
        screen.blit(text_surf, text_rect)
        
        # Draw instructions
        instructions = [
            "Click to login with Spotify",
            "Browser will open for log-in",
            "Return here after log-in",
            "NOTE: Spotify Premium needed and open on device"
        ]
        y_offset = height//2 + 50
        small_font = pygame.font.SysFont("Press Start 2P", 20)
        for instruction in instructions:
            text = small_font.render(instruction, True, WHITE)
            screen.blit(text, (width//2 - text.get_width()//2, y_offset))
            y_offset += 40
        
        # Draw waking up backend message if needed
        if waking_up_backend:
            wake_font = pygame.font.SysFont("Press Start 2P", 22)
            wake_text = wake_font.render("Waking up backend server...", True, LIGHT_BLUE)
            wake_rect = wake_text.get_rect(center=(width//2, height//2 - 100))
            pygame.draw.rect(screen, DARK_GREY, wake_rect.inflate(40, 20))
            screen.blit(wake_text, wake_rect)
        
        # Draw error message if any
        if error_message and time.time() - error_timer < 5:
            error_surf = small_font.render(error_message, True, RED)
            screen.blit(error_surf, (width//2 - error_surf.get_width()//2, height - 50))

        pygame.display.flip()
        clock.tick(30)

async def start_menu():
    """Displays the start menu, handles login, and starts the game or quits."""
    print("DEBUG: ui.py - start_menu called")
    
    # First, show login screen
    print("DEBUG: ui.py - Showing login screen")
    login_success = await login_screen()
    if not login_success:
        print("DEBUG: ui.py - Login failed, exiting")
        return
    
    print("DEBUG: ui.py - Login successful, showing main menu")
    
    # Play background music for the main menu
    print("DEBUG: ui.py - Playing background music")
    try:
        asyncio.create_task(asyncio.to_thread(play_uri_with_details, START_MENU_URI, 0))
        print("DEBUG: ui.py - Background music started")
    except Exception as e:
        print(f"DEBUG: ui.py - Failed to start background music: {e}")
    
    running = True
    try:
        print("DEBUG: ui.py - Attempting to get Spotify device")
        active_device_id = await get_spotify_device()
        print(f"DEBUG: ui.py - Got device ID: {active_device_id}")
        if active_device_id:
            print("DEBUG: ui.py - Device found, attempting to pause playback")
            await safe_pause_playback()
            print("DEBUG: ui.py - Playback paused successfully")
    except Exception as e:
        print(f"DEBUG: ui.py - Exception during device setup: {e}")
        import traceback
        traceback.print_exc()
        pass

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
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("DEBUG: ui.py - QUIT event received")
                await quit_game_async()
                return
        
        # Draw background
        if start_menu_bg:
            screen.blit(start_menu_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        
        # Remove welcome and instruction text
        # Only draw the play button
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()
        
        play_button_rect = pygame.Rect(button_x, play_button_y, button_width, button_height)
        play_hovered = play_button_rect.collidepoint(mouse_pos)

        if play_hovered:
            pygame.draw.rect(screen, DARK_BLUE, play_button_rect)
            if mouse_click[0] == 1:
                print("DEBUG: ui.py - Play button clicked!")
                pygame.time.delay(200)
                running = False
                print("DEBUG: ui.py - About to call start_game")
                await start_game(screen)
                print("DEBUG: ui.py - start_game completed")
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
    print("DEBUG: ui.py - main() function called")
    await start_menu()
    print("DEBUG: ui.py - main() function completed")