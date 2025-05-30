from ui import start_menu
import asyncio # Import asyncio
from spotipy_handling import cleanup # Import cleanup for finalization

# pygame.init() can be called once, either here or safely within ui.py/snake_logic.py if they check
# For simplicity, if ui.py and snake_logic.py already call pygame.init(), it's okay.
# If not, it should be called before any pygame operations.
# Assuming pygame.init() is handled in the other modules as they also use pygame directly.

async def main(): # Make main async
    # pygame.init() # Typically called before any pygame screen/font operations.
    # ui.py already calls pygame.init() so it might be redundant here if start_menu is the first UI part.
    await start_menu() # Await the async start_menu function

if __name__ == "__main__":
    try:
        asyncio.run(main()) # Use asyncio.run to execute the async main function
    except (KeyboardInterrupt, SystemExit):
        print("Application explicitly exited or interrupted.")
    finally:
        cleanup() # Ensure cleanup is called when the application exits