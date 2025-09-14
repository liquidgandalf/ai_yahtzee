"""
AI Yahtzee Server
Flask + SocketIO backend for multiplayer Yahtzee game
"""

import os
import json
import random
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

# Directories
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')
data_dir = os.path.join(base_dir, 'data')
os.makedirs(data_dir, exist_ok=True)
game_state_file = os.path.join(data_dir, 'game_state.json')

# Flask Setup
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SECRET_KEY'] = 'ai_yahtzee_secret_key_change_in_production'
socketio = SocketIO(app)

# Game state
players = {}
ip_to_sid = {}
player_names = {}
game_state = {
    'phase': 'waiting',  # waiting, playing, finished
    'current_player': None,
    'dice': [1, 1, 1, 1, 1],
    'dice_kept': [False, False, False, False, False],
    'roll_count': 0,
    'max_rolls': 3,
    'scores': {},  # player_sid -> category -> score
    'turn_order': [],
    'winner': None
}

# Color pool for players
COLOR_POOL = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (255, 165, 0), (128, 0, 128),
    (0, 128, 128), (128, 128, 0), (255, 105, 180), (0, 100, 255),
    (0, 200, 50), (255, 20, 147), (139, 69, 19), (100, 149, 237)
]
used_colors = set()

def save_game_state():
    """Save current game state to file"""
    state_to_save = {
        'players': players,
        'ip_to_sid': ip_to_sid,
        'player_names': player_names,
        'game_state': game_state,
        'used_colors': list(used_colors)  # Convert set to list for JSON
    }
    with open(game_state_file, 'w') as f:
        json.dump(state_to_save, f, indent=2)

def should_reset_game_state(saved_state):
    """Check if we should reset the game state instead of loading it"""
    game_state_data = saved_state.get('game_state', {})

    # Reset if game is finished
    if game_state_data.get('phase') == 'finished':
        return True

    # Reset if no players
    players_data = saved_state.get('players', {})
    if not players_data:
        return True

    # Reset if all players have no scores (empty or zero scores)
    scores_data = game_state_data.get('scores', {})
    if not scores_data:
        return True

    # Check if any player has actual scores
    has_scores = False
    for player_scores in scores_data.values():
        if player_scores:  # Has any scores at all
            has_scores = True
            break

    # Reset if no actual scores (only empty scoreboards)
    if not has_scores:
        return True

    return False

def load_game_state():
    """Load game state from file"""
    global players, ip_to_sid, player_names, game_state, used_colors
    if os.path.exists(game_state_file):
        try:
            with open(game_state_file, 'r') as f:
                saved_state = json.load(f)

            # Check if we should reset instead of loading
            if should_reset_game_state(saved_state):
                print("Old game state found - resetting for fresh start")
                # Keep player names for convenience, but reset everything else
                player_names_temp = saved_state.get('player_names', {})
                reset_game_state()
                player_names.update(player_names_temp)  # Restore saved names
                save_game_state()  # Save the reset state
                return

            # Load the saved state
            players = saved_state.get('players', {})
            ip_to_sid = saved_state.get('ip_to_sid', {})
            player_names = saved_state.get('player_names', {})
            game_state = saved_state.get('game_state', game_state)
            used_colors = set(tuple(color) if isinstance(color, list) else color for color in saved_state.get('used_colors', []))
            print("Game state loaded successfully")

        except Exception as e:
            print(f"Error loading game state: {e}")
            reset_game_state()

def reset_game_state():
    """Reset all game state to initial values"""
    global players, ip_to_sid, game_state, used_colors
    players = {}
    ip_to_sid = {}
    game_state = {
        'phase': 'waiting',  # waiting, playing, finished
        'current_player': None,
        'dice': [1, 1, 1, 1, 1],
        'dice_kept': [False, False, False, False, False],
        'roll_count': 0,
        'max_rolls': 3,
        'scores': {},  # player_sid -> category -> score
        'turn_order': [],
        'winner': None
    }
    used_colors = set()
    print("Game state reset to initial values")

@app.route('/')
def index():
    """Main game display page"""
    return render_template('index.html')

@app.route('/controller')
def controller():
    """Mobile controller page"""
    client_ip = request.remote_addr
    default_name = player_names.get(client_ip, "")
    return render_template('controller.html', default_name=default_name)

@socketio.on('connect')
def handle_connect():
    """Handle new socket connections"""
    print("Client connected")

@socketio.on('get_game_state')
def handle_get_game_state():
    """Send current game state to client"""
    client_ip = request.remote_addr
    is_known_ip = client_ip in player_names

    print(f"Client {client_ip} requested game state")
    print(f"Is known IP: {is_known_ip}")
    print(f"Game phase: {game_state['phase']}")
    print(f"Players: {list(players.keys())}")

    # Determine what screen to show based on IP and game state
    if not is_known_ip and game_state['phase'] == 'playing':
        # Unknown IP + Game in progress = Cannot join
        print("Sending cannot_join response")
        emit('game_state', {
            'phase': 'cannot_join',
            'reason': 'Game already in progress'
        })
    else:
        # Send current game state
        response_data = {
            'phase': game_state['phase'],
            'players': list(players.values()),
            'current_player': game_state.get('current_player'),
            'dice': game_state['dice'],
            'dice_kept': game_state['dice_kept'],
            'roll_count': game_state['roll_count'],
            'max_rolls': game_state['max_rolls'],
            'scores': game_state['scores'],
            'is_known_ip': is_known_ip,
            'saved_name': player_names.get(client_ip, '')
        }
        print(f"Sending game state: {response_data}")
        emit('game_state', response_data)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnections"""
    sid = request.sid
    if sid in players:
        player = players[sid]
        print(f"Client disconnected - Player {player['name']} (sid: {sid})")

        # Clean up player data
        del players[sid]

        # Clean up IP mapping and color
        for ip, mapped_sid in list(ip_to_sid.items()):
            if mapped_sid == sid:
                del ip_to_sid[ip]
                # Convert color tuple to tuple for set removal
                color_tuple = tuple(player['color']) if isinstance(player['color'], list) else player['color']
                used_colors.discard(color_tuple)

        save_game_state()

@socketio.on('join')
def handle_join(data):
    """Handle a player joining the game"""
    name = data.get('name', '').strip()
    client_ip = request.remote_addr
    new_sid = request.sid

    if not name:
        emit('join_error', {'error': 'Name is required'})
        return

    # Update name memory
    player_names[client_ip] = name

    # Reclaim old session
    old_sid = ip_to_sid.get(client_ip)
    if old_sid:
        old_player = players.pop(old_sid, None)
    else:
        old_player = None

    # Color: reuse or assign new
    if old_player:
        color = old_player['color']
    else:
        available_colors = [c for c in COLOR_POOL if c not in used_colors]
        color = random.choice(available_colors) if available_colors else (
            random.randint(50, 255), random.randint(50, 255), random.randint(50, 255)
        )
        used_colors.add(tuple(color))  # Ensure color is stored as tuple in set

    # Register new player session
    players[new_sid] = {
        'color': color,
        'name': name,
        'ready': False,
        'last_active': time.time(),
        'ip': client_ip
    }

    ip_to_sid[client_ip] = new_sid

    print(f"Player {name} (IP: {client_ip}) joined or rejoined (SID: {new_sid})")
    print(f"Total players now: {len(players)}")
    print(f"Players dict: {list(players.keys())}")
    print(f"Player details: {players[new_sid]}")

    emit('joined', {'color': color, 'game_state': game_state})

    save_game_state()

    # Force a display update by printing to console
    print(f"🎮 SERVER: Player {name} joined - display should update now")

@socketio.on('ready')
def handle_ready():
    """Handle player ready status"""
    sid = request.sid
    if sid in players:
        players[sid]['ready'] = True
        players[sid]['last_active'] = time.time()

        # Check if we can start the game (allow single player for now)
        ready_players = [p for p in players.values() if p['ready']]
        if len(ready_players) >= 1 and len(ready_players) == len(players):
            start_game()

        save_game_state()

def start_game():
    """Start the game when all players are ready"""
    global game_state
    game_state['phase'] = 'playing'
    game_state['turn_order'] = list(players.keys())
    game_state['current_player'] = game_state['turn_order'][0] if game_state['turn_order'] else None

    # Initialize scoreboards
    game_state['scores'] = {sid: {} for sid in players.keys()}

    socketio.emit('game_started', game_state)
    save_game_state()

def run_server():
    """Start the Flask server"""
    load_game_state()  # Load saved state on startup
    socketio.run(app, host='0.0.0.0', port=5050, allow_unsafe_werkzeug=True)