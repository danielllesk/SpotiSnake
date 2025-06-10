import PyInstaller.__main__
import os
import shutil

def build_game():
    """Builds the game into a standalone executable."""
    # Clean previous build
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    # Build with PyInstaller
    PyInstaller.__main__.run([
        'main.py',  # Your main script
        '--name=SpotiSnake',  # Name of the executable
        '--onefile',  # Create a single executable
        '--windowed',  # Don't show console window
        '--add-data=.cache:.',  # Include cache directory
        '--icon=assets/icon.ico',  # Add if you have an icon
        '--clean',  # Clean PyInstaller cache
        '--noconfirm',  # Replace existing build
    ])
    
    print("Build complete! Check the 'dist' folder for your executable.")

if __name__ == "__main__":
    build_game() 