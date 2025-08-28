from ui import start_menu
import asyncio
import pygame

pygame.init()
pygame.font.init()

async def main():
    try:
        try:
            from spotipy_handling import setup_page_unload_handler
            setup_page_unload_handler()
        except Exception as e:
            pass
        
        await start_menu()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print("\nApplication interrupted by user (Ctrl+C).")
    except Exception as e:
        import traceback
        traceback.print_exc()
    await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())


