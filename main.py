print("PYTHON MAIN STARTED")
print("DEBUG: main.py - Starting application initialization")

print("DEBUG: main.py - About to import ui module")
from ui import start_menu
print("DEBUG: main.py - ui module imported successfully")
import asyncio
import pygame

print("DEBUG: main.py - Importing pygame")
pygame.init()
print("DEBUG: main.py - Pygame initialized successfully")
pygame.font.init()
print("DEBUG: main.py - Pygame font initialized successfully")

async def main():
    print("DEBUG: main.py - main() function entered")
    try:
        # Set up page unload handler to pause music when user leaves (non-blocking)
        try:
            from spotipy_handling import setup_page_unload_handler
            setup_page_unload_handler()
            print("DEBUG: main.py - Page unload handler set up")
        except Exception as e:
            print(f"DEBUG: main.py - Failed to set up page unload handler: {e}")
            print("DEBUG: main.py - Continuing without page unload handler")
        
        print("DEBUG: main.py - About to call start_menu()")
        await start_menu()
        print("DEBUG: main.py - start_menu() completed successfully")
    except SystemExit:
        print("DEBUG: main.py - SystemExit caught in main()")
        pass
    except KeyboardInterrupt:
        print("DEBUG: main.py - KeyboardInterrupt caught in main()")
        print("\nApplication interrupted by me (Ctrl+C).")
    except Exception as e:
        print(f"DEBUG: main.py - Unexpected exception in main(): {e}")
        import traceback
        traceback.print_exc()
    print("DEBUG: main.py - About to sleep in main()")
    await asyncio.sleep(0)
    print("DEBUG: main.py - main() function completed")

if __name__ == "__main__":
    print("DEBUG: main.py - __main__ block running")
    print("DEBUG: main.py - About to call asyncio.run(main())")
    asyncio.run(main())
    print("DEBUG: main.py - asyncio.run(main()) completed")


