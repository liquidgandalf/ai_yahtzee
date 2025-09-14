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

        this.socket.on('dice_kept', (data) => {
            this.handleDiceKept(data);
        });

        this.socket.on('score_submitted', (data) => {
            this.handleScoreSubmitted(data);
        });

        this.socket.on('error', (data) => {
            this.showError(data.message);
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
        console.log('=== RECEIVED GAME STATE ===');
        console.log('Full data:', JSON.stringify(data, null, 2));
        console.log('Current screen:', this.currentScreen);
        console.log('Phase:', data.phase);
        console.log('Is known IP:', data.is_known_ip);
        console.log('Saved name:', data.saved_name);
        console.log('Players count:', data.players ? data.players.length : 0);

        this.gameState = data;

        // Handle different scenarios based on server response
        if (data.phase === 'cannot_join') {
            // Server says cannot join
            console.log('🎯 Cannot join - showing cannot-join screen');
            this.showScreen('cannot-join');
        } else if (data.is_known_ip) {
            // Known IP - auto-rejoin or show ready screen
            console.log('🎯 Known IP - handling rejoin');
            this.handleKnownPlayerRejoin(data);
        } else {
            // Unknown IP - show join form
            console.log('🎯 Unknown IP - showing join screen');
            this.showScreen('join');
        }
    }

    checkIfKnownIP() {
        // Check if this IP has a saved player name
        // This would be determined by the server based on IP address
        return document.getElementById('player-name').value !== '';
    }

    handleKnownPlayerRejoin(data) {
        console.log('=== HANDLING KNOWN PLAYER REJOIN ===');
        console.log('Data:', JSON.stringify(data, null, 2));
        console.log('Players array:', data.players);
        console.log('Saved name:', data.saved_name);

        // Check if we're already in the game
        const myPlayer = data.players ? data.players.find(p => p.name === data.saved_name) : null;
        console.log('My player found:', myPlayer);

        if (myPlayer) {
            // We're already in the game
            console.log('🎯 Player already in game:', myPlayer);
            this.playerName = myPlayer.name;
            this.playerId = myPlayer.sid || this.socket.id;

            if (data.phase === 'waiting') {
                console.log('🎯 Showing waiting screen');
                this.showScreen('waiting');
                this.updatePlayersList();
            } else if (data.phase === 'playing') {
                console.log('🎯 Showing game screen');
                this.showScreen('game');
                this.updateGameDisplay();
            }
        } else if (data.saved_name) {
            // We have a saved name but not in current game - pre-fill and show join
            console.log('🎯 Found saved name, pre-filling join form:', data.saved_name);
            document.getElementById('player-name').value = data.saved_name;
            console.log('🎯 Showing join screen with pre-filled name');
            this.showScreen('join');
            // Don't auto-join, let user click the button
        } else {
            // No saved name - show join form
            console.log('🎯 No saved name found, showing join screen');
            this.showScreen('join');
        }
    }

    getClientIP() {
        // This is a simple way - in production you'd get this from server
        return window.location.hostname;
    }

    handleJoined(data) {
        console.log('Join successful:', data);
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

        console.log('Join button clicked, name:', name);

        if (!name) {
            this.showError('Please enter your name');
            return;
        }

        console.log('Emitting join event with name:', name);
        this.socket.emit('join', { name: name });
    }

    handleReady() {
        this.socket.emit('ready');
        document.getElementById('ready-btn').textContent = 'Ready!';
        document.getElementById('ready-btn').disabled = true;
    }

    handleRollDice() {
        const keptDice = [];
        document.querySelectorAll('.die').forEach((die, index) => {
            if (die.classList.contains('kept')) {
                keptDice.push(index);
            }
        });
        this.socket.emit('roll_dice', { keep_indices: keptDice });
    }

    toggleDieKeep(index) {
        const die = document.querySelector(`.die[data-index="${index}"]`);
        die.classList.toggle('kept');
    }

    handleCategorySelect(category) {
        this.socket.emit('score_category', { category: category });
    }

    handleDiceRolled(data) {
        this.updateDiceDisplay(data.dice, data.dice_kept);
        this.updateRollCount(data.roll_count, data.max_rolls);

        // Check if it's the current player's turn
        this.isMyTurn = data.player === this.socket.id;
        this.updateTurnIndicator(data.player);
        this.updateGameControls();
    }

    handleDiceKept(data) {
        this.updateDiceDisplay(this.gameState.dice, data.dice_kept);
    }

    handleScoreSubmitted(data) {
        // Update game state with new score
        if (!this.gameState.scores) {
            this.gameState.scores = {};
        }
        if (!this.gameState.scores[data.player]) {
            this.gameState.scores[data.player] = {};
        }
        this.gameState.scores[data.player][data.category] = data.score;

        // Check if game is finished
        if (data.game_finished) {
            this.handleGameOver({
                winner: data.winner,
                scores: this.gameState.scores
            });
        } else {
            // Move to next turn
            this.isMyTurn = false;
            this.updateTurnIndicator('Next Player');
            this.updateGameControls();
        }
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

        if (this.gameState && this.gameState.players) {
            this.gameState.players.forEach(player => {
                const playerDiv = document.createElement('div');
                playerDiv.className = 'player-item';

                const isCurrentPlayer = player.name === this.playerName;
                const readyStatus = player.ready ? ' (Ready)' : ' (Waiting)';

                playerDiv.textContent = `${player.name}${isCurrentPlayer ? ' (You)' : ''}${readyStatus}`;
                container.appendChild(playerDiv);
            });
        }
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

    updateTurnIndicator(currentPlayerId) {
        let displayName = 'Waiting...';
        if (currentPlayerId === this.socket.id) {
            displayName = 'Your Turn!';
        } else if (this.gameState && this.gameState.players) {
            const player = this.gameState.players.find(p => p.sid === currentPlayerId);
            if (player) {
                displayName = `${player.name}'s Turn`;
            }
        }
        document.getElementById('current-player').textContent = displayName;
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
        if (this.gameState) {
            this.updateDiceDisplay(this.gameState.dice, this.gameState.dice_kept);
            this.updateRollCount(this.gameState.roll_count, this.gameState.max_rolls);
            this.updateTurnIndicator(this.gameState.current_player);
            this.updateGameControls();
        }
    }

    showGameOverScreen(data) {
        const overlay = document.getElementById('game-over-screen');
        const scoresDiv = document.getElementById('final-scores');
        const winnerDiv = document.getElementById('winner-text');

        // Find winner's name
        let winnerName = 'Unknown';
        if (this.gameState && this.gameState.players) {
            const winnerPlayer = this.gameState.players.find(p => p.sid === data.winner);
            if (winnerPlayer) {
                winnerName = winnerPlayer.name;
            }
        }

        // Populate final scores
        scoresDiv.innerHTML = '<h3>Final Scores:</h3>';

        // Calculate and display scores for each player
        if (this.gameState && this.gameState.players) {
            this.gameState.players.forEach(player => {
                const playerScores = data.scores[player.sid] || {};
                let totalScore = 0;

                // Calculate upper section
                const upperCategories = ['ones', 'twos', 'threes', 'fours', 'fives', 'sixes'];
                let upperTotal = 0;
                upperCategories.forEach(cat => {
                    upperTotal += playerScores[cat] || 0;
                });

                // Add upper bonus if >= 63
                if (upperTotal >= 63) {
                    upperTotal += 35;
                }

                // Add lower section
                const lowerCategories = ['three_of_a_kind', 'four_of_a_kind', 'full_house', 'small_straight', 'large_straight', 'yahtzee', 'chance'];
                let lowerTotal = 0;
                lowerCategories.forEach(cat => {
                    lowerTotal += playerScores[cat] || 0;
                });

                totalScore = upperTotal + lowerTotal;

                const scoreDiv = document.createElement('div');
                scoreDiv.textContent = `${player.name}: ${totalScore}`;
                scoresDiv.appendChild(scoreDiv);
            });
        }

        winnerDiv.textContent = `🏆 Winner: ${winnerName}!`;

        overlay.classList.remove('hidden');
    }

    showScreen(screenId) {
        console.log('🎯 Switching to screen:', screenId);

        // Hide all screens
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.add('hidden');
        });

        // Show target screen
        const targetScreen = document.getElementById(`${screenId}-screen`);
        if (targetScreen) {
            targetScreen.classList.remove('hidden');
            console.log('✅ Screen switched to:', screenId);
        } else {
            console.error('❌ Screen not found:', `${screenId}-screen`);
        }

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