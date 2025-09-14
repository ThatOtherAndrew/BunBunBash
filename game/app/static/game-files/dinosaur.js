// Game state
let gameState = {
    running: false,
    paused: false,
    score: 0,
    lastDataTime: 0
};

// Game logic
class Game {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.player = { x: 50, y: 300, width: 20, height: 20, dy: 0, grounded: true };
        this.obstacles = [];
        this.animationId = null;
        this.obstacleSpawnTimer = 0;
        this.obstacleSpawnRate = 120; // Spawn obstacle every 120 frames (2 seconds at 60fps)
    }

    start() {
        gameState.running = true;
        gameState.paused = false;
        document.getElementById('game-status').textContent = 'Running - Press SPACEBAR to jump!';
        this.gameLoop();
    }

    pause() {
        gameState.paused = !gameState.paused;
        document.getElementById('game-status').textContent = 
            gameState.paused ? 'Paused' : 'Running - Press SPACEBAR to jump!';
    }

    reset() {
        gameState.running = false;
        gameState.paused = false;
        gameState.score = 0;
        this.player = { x: 50, y: 300, width: 20, height: 20, dy: 0, grounded: true };
        this.obstacles = [];
        this.obstacleSpawnTimer = 0;
        document.getElementById('game-status').textContent = 'Press Start to begin';
        
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        this.draw();
    }

    jump() {
        // Jump only if player is grounded and game is running
        if (this.player.grounded && gameState.running && !gameState.paused) {
            this.player.dy = -15; // Jump velocity
            this.player.grounded = false;
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
        
        // Spawn obstacles periodically
        this.obstacleSpawnTimer++;
        if (this.obstacleSpawnTimer >= this.obstacleSpawnRate) {
            this.obstacles.push({
                x: this.canvas.width,
                y: 290, // Move up to sit on the ground line (320 - 30 = 290)
                width: 20,
                height: 30
            });
            this.obstacleSpawnTimer = 0;
            
            // Gradually increase difficulty by decreasing spawn rate
            if (this.obstacleSpawnRate > 60) {
                this.obstacleSpawnRate -= 0.5;
            }
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
        document.getElementById('game-status').textContent = `Game Over! Score: ${gameState.score} - Press Reset to play again`;
    }

    draw() {
        // Clear canvas
        this.ctx.fillStyle = '#fff';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw ground
        this.ctx.fillStyle = '#333';
        this.ctx.fillRect(0, 320, this.canvas.width, 2);
        
        // Draw player (simple rectangle dinosaur)
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
        
        // Draw instructions when not running
        if (!gameState.running && !gameState.paused) {
            this.ctx.fillStyle = '#666';
            this.ctx.font = '14px Arial';
            this.ctx.fillText('Press Start, then use SPACEBAR to jump over obstacles', 200, 200);
        }
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
    
    // Controls
    document.getElementById('start-btn').addEventListener('click', () => game.start());
    document.getElementById('pause-btn').addEventListener('click', () => game.pause());
    document.getElementById('reset-btn').addEventListener('click', () => game.reset());
    
    // Keyboard controls - spacebar to jump
    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            game.jump();
            e.preventDefault(); // Prevent page scrolling
        }
    });
    
    // Initial draw
    game.draw();
});