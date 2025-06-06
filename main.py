from ui import start_menu
from spotipy_handling import cleanup
import asyncio

async def main():
    await start_menu()  # Await your async start menu

if __name__ == "__main__":
    try:
        asyncio.run(main())  # Only run it once!
    except SystemExit:
        pass  # Allow clean exit
    except KeyboardInterrupt:
        print("\nApplication interrupted by user (Ctrl+C).")
    finally:
        cleanup()  # Ensure cleanup

