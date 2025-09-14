"""
AI Yahtzee Server
Flask + SocketIO backend for multiplayer Yahtzee game
"""

import os
import json
import random
import time
import threading
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

# Thread synchronization
data_lock = threading.Lock()

# Shared data structure for thread-safe communication
class SharedGameData:
    def __init__(self):
        self.players = {}
        self.ip_to_sid = {}
        self.player_names = {}
        self.game_state = {
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
        self.used_colors = set()

shared_data = SharedGameData()

# For backward compatibility, create references
players = shared_data.players
ip_to_sid = shared_data.ip_to_sid
player_names = shared_data.player_names
game_state = shared_data.game_state
used_colors = shared_data.used_colors

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
        'players': shared_data.players,
        'ip_to_sid': shared_data.ip_to_sid,
        'player_names': shared_data.player_names,
        'game_state': shared_data.game_state,
        'used_colors': list(shared_data.used_colors)  # Convert set to list for JSON
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
                shared_data.player_names.update(player_names_temp)  # Restore saved names
                save_game_state()  # Save the reset state
                return

            # Load the saved state
            shared_data.players = saved_state.get('players', {})
            shared_data.ip_to_sid = saved_state.get('ip_to_sid', {})
            shared_data.player_names = saved_state.get('player_names', {})
            shared_data.game_state = saved_state.get('game_state', shared_data.game_state)
            shared_data.used_colors = set(tuple(color) if isinstance(color, list) else color for color in saved_state.get('used_colors', []))
            print("Game state loaded successfully")

        except Exception as e:
            print(f"Error loading game state: {e}")
            reset_game_state()

def reset_game_state():
    """Reset all game state to initial values"""
    shared_data.players = {}
    shared_data.ip_to_sid = {}
    shared_data.game_state = {
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
    shared_data.used_colors = set()
    print("Game state reset to initial values")

@app.route('/')
def index():
    """Main game display page"""
    return render_template('index.html')

@app.route('/controller')
def controller():
    """Mobile controller page"""
    client_ip = request.remote_addr
    default_name = shared_data.player_names.get(client_ip, "")
    return render_template('controller.html', default_name=default_name)

@socketio.on('connect')
def handle_connect():
    """Handle new socket connections"""
    print("Client connected")

@socketio.on('get_game_state')
def handle_get_game_state():
    """Send current game state to client"""
    client_ip = request.remote_addr
    is_known_ip = client_ip in shared_data.player_names

    print(f"Client {client_ip} requested game state")
    print(f"Is known IP: {is_known_ip}")
    print(f"Game phase: {shared_data.game_state['phase']}")
    print(f"Players: {list(shared_data.players.keys())}")

    # Determine what screen to show based on IP and game state
    if not is_known_ip and shared_data.game_state['phase'] == 'playing':
        # Unknown IP + Game in progress = Cannot join
        print("Sending cannot_join response")
        emit('game_state', {
            'phase': 'cannot_join',
            'reason': 'Game already in progress'
        })
    else:
        # Send current game state
        response_data = {
            'phase': shared_data.game_state['phase'],
            'players': list(shared_data.players.values()),
            'current_player': shared_data.game_state.get('current_player'),
            'dice': shared_data.game_state['dice'],
            'dice_kept': shared_data.game_state['dice_kept'],
            'roll_count': shared_data.game_state['roll_count'],
            'max_rolls': shared_data.game_state['max_rolls'],
            'scores': shared_data.game_state['scores'],
            'is_known_ip': is_known_ip,
            'saved_name': shared_data.player_names.get(client_ip, '')
        }
        print(f"Sending game state: {response_data}")
        emit('game_state', response_data)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnections"""
    sid = request.sid
    if sid in shared_data.players:
        player = shared_data.players[sid]
        print(f"Client disconnected - Player {player['name']} (sid: {sid})")

        # Clean up player data
        del shared_data.players[sid]

        # Clean up IP mapping and color
        for ip, mapped_sid in list(shared_data.ip_to_sid.items()):
            if mapped_sid == sid:
                del shared_data.ip_to_sid[ip]
                # Convert color tuple to tuple for set removal
                color_tuple = tuple(player['color']) if isinstance(player['color'], list) else player['color']
                shared_data.used_colors.discard(color_tuple)

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
    shared_data.player_names[client_ip] = name

    # Reclaim old session
    old_sid = shared_data.ip_to_sid.get(client_ip)
    if old_sid:
        old_player = shared_data.players.pop(old_sid, None)
    else:
        old_player = None

    # Color: reuse or assign new
    if old_player:
        color = old_player['color']
    else:
        available_colors = [c for c in COLOR_POOL if c not in shared_data.used_colors]
        color = random.choice(available_colors) if available_colors else (
            random.randint(50, 255), random.randint(50, 255), random.randint(50, 255)
        )
        shared_data.used_colors.add(tuple(color))  # Ensure color is stored as tuple in set

    # Register new player session
    shared_data.players[new_sid] = {
        'color': color,
        'name': name,
        'ready': False,
        'last_active': time.time(),
        'ip': client_ip
    }

    shared_data.ip_to_sid[client_ip] = new_sid

    print(f"Player {name} (IP: {client_ip}) joined or rejoined (SID: {new_sid})")
    print(f"Total players now: {len(shared_data.players)}")
    print(f"Players dict: {list(shared_data.players.keys())}")
    print(f"Player details: {shared_data.players[new_sid]}")

    emit('joined', {'color': color, 'game_state': shared_data.game_state})

    save_game_state()

    # Force a display update by printing to console
    print(f"🎮 SERVER: Player {name} joined - display should update now")

@socketio.on('ready')
def handle_ready():
    """Handle player ready status"""
    sid = request.sid
    if sid in shared_data.players:
        shared_data.players[sid]['ready'] = True
        shared_data.players[sid]['last_active'] = time.time()

        # Check if we can start the game (allow single player for now)
        ready_players = [p for p in shared_data.players.values() if p['ready']]
        if len(ready_players) >= 1 and len(ready_players) == len(shared_data.players):
            start_game()

        save_game_state()

def roll_dice(keep_indices=None):
    """Roll dice for the current player"""
    if keep_indices is None:
        keep_indices = []

    # Roll all dice or only non-kept dice
    new_dice = []
    for i in range(5):
        if i in keep_indices:
            # Keep the existing die
            new_dice.append(shared_data.game_state['dice'][i])
        else:
            # Roll a new die (1-6)
            new_dice.append(random.randint(1, 6))

    shared_data.game_state['dice'] = new_dice
    shared_data.game_state['roll_count'] += 1

    # Update kept status
    shared_data.game_state['dice_kept'] = [i in keep_indices for i in range(5)]

    return new_dice

def calculate_score(dice, category):
    """Calculate score for a Yahtzee category"""
    if not dice or len(dice) != 5:
        return 0

    dice_counts = {}
    for die in dice:
        dice_counts[die] = dice_counts.get(die, 0) + 1

    # Upper section (1-6)
    if category in ['ones', 'twos', 'threes', 'fours', 'fives', 'sixes']:
        number = int(category[0])  # Extract number from category name
        return dice_counts.get(number, 0) * number

    # Lower section
    elif category == 'three_of_a_kind':
        for count in dice_counts.values():
            if count >= 3:
                return sum(dice)
        return 0

    elif category == 'four_of_a_kind':
        for count in dice_counts.values():
            if count >= 4:
                return sum(dice)
        return 0

    elif category == 'full_house':
        has_three = False
        has_two = False
        for count in dice_counts.values():
            if count == 3:
                has_three = True
            elif count == 2:
                has_two = True
        return 25 if has_three and has_two else 0

    elif category == 'small_straight':
        sorted_dice = sorted(dice)
        # Check for 1,2,3,4 or 2,3,4,5 or 3,4,5,6
        straights = [
            [1,2,3,4], [2,3,4,5], [3,4,5,6]
        ]
        for straight in straights:
            if all(num in sorted_dice for num in straight):
                return 30
        return 0

    elif category == 'large_straight':
        sorted_dice = sorted(dice)
        # Check for 1,2,3,4,5 or 2,3,4,5,6
        if sorted_dice in [[1,2,3,4,5], [2,3,4,5,6]]:
            return 40
        return 0

    elif category == 'yahtzee':
        for count in dice_counts.values():
            if count == 5:
                return 50
        return 0

    elif category == 'chance':
        return sum(dice)

    return 0

def next_turn():
    """Move to the next player's turn"""
    if not shared_data.game_state['turn_order']:
        return

    current_idx = shared_data.game_state['turn_order'].index(shared_data.game_state['current_player'])
    next_idx = (current_idx + 1) % len(shared_data.game_state['turn_order'])
    shared_data.game_state['current_player'] = shared_data.game_state['turn_order'][next_idx]

    # Reset dice for new turn
    shared_data.game_state['dice'] = [1, 1, 1, 1, 1]
    shared_data.game_state['dice_kept'] = [False, False, False, False, False]
    shared_data.game_state['roll_count'] = 0

def start_game():
    """Start the game when all players are ready"""
    shared_data.game_state['phase'] = 'playing'
    shared_data.game_state['turn_order'] = list(shared_data.players.keys())
    shared_data.game_state['current_player'] = shared_data.game_state['turn_order'][0] if shared_data.game_state['turn_order'] else None

    # Initialize scoreboards
    shared_data.game_state['scores'] = {sid: {} for sid in shared_data.players.keys()}

    # Roll initial dice for first player
    if shared_data.game_state['current_player']:
        roll_dice()

    socketio.emit('game_started', shared_data.game_state)
    save_game_state()

@socketio.on('roll_dice')
def handle_roll_dice(data):
    """Handle dice roll request"""
    sid = request.sid

    # Only allow current player to roll
    if sid != shared_data.game_state['current_player']:
        emit('error', {'message': 'Not your turn'})
        return

    # Check if player has rolls left
    if shared_data.game_state['roll_count'] >= shared_data.game_state['max_rolls']:
        emit('error', {'message': 'No rolls left'})
        return

    # Get kept dice indices
    keep_indices = data.get('keep_indices', [])

    # Roll dice
    new_dice = roll_dice(keep_indices)

    # Save and broadcast
    save_game_state()
    socketio.emit('dice_rolled', {
        'dice': new_dice,
        'dice_kept': shared_data.game_state['dice_kept'],
        'roll_count': shared_data.game_state['roll_count'],
        'player': sid
    })

@socketio.on('keep_dice')
def handle_keep_dice(data):
    """Handle dice keeping selection"""
    sid = request.sid

    # Only allow current player to keep dice
    if sid != shared_data.game_state['current_player']:
        emit('error', {'message': 'Not your turn'})
        return

    keep_indices = data.get('keep_indices', [])
    shared_data.game_state['dice_kept'] = [i in keep_indices for i in range(5)]

    save_game_state()
    socketio.emit('dice_kept', {
        'dice_kept': shared_data.game_state['dice_kept'],
        'player': sid
    })

@socketio.on('score_category')
def handle_score_category(data):
    """Handle scoring in a category"""
    sid = request.sid
    category = data.get('category', '')

    # Only allow current player to score
    if sid != shared_data.game_state['current_player']:
        emit('error', {'message': 'Not your turn'})
        return

    # Check if category is already used
    if category in shared_data.game_state['scores'].get(sid, {}):
        emit('error', {'message': 'Category already used'})
        return

    # Calculate score
    dice = shared_data.game_state['dice']
    score = calculate_score(dice, category)

    # Save score
    if sid not in shared_data.game_state['scores']:
        shared_data.game_state['scores'][sid] = {}
    shared_data.game_state['scores'][sid][category] = score

    # Check if game is finished
    game_finished = check_game_finished()

    if game_finished:
        shared_data.game_state['phase'] = 'finished'
        winner = determine_winner()
        shared_data.game_state['winner'] = winner

    # Move to next turn (if game not finished)
    if not game_finished:
        next_turn()

    save_game_state()
    socketio.emit('score_submitted', {
        'player': sid,
        'category': category,
        'score': score,
        'game_finished': game_finished,
        'winner': winner if game_finished else None
    })

def check_game_finished():
    """Check if all players have filled all categories"""
    for player_scores in shared_data.game_state['scores'].values():
        if len(player_scores) < 13:  # 13 Yahtzee categories
            return False
    return True

def determine_winner():
    """Determine the winner based on total scores"""
    player_totals = {}

    for sid, scores in shared_data.game_state['scores'].items():
        total = 0
        # Calculate upper section
        upper_total = 0
        for category in ['ones', 'twos', 'threes', 'fours', 'fives', 'sixes']:
            upper_total += scores.get(category, 0)

        # Add upper bonus if >= 63
        if upper_total >= 63:
            upper_total += 35

        # Add lower section
        lower_total = 0
        for category in ['three_of_a_kind', 'four_of_a_kind', 'full_house', 'small_straight', 'large_straight', 'yahtzee', 'chance']:
            lower_total += scores.get(category, 0)

        total = upper_total + lower_total
        player_totals[sid] = total

    # Find winner (highest score)
    winner = max(player_totals, key=player_totals.get)
    return winner

def run_server():
    """Start the Flask server"""
    load_game_state()  # Load saved state on startup
    socketio.run(app, host='0.0.0.0', port=5050, allow_unsafe_werkzeug=True)