from ui import start_menu
from spotipy_handling import cleanup
import asyncio

async def main():
    try:
        await start_menu()  # Now this is properly awaited
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print("\nApplication interrupted by me (Ctrl+C).")
    finally:
        cleanup()
    await asyncio.sleep(0)
asyncio.run(main() )
if __name__ == "__main__":
    asyncio.run(main() )


