/**
 * AI Yahtzee Mobile Controller
 * Handles all client-side logic for the mobile game controller
 */

class YahtzeeController {
    constructor() {
        this.socket = null;
        this.currentScreen = 'loading';
        this.playerName = '';
        this.playerId = null;
        this.gameState = null;
        this.isMyTurn = false;

        this.init();
    }

    init() {
        this.setupSocket();
        this.setupEventListeners();
        this.showScreen('loading');
    }

    setupSocket() {
        this.socket = io();

        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.requestGameState();
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.showError('Lost connection to server');
        });

        // Game state events
        this.socket.on('game_state', (data) => {
            this.handleGameState(data);
        });

        this.socket.on('joined', (data) => {
            this.handleJoined(data);
        });

        this.socket.on('join_error', (data) => {
            this.showError(data.error);
        });

        this.socket.on('game_started', (data) => {
            this.handleGameStarted(data);
        });

        this.socket.on('dice_rolled', (data) => {
            this.handleDiceRolled(data);
        });

        this.socket.on('turn_changed', (data) => {
            this.handleTurnChanged(data);
        });

        this.socket.on('game_over', (data) => {
            this.handleGameOver(data);
        });
    }

    setupEventListeners() {
        // Join screen
        document.getElementById('join-btn').addEventListener('click', () => {
            this.handleJoin();
        });

        document.getElementById('player-name').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleJoin();
            }
        });

        // Ready screen
        document.getElementById('ready-btn').addEventListener('click', () => {
            this.handleReady();
        });

        // Game controls
        document.getElementById('roll-btn').addEventListener('click', () => {
            this.handleRollDice();
        });

        document.getElementById('reroll-btn').addEventListener('click', () => {
            this.handleRerollDice();
        });

        // Dice keep buttons
        document.querySelectorAll('.keep-btn').forEach((btn, index) => {
            btn.addEventListener('click', () => {
                this.toggleDieKeep(index);
            });
        });

        // Category buttons
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.handleCategorySelect(btn.dataset.category);
            });
        });

        // Other buttons
        document.getElementById('retry-btn').addEventListener('click', () => {
            location.reload();
        });

        document.getElementById('play-again-btn').addEventListener('click', () => {
            this.handlePlayAgain();
        });
    }

    requestGameState() {
        // Request current game state from server
        this.socket.emit('get_game_state');
    }

    handleGameState(data) {
        this.gameState = data;

        // Determine which screen to show based on IP recognition and game state
        const isKnownIP = this.checkIfKnownIP();
        const gameInProgress = data.phase === 'playing';

        if (!isKnownIP && gameInProgress) {
            // Unknown IP + Game in progress = Cannot join
            this.showScreen('cannot-join');
        } else if (isKnownIP) {
            // Known IP = Auto-rejoin
            this.handleKnownPlayerRejoin();
        } else if (!isKnownIP && !gameInProgress) {
            // Unknown IP + No game = Show join form
            this.showScreen('join');
        }
    }

    checkIfKnownIP() {
        // Check if this IP has a saved player name
        // This would be determined by the server based on IP address
        return document.getElementById('player-name').value !== '';
    }

    handleKnownPlayerRejoin() {
        // For known players, try to rejoin automatically
        const savedName = document.getElementById('player-name').value;
        if (savedName) {
            this.socket.emit('join', { name: savedName });
        } else {
            this.showScreen('join');
        }
    }

    handleJoined(data) {
        this.playerId = this.socket.id;
        this.playerName = data.name;

        // Update greeting
        document.getElementById('player-greeting').textContent = `Welcome, ${this.playerName}!`;

        // Show waiting screen
        this.showScreen('waiting');
        this.updatePlayersList();
    }

    handleGameStarted(data) {
        this.gameState = data;
        this.showScreen('game');
        this.updateGameDisplay();
    }

    handleJoin() {
        const nameInput = document.getElementById('player-name');
        const name = nameInput.value.trim();

        if (!name) {
            this.showError('Please enter your name');
            return;
        }

        this.socket.emit('join', { name: name });
    }

    handleReady() {
        this.socket.emit('ready');
        document.getElementById('ready-btn').textContent = 'Ready!';
        document.getElementById('ready-btn').disabled = true;
    }

    handleRollDice() {
        this.socket.emit('roll_dice');
    }

    handleRerollDice() {
        const keptDice = [];
        document.querySelectorAll('.die').forEach((die, index) => {
            if (die.classList.contains('kept')) {
                keptDice.push(index);
            }
        });
        this.socket.emit('reroll_dice', { kept: keptDice });
    }

    toggleDieKeep(index) {
        const die = document.querySelector(`.die[data-index="${index}"]`);
        die.classList.toggle('kept');
    }

    handleCategorySelect(category) {
        this.socket.emit('score_category', { category: category });
    }

    handleDiceRolled(data) {
        this.updateDiceDisplay(data.dice, data.kept);
        this.updateRollCount(data.roll_count, data.max_rolls);
    }

    handleTurnChanged(data) {
        this.isMyTurn = data.current_player === this.playerId;
        this.updateTurnIndicator(data.current_player_name);
        this.updateGameControls();
    }

    handleGameOver(data) {
        this.showGameOverScreen(data);
    }

    handlePlayAgain() {
        // Reset for new game
        this.showScreen('waiting');
    }

    updatePlayersList() {
        const container = document.getElementById('players-container');
        container.innerHTML = '';

        // This would be populated from server data
        // For now, just show current player
        const playerDiv = document.createElement('div');
        playerDiv.className = 'player-item';
        playerDiv.textContent = `${this.playerName} (You)`;
        container.appendChild(playerDiv);
    }

    updateDiceDisplay(dice, kept) {
        dice.forEach((value, index) => {
            const die = document.querySelector(`.die[data-index="${index}"]`);
            const valueSpan = die.querySelector('.die-value');
            valueSpan.textContent = value;

            if (kept[index]) {
                die.classList.add('kept');
            } else {
                die.classList.remove('kept');
            }
        });
    }

    updateRollCount(current, max) {
        document.getElementById('roll-count').textContent = `${current}/${max}`;

        if (current >= max) {
            document.getElementById('roll-btn').classList.add('hidden');
            document.getElementById('reroll-btn').classList.add('hidden');
            // Show scoring area
            document.querySelector('.scoring-area').classList.remove('hidden');
        } else {
            document.getElementById('roll-btn').classList.add('hidden');
            document.getElementById('reroll-btn').classList.remove('hidden');
        }
    }

    updateTurnIndicator(currentPlayerName) {
        document.getElementById('current-player').textContent = currentPlayerName;
    }

    updateGameControls() {
        const rollBtn = document.getElementById('roll-btn');
        const rerollBtn = document.getElementById('reroll-btn');

        if (this.isMyTurn) {
            rollBtn.disabled = false;
            rerollBtn.disabled = false;
        } else {
            rollBtn.disabled = true;
            rerollBtn.disabled = true;
        }
    }

    updateGameDisplay() {
        // Update all game display elements
        this.updateDiceDisplay(this.gameState.dice, this.gameState.dice_kept);
        this.updateRollCount(this.gameState.roll_count, this.gameState.max_rolls);
        this.updateTurnIndicator(this.gameState.current_player_name);
        this.updateGameControls();
    }

    showGameOverScreen(data) {
        const overlay = document.getElementById('game-over-screen');
        const scoresDiv = document.getElementById('final-scores');
        const winnerDiv = document.getElementById('winner-text');

        // Populate final scores
        scoresDiv.innerHTML = '<h3>Final Scores:</h3>';
        data.scores.forEach(player => {
            const scoreDiv = document.createElement('div');
            scoreDiv.textContent = `${player.name}: ${player.total_score}`;
            scoresDiv.appendChild(scoreDiv);
        });

        winnerDiv.textContent = `🏆 Winner: ${data.winner}!`;

        overlay.classList.remove('hidden');
    }

    showScreen(screenId) {
        // Hide all screens
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.add('hidden');
        });

        // Show target screen
        document.getElementById(`${screenId}-screen`).classList.remove('hidden');
        this.currentScreen = screenId;
    }

    showError(message) {
        const errorDiv = document.getElementById('error-message');
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');

        setTimeout(() => {
            errorDiv.classList.add('hidden');
        }, 5000);
    }
}

// Initialize controller when page loads
document.addEventListener('DOMContentLoaded', () => {
    new YahtzeeController();
});