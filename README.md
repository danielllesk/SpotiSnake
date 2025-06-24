# 🎵 SpotiSnake

**SpotiSnake** is a new way to enjoy your album listening experience.
it's a twist on the classic Snake game, and slight inspiration from the "eat your playlist" feature on spotify ;)
Eat album cover "fruit" tiles, piece together a full album, and listen to real-time music as you play.
---

## 🐍 How It Works

- Choose a **Spotify album** at the start of the game, preferrable something with cool album art.
- Play as a snake that eats randomly scattered pieces of the album cover.
- As you eat, each tile gets "locked in" onto the background, slowly revealing the full album.
- After 5 blocks, a new random track from the album plays in the background. When it changes, the game updates accordingly.
- If a secret **easter egg track** plays, you’ll get a special message. Message me if you get it👀
- Want to challenge friends? **Send me the albums you ate!**

---

## ⚙️ Tech Stack

| Component            | Tech Used                                     |
|---------------------|-----------------------------------------------|
| Game Engine          | [`pygame`](https://www.pygame.org/)          |
| Spotify API          | [`spotipy`](https://spotipy.readthedocs.io/) |
| OAuth2 Auth Flow     | `SpotifyOAuth` for secure access              |
| Async Handling       | `asyncio` + `aiohttp` for smoother music control (non-blocking) |
| Multi-threading (initially) | Used `concurrent.futures.ThreadPoolExecutor`, now adapted for browser compatibility |
| Web Portability      | Designed for conversion with WebAssembly & Pyodide |

---

## 📦 Project Structure (Sample)

```
SpotiSnake/
├── main.py               # Main game loop
├── ui.py                 # Start menu, buttons, and event handling
├── snake_logic.py        # Snake movement, collision, and gameplay
├── spotify_handler.py    # Album fetching, authentication, and playback
└── README.md
```

---

## 🎁 Easter Egg

A very specific track, when played, will trigger a **special hidden message** in-game.

No hints — discover it for yourself.

---

## 📬 Share Your Wins!

Finished an album? Snaked your way through some obscure indie record?  
**Send me the albums you ate** — I'd love to see what you've built (or uncovered)!

---

## Current Stage
- Web deployment, and code cleanup as of right now (currently available to download for mac users at https://danielllesk.itch.io/spotisnake but am working on a browser playable version)

## 🧠 Future Ideas
- Multiplayer snake battle mode (battle of the albums)
- Album progress saving and leaderboard
- Integration with lyrics or track popularity stats
- Visual filters for dark album covers
- Standalone app/website where users create accounts, connect with friends, see what albums they are eating

