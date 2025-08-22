# 🎵 SpotiSnake

**SpotiSnake** is an innovative fusion of the classic Snake game and Spotify album listening. Eat apples, and reveal the full artwork, and enjoy real-time music as you play!

## 🎮 Game Overview

SpotiSnake transforms your favorite albums into an interactive gaming experience:

- **🎯 Choose Your Album**: Search and select any Spotify album with cool artwork
- **🐍 Play as Snake**: Navigate and eat scattered pieces of fruit
- **🖼️ Reveal Artwork**: Each apple you eat reveals a piece of the album cover of the album you chose 
- **🎵 Dynamic Music**: New tracks play every 5 apples eaten, with progressive speed
- **🥚 Hidden Easter Egg**: Discover a secret track for a special surprise!

---

## 🎯 How to Play

1. **Login**: Click "Login with Spotify" and authorize the app
2. **Search**: Type an album name and select from results
3. **Play**: Use arrow keys to move the snake
4. **Eat**: Collect album pieces to reveal the artwork
5. **Listen**: Enjoy music that changes every 5 pieces
6. **Win**: Complete the album or achieve high scores!

---

## 🏗️ Architecture

### Core Components
- **`main.py`**: Application entry point and initialization
- **`ui.py`**: User interface, menus, and navigation
- **`snake_logic.py`**: Game mechanics, collision detection, and scoring
- **`spotipy_handling.py`**: Spotify API integration and music control
- **`backend.py`**: Flask server for API proxying and authentication
- **`shared_constants.py`**: Global constants, colors, and configuration

### Tech Stack
| Component | Technology | Purpose |
|-----------|------------|---------|
| **Game Engine** | Pygame | Graphics, input handling, game loop |
| **Music API** | Spotipy | Spotify integration and playback control |
| **Authentication** | OAuth2 | Secure Spotify login |
| **Web Support** | Pygbag/Pyodide | Browser compatibility |
| **Backend** | Flask | API proxying and session management |
| **Async Operations** | asyncio | Non-blocking music control |

---

## 🎨 Features

### Core Gameplay
- **Progressive Difficulty**: Snake speed increases with score
- **Dynamic Music**: Seamless track transitions every 5 pieces
- **Visual Feedback**: Real-time album artwork revelation
- **Score Tracking**: Persistent scoring system

### Music Integration
- **Real-time Playback**: Direct Spotify control
- **Album Search**: Full Spotify catalog access
- **Track Randomization**: Varied listening experience
- **Volume Control**: Automatic music management

### User Experience
- **Responsive UI**: Clean, intuitive interface
- **Error Handling**: Graceful failure recovery
- **Cross-platform**: Works on desktop and web
- **Session Management**: Persistent login state

---

## 🐛 Troubleshooting

### Common Issues

**Music not playing:**
- Ensure Spotify app is running
- Check Premium subscription status, may or may not be an issue upon deployment
- Try to get 5 pieces, sometimes the API takes a second to handle your request 
---

## 🎁 Easter Egg

A very specific track triggers a **hidden message** in-game and automatically wins you a game. No hints — discover it yourself! 🥚

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Want to contact me for any reason, could even just be a game suggestion, could be to tell me how your day is going I'm open 

- **Email**: danielesk6@gmail.com
- **Username for almost any app**: danielllesk

---

## 🚀 Roadmap

### Upcoming Features
- [ ] Multiplayer battle mode
- [ ] Album progress saving
- [ ] Leaderboards and achievements
- [ ] Lyrics integration
- [ ] Mobile app version
- [ ] Social features and sharing

### Current Status
- ✅ Core gameplay complete
- ✅ Spotify integration working
- ✅ Web deployment ready
- 🔄 Performance optimization
- 🔄 Additional game modes

---

**Made with ❤️ for music lovers and gamers everywhere**

