// Game state
let gameState = {
    running: false,
    paused: false,
    score: 0,
    dataBuffer: [],
    lastDataTime: 0
};

// Data handling
class DataHandler {
    constructor() {
        this.buffer = [];
        this.maxBufferSize = 100;
        this.dataCallbacks = [];
    }

    // Simulate HTTP data fetching
    async fetchData() {
        try {
            // Replace with your actual HTTP endpoint
            // const response = await fetch('/api/data');
            // const data = await response.json();
            
            // Simulated data for demo
            const data = {
                value: Math.sin(Date.now() / 1000) + Math.random() * 0.5,
                timestamp: Date.now()
            };
            
            this.addData(data);
            return data;
        } catch (error) {
            console.error('Data fetch error:', error);
            return null;
        }
    }

    addData(dataPoint) {
        this.buffer.push(dataPoint);
        if (this.buffer.length > this.maxBufferSize) {
            this.buffer.shift();
        }
        
        // Notify callbacks
        this.dataCallbacks.forEach(callback => callback(dataPoint));
        
        // Update displays
        this.updateDataDisplay(dataPoint);
        this.updateWaveVisualization();
    }

    updateDataDisplay(dataPoint) {
        document.getElementById('current-value').textContent = 
            `Value: ${dataPoint.value.toFixed(3)}`;
        document.getElementById('connection-status').textContent = 
            'Connected';
    }

    updateWaveVisualization() {
        const svg = document.getElementById('header-wave');
        const path = document.getElementById('wave-path');
        const points = document.getElementById('wave-points');
        
        if (this.buffer.length < 2) return;
        
        const width = 300;
        const height = 100;
        const stepX = width / (this.buffer.length - 1);
        
        // Create path
        let pathData = '';
        this.buffer.forEach((point, i) => {
            const x = i * stepX;
            const y = height/2 + point.value * 20; // Scale the data
            
            if (i === 0) {
                pathData += `M ${x} ${y}`;
            } else {
                pathData += ` L ${x} ${y}`;
            }
        });
        
        path.setAttribute('d', pathData);
        
        // Add points for recent peaks
        points.innerHTML = '';
        this.buffer.slice(-5).forEach((point, i) => {
            if (Math.abs(point.value) > 0.8) { // Peak threshold
                const x = (this.buffer.length - 5 + i) * stepX;
                const y = height/2 + point.value * 20;
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', x);
                circle.setAttribute('cy', y);
                circle.setAttribute('r', 3);
                points.appendChild(circle);
            }
        });
    }

    onData(callback) {
        this.dataCallbacks.push(callback);
    }
}

// Game logic
class Game {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.player = { x: 50, y: 300, width: 20, height: 20, dy: 0, grounded: true };
        this.obstacles = [];
        this.animationId = null;
    }

    start() {
        gameState.running = true;
        gameState.paused = false;
        document.getElementById('game-status').textContent = 'Running';
        this.gameLoop();
    }

    pause() {
        gameState.paused = !gameState.paused;
        document.getElementById('game-status').textContent = 
            gameState.paused ? 'Paused' : 'Running';
    }

    reset() {
        gameState.running = false;
        gameState.paused = false;
        gameState.score = 0;
        this.player = { x: 50, y: 300, width: 20, height: 20, dy: 0, grounded: true };
        this.obstacles = [];
        document.getElementById('game-status').textContent = 'Press Start to begin';
        
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        this.draw();
    }

    handleDataPoint(dataPoint) {
        // Jump when data exceeds threshold
        if (Math.abs(dataPoint.value) > 0.8 && this.player.grounded) {
            this.player.dy = -15; // Jump velocity
            this.player.grounded = false;
        }
        
        // Add obstacles based on data
        if (Math.random() < Math.abs(dataPoint.value) * 0.3) {
            this.obstacles.push({
                x: this.canvas.width,
                y: 350,
                width: 20,
                height: 30
            });
        }
    }

    update() {
        if (!gameState.running || gameState.paused) return;
        
        // Player physics
        this.player.dy += 0.8; // Gravity
        this.player.y += this.player.dy;
        
        // Ground collision
        if (this.player.y >= 300) {
            this.player.y = 300;
            this.player.dy = 0;
            this.player.grounded = true;
        }
        
        // Update obstacles
        this.obstacles.forEach((obstacle, index) => {
            obstacle.x -= 5;
            if (obstacle.x + obstacle.width < 0) {
                this.obstacles.splice(index, 1);
                gameState.score += 10;
            }
        });
        
        // Collision detection
        this.checkCollisions();
    }

    checkCollisions() {
        this.obstacles.forEach(obstacle => {
            if (this.player.x < obstacle.x + obstacle.width &&
                this.player.x + this.player.width > obstacle.x &&
                this.player.y < obstacle.y + obstacle.height &&
                this.player.y + this.player.height > obstacle.y) {
                this.gameOver();
            }
        });
    }

    gameOver() {
        gameState.running = false;
        document.getElementById('game-status').textContent = `Game Over! Score: ${gameState.score}`;
    }

    draw() {
        // Clear canvas
        this.ctx.fillStyle = '#fff';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw ground
        this.ctx.fillStyle = '#333';
        this.ctx.fillRect(0, 320, this.canvas.width, 2);
        
        // Draw player
        this.ctx.fillStyle = '#333';
        this.ctx.fillRect(this.player.x, this.player.y, this.player.width, this.player.height);
        
        // Draw obstacles
        this.ctx.fillStyle = '#666';
        this.obstacles.forEach(obstacle => {
            this.ctx.fillRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height);
        });
        
        // Draw score
        this.ctx.fillStyle = '#333';
        this.ctx.font = '16px Arial';
        this.ctx.fillText(`Score: ${gameState.score}`, 10, 30);
    }

    gameLoop() {
        this.update();
        this.draw();
        
        if (gameState.running) {
            this.animationId = requestAnimationFrame(() => this.gameLoop());
        }
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('game-canvas');
    const game = new Game(canvas);
    const dataHandler = new DataHandler();
    
    // Connect data to game
    dataHandler.onData(dataPoint => game.handleDataPoint(dataPoint));
    
    // Controls
    document.getElementById('start-btn').addEventListener('click', () => game.start());
    document.getElementById('pause-btn').addEventListener('click', () => game.pause());
    document.getElementById('reset-btn').addEventListener('click', () => game.reset());
    
    // Keyboard controls
    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && game.player.grounded) {
            game.player.dy = -15;
            game.player.grounded = false;
            e.preventDefault();
        }
    });
    
    // Start data fetching
    setInterval(() => {
        if (gameState.running) {
            dataHandler.fetchData();
        }
    }, 100); // Fetch every 100ms
    
    // Initial draw
    game.draw();
});