from ui import start_menu
from spotipy_handling import cleanup
import asyncio

async def main():
    try:
        await start_menu()  # This is async, need await
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print("\nApplication interrupted by user (Ctrl+C).")
    finally:
        cleanup()

if __name__ == "__main__":
    asyncio.run(main())


