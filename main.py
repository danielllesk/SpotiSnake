from ui import start_menu
import asyncio 
from spotipy_handling import cleanup 

async def main():
    await start_menu() # Await the async start_menu function

if __name__ == "__main__":
    try:
        asyncio.run(main()) 
    except SystemExit:
        pass # Allow clean exit
    except KeyboardInterrupt:
        print("\nApplication interrupted by user (Ctrl+C).")
    finally:
        cleanup() # Ensure Spotify is paused etc.