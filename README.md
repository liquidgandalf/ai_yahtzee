# AI Yahtzee

A multiplayer Yahtzee game built with Flask, SocketIO, and Pygame. Players join via QR code on mobile devices, with the main screen displaying the game state and mobile phones providing controls.

## Features

- **Multiplayer**: Real-time multiplayer gameplay
- **Mobile Controls**: Players join via QR code on their phones
- **Persistent Game State**: Game resumes after server restart
- **Turn-based Gameplay**: Proper Yahtzee rules with 3 rolls per turn
- **Score Validation**: Automatic scoring and validation
- **Rejoin Support**: Players can rejoin if disconnected

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the game:**
   ```bash
   python main.py
   ```

3. **Join the game:**
   - Open a browser and navigate to `http://localhost:5050`
   - Scan the QR code with your mobile device
   - Join with a name and click "Ready"

## Project Structure

```
ai_yahtzee/
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── app/
│   ├── server.py          # Flask + SocketIO backend
│   └── game.py            # Pygame display logic
├── templates/
│   ├── index.html         # Main game display
│   └── controller.html    # Mobile controller
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── controls.js
├── data/
│   └── game_state.json    # Saved game state
└── .gitignore
```

## Yahtzee Rules

### Objective
Score the highest total by filling all 13 scoring categories.

### Turn Structure
1. Roll all 5 dice
2. Keep some dice and reroll the rest (up to 2 additional rolls)
3. Score in one unfilled category

### Categories
- **Upper Section**: Ones through Sixes (bonus if ≥63)
- **Lower Section**: 3-of-a-Kind, 4-of-a-Kind, Full House, Small/Large Straight, Yahtzee, Chance

## Development

- Uses Flask for web server
- SocketIO for real-time communication
- Pygame for server-side display
- QR codes for easy mobile joining

## License

This project is open source. See projectplan.md for detailed implementation notes.