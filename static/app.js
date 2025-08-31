// API base URL - adjust if needed
const API_BASE = window.location.origin;

// Current game session
let currentSession = null;
let currentRuleset = null;
let currentEvaluation = null; // Store current evaluation result

// DOM elements
let elements = {};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeElements();
    setupEventListeners();

    // If we're on the game page, load the session from URL
    if (window.location.pathname.includes('game.html')) {
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = urlParams.get('session');
        if (sessionId) {
            loadGameSession(sessionId);
        }
    } else {
        loadGamesList();
    }
});

function initializeElements() {
    // Index page elements
    elements.rulesetSelect = document.getElementById('ruleset-select');
    elements.createGameBtn = document.getElementById('create-game-btn');
    elements.loading = document.getElementById('loading');
    elements.gamesContainer = document.getElementById('games-container');

    // Game page elements
    elements.gameTitle = document.getElementById('game-title');
    elements.backBtn = document.getElementById('back-btn');
    elements.gameStatus = document.getElementById('game-status');
    elements.gameBoard = document.getElementById('game-board');

    // Chess controls
    elements.chessPieceSelect = document.getElementById('chess-piece-select');
    elements.chessMoveSelect = document.getElementById('chess-move-select');
    elements.submitChessMove = document.getElementById('submit-chess-move');

    // TBS controls
    elements.tbsActionType = document.getElementById('tbs-action-type');
    elements.tbsUnitSelect = document.getElementById('tbs-unit-select');
    elements.tbsMoveSelect = document.getElementById('tbs-move-select');
    elements.tbsTargetSelect = document.getElementById('tbs-target-select');
    elements.submitTbsAction = document.getElementById('submit-tbs-action');
    elements.moveFields = document.getElementById('move-fields');
    elements.attackFields = document.getElementById('attack-fields');
    elements.unitSelection = document.getElementById('unit-selection');

    // Evaluation
    elements.evaluationResult = document.getElementById('evaluation-result');
    elements.evalOutput = document.getElementById('eval-output');
}

function setupEventListeners() {
    if (elements.createGameBtn) {
        elements.createGameBtn.addEventListener('click', createNewGame);
    }

    if (elements.backBtn) {
        elements.backBtn.addEventListener('click', () => {
            window.location.href = 'index.html';
        });
    }

    if (elements.submitChessMove) {
        elements.submitChessMove.addEventListener('click', submitChessMove);
    }

    if (elements.submitTbsAction) {
        elements.submitTbsAction.addEventListener('click', submitTbsAction);
    }

    if (elements.tbsActionType) {
        elements.tbsActionType.addEventListener('change', toggleTbsActionFields);
    }

    // New event listeners for dropdowns
    if (elements.chessPieceSelect) {
        elements.chessPieceSelect.addEventListener('change', onChessPieceSelected);
    }

    if (elements.tbsUnitSelect) {
        elements.tbsUnitSelect.addEventListener('change', onTbsUnitSelected);
    }

    if (elements.tbsMoveSelect) {
        elements.tbsMoveSelect.addEventListener('change', onTbsMoveSelected);
    }

    if (elements.tbsTargetSelect) {
        elements.tbsTargetSelect.addEventListener('change', onTbsTargetSelected);
    }
}

async function createNewGame() {
    const ruleset = elements.rulesetSelect.value;
    elements.loading.style.display = 'block';
    elements.createGameBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ruleset: ruleset })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const session = await response.json();
        window.location.href = `game.html?session=${session.id}`;

    } catch (error) {
                showErrorMessage(`Failed to create game: ${error.message}`);
        console.error('Create game error:', error);
    } finally {
        elements.loading.style.display = 'none';
        elements.createGameBtn.disabled = false;
    }
}

async function loadGamesList() {
    try {
        const response = await fetch(`${API_BASE}/sessions`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const sessions = await response.json();
        displayGamesList(sessions);

    } catch (error) {
        console.error('Load games error:', error);
        elements.gamesContainer.innerHTML = '<p>Failed to load games. Make sure the API is running.</p>';
    }
}

function displayGamesList(sessions) {
    if (!sessions || sessions.length === 0) {
        elements.gamesContainer.innerHTML = '<p>No games found. Create a new game to get started!</p>';
        return;
    }

    const html = sessions.map(session => `
        <div class="game-card">
            <h3>${session.ruleset.toUpperCase()} Game</h3>
            <p>Status: ${session.state?.status || 'Active'}</p>
            <p>Created: ${new Date(session.created_at).toLocaleString()}</p>
            <button onclick="window.location.href='game.html?session=${session.id}'">Continue Game</button>
        </div>
    `).join('');

    elements.gamesContainer.innerHTML = html;
}

async function loadGameSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        currentSession = await response.json();
        currentRuleset = currentSession.ruleset;

        displayGameSession();

    } catch (error) {
        showErrorMessage(`Failed to load game: ${error.message}`);
        console.error('Load session error:', error);
    }
}

function displayGameSession() {
    if (!currentSession) return;

    elements.gameTitle.textContent = `${currentSession.ruleset.toUpperCase()} Game - ${currentSession.id}`;

    // Display game status
    const status = currentSession.state?.status || 'active';
    const winner = currentSession.state?.winner;
    elements.gameStatus.innerHTML = `
        <h3>Game Status: ${status.toUpperCase()}</h3>
        ${winner ? `<p>Winner: ${winner}</p>` : ''}
        ${currentSession.state?.turn_order ? `<p>Current Turn: ${currentSession.state.active_index || 0}</p>` : ''}
    `;

    // Show appropriate controls
    if (currentRuleset === 'chess') {
        document.getElementById('chess-controls').style.display = 'block';
        document.getElementById('tbs-controls').style.display = 'none';
    } else if (currentRuleset === 'tbs') {
        document.getElementById('chess-controls').style.display = 'none';
        document.getElementById('tbs-controls').style.display = 'block';
    }

    // Display game board/state
    displayGameBoard();

    // Populate unit dropdowns
    populateUnitDropdowns();

    // Initialize TBS action fields
    if (currentRuleset === 'tbs' && elements.tbsActionType) {
        toggleTbsActionFields();
    }
}

function displayGameBoard() {
    if (!currentSession || !currentSession.state) return;

    let boardHtml = '';

    if (currentRuleset === 'chess' && currentSession.state.board) {
        boardHtml = displayChessBoard(currentSession.state.board);
    } else if (currentRuleset === 'tbs') {
        boardHtml = displayTbsBoard(currentSession.state);
    }

    elements.gameBoard.innerHTML = boardHtml;
}

function displayChessBoard(board) {
    let html = '<div class="chess-board">';
    html += '<div style="margin-bottom: 10px; font-weight: bold;">Chess Board</div>';

    for (let rank = 8; rank >= 1; rank--) {
        html += `<span style="display: inline-block; width: 20px;">${rank}</span>`;
        for (let file = 0; file < 8; file++) {
            const square = String.fromCharCode(97 + file) + rank;
            const piece = board[square];
            const isLight = (file + rank) % 2 === 0;

            let cellClass = `piece ${isLight ? 'light' : 'dark'}`;
            let cellContent = '';

            if (piece && piece.type && piece.color) {
                const pieceKey = `${piece.color}_${piece.type}`;
                cellContent = getChessPieceSymbol(pieceKey);
            }

            html += `<span class="${cellClass}" title="${square}">${cellContent}</span>`;
        }
        html += '<br>';
    }

    html += '<span style="display: inline-block; width: 20px;"></span>';
    for (let file = 0; file < 8; file++) {
        html += `<span style="display: inline-block; width: 35px; text-align: center; font-weight: bold;">${String.fromCharCode(97 + file)}</span>`;
    }

    html += '</div>';
    return html;
}

function getChessPieceSymbol(piece) {
    const symbols = {
        'white_king': '♔', 'white_queen': '♕', 'white_rook': '♖',
        'white_bishop': '♗', 'white_knight': '♘', 'white_pawn': '♙',
        'black_king': '♚', 'black_queen': '♛', 'black_rook': '♜',
        'black_bishop': '♝', 'black_knight': '♞', 'black_pawn': '♟'
    };
    return symbols[piece] || '?';
}

function displayTbsBoard(state) {
    if (!state.map) return '<p>No map data available</p>';

    const width = state.map.width;
    const height = state.map.height;
    const obstacles = new Set(state.map.obstacles.map(pos => `${pos.x},${pos.y}`));

    let html = `<div class="tbs-grid" style="grid-template-columns: repeat(${width}, 40px);">`;

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const posKey = `${x},${y}`;
            const isObstacle = obstacles.has(posKey);
            const unit = Object.values(state.units || {}).find(u => u.pos.x === x && u.pos.y === y);

            let cellClass = 'tbs-cell';
            let cellContent = '';
            let cellTitle = `Position (${x}, ${y})`;

            if (isObstacle) {
                cellClass += ' obstacle';
                cellContent = '█';
                cellTitle += ' - Obstacle';
            } else if (unit) {
                cellClass += ` unit ${unit.side}`;
                cellContent = `${unit.name.charAt(0)}${unit.hp}`;
                cellTitle += ` - ${unit.name} (${unit.side}) HP: ${unit.hp}/${unit.max_hp}`;
            } else {
                cellClass += ' empty';
                cellContent = '';
                cellTitle += ' - Empty';
            }

            html += `<div class="${cellClass}" data-pos="${posKey}" title="${cellTitle}">${cellContent}</div>`;
        }
    }

    html += '</div>';
    return html;
}

async function submitChessMove() {
    const fromSquare = elements.chessPieceSelect.value;
    const toSquare = elements.chessMoveSelect.value;

    if (!fromSquare) {
        showErrorMessage('Please select a piece first');
        return;
    }

    if (!toSquare) {
        showErrorMessage('Please select a destination');
        return;
    }

    // Check if game is over
    if (currentSession.state.winner) {
        showErrorMessage(`Game is over! Winner: ${currentSession.state.winner}`);
        return;
    }

    // Parse the move selection - it should be in format "e2e4"
    // But we need to send src and dst separately
    const src = fromSquare;
    const dst = toSquare;

    const action = {
        type: 'move',
        src: src,
        dst: dst
    };

    await submitAction(action);
}

async function submitTbsAction() {
    const actionType = elements.tbsActionType.value;

    // For end_turn, we don't need a unit to be selected
    if (actionType !== 'end_turn') {
        const unitId = elements.tbsUnitSelect.value;
        if (!unitId) {
            showErrorMessage('Please select a unit');
            return;
        }

        // Check if game is over
        if (currentSession.state.winner) {
            showErrorMessage(`Game is over! Winner: ${currentSession.state.winner}`);
            return;
        }

        // Check if the selected unit is the active unit
        const activeUnitId = currentSession.state.turn_order[currentSession.state.active_index];
        if (unitId !== activeUnitId) {
            const activeUnit = currentSession.state.units[activeUnitId];
            const selectedUnit = currentSession.state.units[unitId];
            showErrorMessage(`It's ${activeUnit ? activeUnit.name : 'another unit'}'s turn, not ${selectedUnit ? selectedUnit.name : 'this unit'}'s turn`);
            return;
        }
    }

    let action = { type: actionType };

    if (actionType === 'move') {
        const unitId = elements.tbsUnitSelect.value;
        const movePos = elements.tbsMoveSelect.value;
        if (!movePos) {
            showErrorMessage('Please select a destination');
            return;
        }

        const [x, y] = movePos.split(',').map(n => parseInt(n.trim()));
        action.unit_id = unitId;
        action.to = { x: x, y: y };

    } else if (actionType === 'attack') {
        const unitId = elements.tbsUnitSelect.value;
        const targetId = elements.tbsTargetSelect.value;
        if (!targetId) {
            showErrorMessage('Please select a target');
            return;
        }

        action.attacker_id = unitId;
        action.target_id = targetId;
    }
    // For end_turn, just the type is sufficient

    await submitAction(action);
}

async function submitAction(action) {
    if (!currentSession) return;

    try {
        const response = await fetch(`${API_BASE}/sessions/${currentSession.id}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(action)
        });

        if (!response.ok) {
            let errorMessage = 'Action failed';

            if (response.status === 400) {
                // Show the raw error message from backend
                try {
                    const errorData = await response.json();
                    if (errorData.error) {
                        errorMessage = errorData.error;
                    }
                } catch (parseError) {
                    errorMessage = 'Invalid action';
                }
            } else if (response.status === 404) {
                errorMessage = 'Game session not found';
            } else {
                errorMessage = `Server error (${response.status})`;
            }

            // Show error message
            showErrorMessage(errorMessage);
            return;
        }

        const updatedSession = await response.json();
        currentSession = updatedSession;
        displayGameSession();

        // Clear form inputs
        if (currentRuleset === 'chess') {
            elements.chessPieceSelect.value = '';
            elements.chessMoveSelect.innerHTML = '<option value="">Select destination...</option>';
        } else {
            // Only clear unit select if it's visible (not for end_turn)
            if (elements.tbsActionType.value !== 'end_turn') {
                elements.tbsUnitSelect.value = '';
            }
            elements.tbsMoveSelect.innerHTML = '<option value="">Select destination...</option>';
            elements.tbsTargetSelect.innerHTML = '<option value="">Select target...</option>';
        }

        // Hide evaluation after successful action
        hideEvaluation();

    } catch (error) {
        console.error('Submit action error:', error);
        showErrorMessage('Network error occurred');
    }
}

function toggleTbsActionFields() {
    const actionType = elements.tbsActionType.value;

    if (actionType === 'move') {
        elements.moveFields.style.display = 'block';
        elements.attackFields.style.display = 'none';
        elements.unitSelection.style.display = 'block';
        elements.submitTbsAction.textContent = 'Submit Move';
    } else if (actionType === 'attack') {
        elements.moveFields.style.display = 'none';
        elements.attackFields.style.display = 'block';
        elements.unitSelection.style.display = 'block';
        elements.submitTbsAction.textContent = 'Submit Attack';
    } else if (actionType === 'end_turn') {
        elements.moveFields.style.display = 'none';
        elements.attackFields.style.display = 'none';
        elements.unitSelection.style.display = 'none';
        elements.submitTbsAction.textContent = 'End Turn';
    } else {
        elements.moveFields.style.display = 'none';
        elements.attackFields.style.display = 'none';
        elements.unitSelection.style.display = 'none';
        elements.submitTbsAction.textContent = 'Submit Action';
    }

    // Clear selections when changing action type
    if (elements.tbsUnitSelect) elements.tbsUnitSelect.value = '';
    if (elements.tbsMoveSelect) elements.tbsMoveSelect.value = '';
    if (elements.tbsTargetSelect) elements.tbsTargetSelect.value = '';
    currentEvaluation = null;
    hideEvaluation();
}

function populateUnitDropdowns() {
    if (!currentSession || !currentSession.state) return;

    try {
        if (currentRuleset === 'chess') {
            populateChessPieces();
        } else if (currentRuleset === 'tbs') {
            populateTbsUnits();
        }
    } catch (error) {
        console.error('Error populating unit dropdowns:', error);
        showErrorMessage('Error loading game pieces/units');
    }
}

function populateChessPieces() {
    if (!elements.chessPieceSelect || !currentSession.state.board) return;

    try {
        const select = elements.chessPieceSelect;
        select.innerHTML = '<option value="">Choose a piece...</option>';

        // Get all pieces on the board
        Object.entries(currentSession.state.board).forEach(([square, piece]) => {
            if (piece && piece.type && piece.color) {
                const pieceKey = `${piece.color}_${piece.type}`;
                const pieceType = piece.type.charAt(0).toUpperCase() + piece.type.slice(1);
                const option = document.createElement('option');
                option.value = square;
                option.textContent = `${getChessPieceSymbol(pieceKey)} ${pieceType} at ${square.toUpperCase()}`;
                select.appendChild(option);
            }
        });
    } catch (error) {
        console.error('Error populating chess pieces:', error);
        showErrorMessage('Error loading chess pieces');
        if (elements.chessPieceSelect) {
            elements.chessPieceSelect.innerHTML = '<option value="">Error loading pieces...</option>';
        }
    }
}

function populateTbsUnits() {
    if (!elements.tbsUnitSelect || !currentSession.state.units) return;

    try {
        const select = elements.tbsUnitSelect;
        select.innerHTML = '<option value="">Choose a unit...</option>';

        // Get all units
        Object.entries(currentSession.state.units).forEach(([unitId, unit]) => {
            if (unit.hp > 0) { // Only show alive units
                const option = document.createElement('option');
                option.value = unitId;
                option.textContent = `${unit.name} (${unit.side}) - HP: ${unit.hp}/${unit.max_hp}`;
                select.appendChild(option);
            }
        });
    } catch (error) {
        console.error('Error populating TBS units:', error);
        showErrorMessage('Error loading game units');
        if (elements.tbsUnitSelect) {
            elements.tbsUnitSelect.innerHTML = '<option value="">Error loading units...</option>';
        }
    }
}

async function onChessPieceSelected() {
    const pieceSquare = elements.chessPieceSelect.value;
    if (!pieceSquare) {
        elements.chessMoveSelect.innerHTML = '<option value="">Select destination...</option>';
        return;
    }

    // Check if game is over
    if (currentSession.state.winner) {
        showErrorMessage(`Game is over! Winner: ${currentSession.state.winner}`);
        return;
    }

    try {
        // Get all possible destination squares (8x8 board)
        const files = 'abcdefgh';
        const ranks = '12345678';
        const possibleMoves = [];

        // Try each possible destination square
        for (let file of files) {
            for (let rank of ranks) {
                const dst = file + rank;

                // Skip if same as source
                if (dst === pieceSquare) continue;

                try {
                    const evaluationData = { type: 'move', src: pieceSquare, dst: dst };
                    const response = await fetch(`${API_BASE}/sessions/${currentSession.id}/evaluate`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(evaluationData)
                    });

                    if (response.ok) {
                        const result = await response.json();
                        if (result.ok) {
                            // This is a legal move
                            possibleMoves.push(dst);
                        }
                    }
                } catch (error) {
                    // Ignore individual evaluation errors
                    console.warn(`Failed to evaluate move to ${dst}:`, error);
                }
            }
        }

        // Populate the move select dropdown
        const select = elements.chessMoveSelect;
        select.innerHTML = '<option value="">Select destination...</option>';

        if (possibleMoves.length > 0) {
            possibleMoves.forEach(move => {
                const option = document.createElement('option');
                option.value = move;
                option.textContent = move.toUpperCase();
                select.appendChild(option);
            });

            // Show evaluation for the first move as an example
            if (possibleMoves.length > 0) {
                const firstMove = possibleMoves[0];
                const evaluationData = { type: 'move', src: pieceSquare, dst: firstMove };
                const response = await fetch(`${API_BASE}/sessions/${currentSession.id}/evaluate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(evaluationData)
                });

                if (response.ok) {
                    const result = await response.json();
                    currentEvaluation = result;
                    showEvaluation(result);
                }
            }
        } else {
            select.innerHTML += '<option value="" disabled>No legal moves available</option>';
            showErrorMessage('No legal moves available for this piece');
        }

    } catch (error) {
        console.error('Error evaluating chess moves:', error);
        showErrorMessage('Error evaluating possible moves');
        elements.chessMoveSelect.innerHTML = '<option value="">Error loading moves...</option>';
    }
}

async function onTbsUnitSelected() {
    const unitId = elements.tbsUnitSelect.value;
    const actionType = elements.tbsActionType.value;

    // For end_turn, we don't need to evaluate anything
    if (actionType === 'end_turn') {
        clearMoveOptions();
        return;
    }

    if (!unitId) {
        clearMoveOptions();
        return;
    }

    // Check if game is over
    if (currentSession.state.winner) {
        showErrorMessage(`Game is over! Winner: ${currentSession.state.winner}`);
        return;
    }

    // Check if the selected unit is the active unit
    const activeUnitId = currentSession.state.turn_order[currentSession.state.active_index];
    if (unitId !== activeUnitId) {
        const activeUnit = currentSession.state.units[activeUnitId];
        const selectedUnit = currentSession.state.units[unitId];
        showErrorMessage(`It's ${activeUnit ? activeUnit.name : 'another unit'}'s turn, not ${selectedUnit ? selectedUnit.name : 'this unit'}'s turn`);
        return;
    }

    try {
        if (actionType === 'move') {
            await evaluateTbsMoves(unitId);
        } else if (actionType === 'attack') {
            await evaluateTbsAttacks(unitId);
        }
    } catch (error) {
        console.error('Error in TBS unit selection:', error);
        showErrorMessage('Error processing unit selection');
        clearMoveOptions();
    }
}

async function evaluateTbsMoves(unitId) {
    try {
        const unit = currentSession.state.units[unitId];
        if (!unit) {
            showErrorMessage('Unit not found');
            return;
        }

        // Check if unit is alive
        if (unit.hp <= 0) {
            showErrorMessage('Cannot move: unit is dead');
            return;
        }

        // Check if unit has AP
        if (unit.ap <= 0) {
            showErrorMessage('Cannot move: unit has no Action Points left');
            return;
        }

        const currentX = unit.pos.x;
        const currentY = unit.pos.y;
        const possibleMoves = [];

        // Calculate unit's total range (base 1 + item bonuses)
        const baseRange = 1;
        const rangeBonus = unit.item_ids.reduce((total, itemId) => {
            const item = currentSession.state.items[itemId];
            return total + (item ? item.range_bonus : 0);
        }, 0);
        const totalRange = baseRange + rangeBonus;

        // Try all positions within the unit's range
        for (let dx = -totalRange; dx <= totalRange; dx++) {
            for (let dy = -totalRange; dy <= totalRange; dy++) {
                if (dx === 0 && dy === 0) continue;

                const newX = currentX + dx;
                const newY = currentY + dy;

                // Check bounds
                if (newX >= 0 && newX < currentSession.state.map.width &&
                    newY >= 0 && newY < currentSession.state.map.height) {

                    // Check if within Manhattan distance range
                    const distance = Math.abs(dx) + Math.abs(dy);
                    if (distance <= totalRange) {
                        try {
                            const evaluationData = {
                                type: 'move',
                                unit_id: unitId,
                                to: { x: newX, y: newY }
                            };

                            const response = await fetch(`${API_BASE}/sessions/${currentSession.id}/evaluate`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(evaluationData)
                            });

                            if (response.ok) {
                                const result = await response.json();
                                if (result.ok) {
                                    // This is a legal move
                                    possibleMoves.push(`${newX},${newY}`);
                                }
                            }
                        } catch (error) {
                            console.warn(`Failed to evaluate move to (${newX},${newY}):`, error);
                        }
                    }
                }
            }
        }

        // Populate move options
        populateMoveOptionsFromAPI(unitId, possibleMoves);

        // Show evaluation for the first move if available
        if (possibleMoves.length > 0) {
            const firstMove = possibleMoves[0];
            const [x, y] = firstMove.split(',').map(n => parseInt(n.trim()));
            const evaluationData = {
                type: 'move',
                unit_id: unitId,
                to: { x: x, y: y }
            };

            const response = await fetch(`${API_BASE}/sessions/${currentSession.id}/evaluate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(evaluationData)
            });

            if (response.ok) {
                const result = await response.json();
                currentEvaluation = result;
                showEvaluation(result);
            }
        } else {
            // No moves available - show error message
            showErrorMessage('No legal moves available for this unit');
        }

    } catch (error) {
        console.error('Evaluation error:', error);
        showErrorMessage('Network error during move evaluation');
    }
}

async function evaluateTbsAttacks(unitId) {
    try {
        const attacker = currentSession.state.units[unitId];
        if (!attacker) {
            showErrorMessage('Unit not found');
            return;
        }

        // Check if attacker is alive
        if (attacker.hp <= 0) {
            showErrorMessage('Cannot attack: unit is dead');
            return;
        }

        // Check if attacker has AP
        if (attacker.ap <= 0) {
            showErrorMessage('Cannot attack: unit has no Action Points left');
            return;
        }

        const possibleTargets = [];

        // Try all possible target units and evaluate each attack
        for (const [targetId, target] of Object.entries(currentSession.state.units)) {
            if (targetId !== unitId && target.hp > 0 && target.side !== attacker.side) {
                try {
                    const evaluationData = {
                        type: 'attack',
                        attacker_id: unitId,
                        target_id: targetId
                    };

                    const response = await fetch(`${API_BASE}/sessions/${currentSession.id}/evaluate`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(evaluationData)
                    });

                    if (response.ok) {
                        const result = await response.json();
                        if (result.ok) {
                            // This is a valid attack target
                            possibleTargets.push(targetId);
                        }
                    }
                } catch (error) {
                    console.warn(`Failed to evaluate attack on ${targetId}:`, error);
                }
            }
        }

        // Populate target options
        populateTargetOptionsFromAPI(unitId, possibleTargets);

        // Show evaluation for the first target if available
        if (possibleTargets.length > 0) {
            const firstTarget = possibleTargets[0];
            const evaluationData = {
                type: 'attack',
                attacker_id: unitId,
                target_id: firstTarget
            };

            const response = await fetch(`${API_BASE}/sessions/${currentSession.id}/evaluate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(evaluationData)
            });

            if (response.ok) {
                const result = await response.json();
                currentEvaluation = result;
                showEvaluation(result);
            }
        } else {
            // No targets available - show error message
            showErrorMessage('No valid attack targets available for this unit');
        }

    } catch (error) {
        console.error('Error evaluating TBS attacks:', error);
        showErrorMessage('Error evaluating attack targets');
    }
}

function populateMoveOptionsFromAPI(unitId, possibleMoves) {
    if (!elements.tbsMoveSelect) return;

    try {
        const select = elements.tbsMoveSelect;
        select.innerHTML = '<option value="">Select destination...</option>';

        if (Array.isArray(possibleMoves)) {
            if (possibleMoves.length > 0) {
                possibleMoves.forEach(move => {
                    const option = document.createElement('option');
                    option.value = move;
                    option.textContent = `(${move})`;
                    select.appendChild(option);
                });
            } else {
                // No moves available
                const option = document.createElement('option');
                option.value = '';
                option.disabled = true;
                option.textContent = 'No legal moves available';
                select.appendChild(option);
            }
        } else {
            // Fallback to old logic if possibleMoves is not an array
            const unit = currentSession.state.units[unitId];
            if (!unit) return;

            const currentX = unit.pos.x;
            const currentY = unit.pos.y;

            // Calculate unit's total range (base 1 + item bonuses)
            const baseRange = 1;
            const rangeBonus = unit.item_ids.reduce((total, itemId) => {
                const item = currentSession.state.items[itemId];
                return total + (item ? item.range_bonus : 0);
            }, 0);
            const totalRange = baseRange + rangeBonus;

            // Generate moves within range
            const moves = [];
            for (let dx = -totalRange; dx <= totalRange; dx++) {
                for (let dy = -totalRange; dy <= totalRange; dy++) {
                    if (dx === 0 && dy === 0) continue;
                    const newX = currentX + dx;
                    const newY = currentY + dy;

                    // Check bounds and obstacles
                    if (newX >= 0 && newX < currentSession.state.map.width &&
                        newY >= 0 && newY < currentSession.state.map.height) {

                        // Check if within Manhattan distance range
                        const distance = Math.abs(dx) + Math.abs(dy);
                        if (distance <= totalRange) {
                            const isObstacle = currentSession.state.map.obstacles.some(
                                obs => obs.x === newX && obs.y === newY
                            );

                            if (!isObstacle) {
                                moves.push(`${newX},${newY}`);
                            }
                        }
                    }
                }
            }

            moves.forEach(move => {
                const option = document.createElement('option');
                option.value = move;
                option.textContent = `(${move})`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error populating move options from API:', error);
        showErrorMessage('Error loading move options');
        if (elements.tbsMoveSelect) {
            elements.tbsMoveSelect.innerHTML = '<option value="">Error loading moves...</option>';
        }
    }
}

function populateTargetOptionsFromAPI(attackerId, possibleTargets) {
    if (!elements.tbsTargetSelect) return;

    try {
        const select = elements.tbsTargetSelect;
        select.innerHTML = '<option value="">Select target...</option>';

        if (Array.isArray(possibleTargets)) {
            if (possibleTargets.length > 0) {
                possibleTargets.forEach(targetId => {
                    const target = currentSession.state.units[targetId];
                    if (target) {
                        const option = document.createElement('option');
                        option.value = targetId;
                        option.textContent = `${target.name} (${target.side}) - HP: ${target.hp}`;
                        select.appendChild(option);
                    }
                });
            } else {
                // No targets available
                const option = document.createElement('option');
                option.value = '';
                option.disabled = true;
                option.textContent = 'No valid targets available';
                select.appendChild(option);
            }
        } else {
            // Fallback to old logic if possibleTargets is not an array
            const attacker = currentSession.state.units[attackerId];
            if (!attacker) return;

            // Find potential targets (enemy units in range)
            Object.entries(currentSession.state.units).forEach(([unitId, unit]) => {
                if (unitId !== attackerId && unit.hp > 0 && unit.side !== attacker.side) {
                    // Check if in attack range (simplified distance check)
                    const distance = Math.abs(unit.pos.x - attacker.pos.x) + Math.abs(unit.pos.y - attacker.pos.y);
                    if (distance <= 2) { // Arbitrary range
                        const option = document.createElement('option');
                        option.value = unitId;
                        option.textContent = `${unit.name} (${unit.side}) - HP: ${unit.hp}`;
                        select.appendChild(option);
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error populating target options from API:', error);
        showErrorMessage('Error loading attack targets');
        if (elements.tbsTargetSelect) {
            elements.tbsTargetSelect.innerHTML = '<option value="">Error loading targets...</option>';
        }
    }
}

function clearMoveOptions() {
    if (elements.tbsMoveSelect) {
        elements.tbsMoveSelect.innerHTML = '<option value="">Select destination...</option>';
    }
    if (elements.tbsTargetSelect) {
        elements.tbsTargetSelect.innerHTML = '<option value="">Select target...</option>';
    }
    if (elements.chessMoveSelect) {
        elements.chessMoveSelect.innerHTML = '<option value="">Select destination...</option>';
    }
    currentEvaluation = null;
    hideEvaluation();
}

function onTbsMoveSelected() {
    // Could show preview of the move
    const movePos = elements.tbsMoveSelect.value;
    if (movePos && currentEvaluation) {
        showEvaluation(currentEvaluation);
    }
}

function onTbsTargetSelected() {
    // Could show attack preview
    const targetId = elements.tbsTargetSelect.value;
    if (targetId) {
        // You could evaluate the specific attack here
    }
}

function showEvaluation(evaluation) {
    if (!elements.evaluationResult || !elements.evalOutput) return;

    elements.evaluationResult.style.display = 'block';
    elements.evalOutput.textContent = JSON.stringify(evaluation, null, 2);
}

function hideEvaluation() {
    if (elements.evaluationResult) {
        elements.evaluationResult.style.display = 'none';
    }
    currentEvaluation = null;
}

function showErrorMessage(message) {
    // Create or update error display element
    let errorDiv = document.getElementById('error-message');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'error-message';
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff4444;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 1000;
            max-width: 400px;
            font-family: Arial, sans-serif;
            border-left: 4px solid #cc0000;
        `;

        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '×';
        closeBtn.style.cssText = `
            position: absolute;
            top: 5px;
            right: 10px;
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        closeBtn.onclick = () => errorDiv.remove();

        errorDiv.appendChild(closeBtn);
        document.body.appendChild(errorDiv);
    }

    errorDiv.innerHTML = `
        <button onclick="this.parentElement.remove()" style="
            position: absolute;
            top: 5px;
            right: 10px;
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        ">×</button>
        <div>${message}</div>
    `;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentElement) {
            errorDiv.remove();
        }
    }, 5000);
}
