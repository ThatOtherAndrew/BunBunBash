// Game state
let gameState = {
    running: false,
    paused: false,
    score: 0,
    timeLeft: 60, // 60 second game
    gameTimer: null,
    moles: [],
    difficultyLevel: 0 // 0-5 (6 levels over 60 seconds)
};

// Image loading
const moleImages = {
    good: null,
    bad: null,
    loading: true
};

const backgroundImages = {
    background: null,
    bottomOverlay: null,
    loading: true
};

const bashImages = {
    frame1: null,
    frame2: null,
    loading: true
};

// Load images
function loadImages() {
    const goodImg = new Image();
    const badImg = new Image();
    const backgroundImg = new Image();
    const bottomOverlayImg = new Image();
    const bashFrame1Img = new Image();
    const bashFrame2Img = new Image();
    
    let loadedCount = 0;
    const totalImages = 6; // Loading 6 images now (good, bad, background, bottom overlay, bash frames)
    const checkAllLoaded = () => {
        loadedCount++;
        if (loadedCount === totalImages) {
            moleImages.loading = false;
            backgroundImages.loading = false;
            bashImages.loading = false;
            console.log('All images loaded');
        }
    };
    
    goodImg.onload = () => {
        moleImages.good = goodImg;
        checkAllLoaded();
    };
    
    badImg.onload = () => {
        moleImages.bad = badImg;
        checkAllLoaded();
    };
    
    backgroundImg.onload = () => {
        backgroundImages.background = backgroundImg;
        checkAllLoaded();
    };
    
    bottomOverlayImg.onload = () => {
        backgroundImages.bottomOverlay = bottomOverlayImg;
        checkAllLoaded();
    };
    
    bashFrame1Img.onload = () => {
        bashImages.frame1 = bashFrame1Img;
        checkAllLoaded();
    };
    
    bashFrame2Img.onload = () => {
        bashImages.frame2 = bashFrame2Img;
        checkAllLoaded();
    };
    
    // Set image sources
    goodImg.src = '/static/images/good-mole.png';
    badImg.src = '/static/images/bad-mole.png';
    backgroundImg.src = '/static/images/holes_background.png';
    bottomOverlayImg.src = '/static/images/holes_bottom_overlay.png';
    bashFrame1Img.src = '/static/images/bash_animation_1.png';
    bashFrame2Img.src = '/static/images/bash_animation_2.png';
    
    // Fallback if images don't load
    goodImg.onerror = () => {
        console.warn('Good mole image failed to load');
        checkAllLoaded();
    };
    
    badImg.onerror = () => {
        console.warn('Bad mole image failed to load');
        checkAllLoaded();
    };
    
    backgroundImg.onerror = () => {
        console.warn('Background image failed to load');
        checkAllLoaded();
    };
    
    bottomOverlayImg.onerror = () => {
        console.warn('Bottom overlay image failed to load');
        checkAllLoaded();
    };
    
    bashFrame1Img.onerror = () => {
        console.warn('Bash frame 1 image failed to load');
        checkAllLoaded();
    };
    
    bashFrame2Img.onerror = () => {
        console.warn('Bash frame 2 image failed to load');
        checkAllLoaded();
    };
}

// Mole class
class Mole {
    constructor(id, x, y) {
        this.id = id;
        this.x = x;
        this.y = y;
        this.baseY = y; // Store the base position (bottom of hole)
        this.radius = 180; // 3 times bigger (60 * 3)
        this.isVisible = false;
        this.isHit = false;
        this.isGoodMole = true; // Will be randomized when shown
        this.visibilityTimer = null;
        // Difficulty settings will be set dynamically based on game time
        
        // Animation properties
        this.animationProgress = 0; // 0 = hidden, 1 = fully visible
        this.isAnimating = false;
        
        // Bash animation properties
        this.isBashAnimating = false;
        this.bashFrame = 0; // 0 = no animation, 1 = frame 1, 2 = frame 2
        this.bashTimer = null;
    }

    show() {
        if (!gameState.running || gameState.paused) return;
        
        this.isVisible = true;
        this.isHit = false;
        this.isAnimating = true;
        this.animationProgress = 0;
        
        // 75% chance of good mole, 25% chance of bad mole
        const randomValue = Math.random();
        this.isGoodMole = randomValue < 0.75;
        
        // Get current difficulty settings
        const difficulty = getDifficultySettings();
        
        // Debug logging
        console.log(`Mole ${this.id}: ${this.isGoodMole ? 'GOOD' : 'BAD'} (Level ${gameState.difficultyLevel}, random: ${randomValue.toFixed(3)})`);
        
        // Schedule hiding after random time based on current difficulty
        const showDuration = Math.random() * (difficulty.maxShowTime - difficulty.minShowTime) + difficulty.minShowTime;
        this.visibilityTimer = setTimeout(() => {
            this.hide();
        }, showDuration);
    }

    hide() {
        this.isVisible = false;
        this.isHit = false;
        this.isAnimating = true;
        // Don't change animationProgress here - let update() handle the animation
        
        if (this.visibilityTimer) {
            clearTimeout(this.visibilityTimer);
            this.visibilityTimer = null;
        }
        
        // Schedule next appearance after random time based on current difficulty
        if (gameState.running && !gameState.paused) {
            const difficulty = getDifficultySettings();
            const hideDuration = Math.random() * (difficulty.maxHideTime - difficulty.minHideTime) + difficulty.minHideTime;
            setTimeout(() => {
                this.show();
            }, hideDuration);
        }
    }

    update() {
        if (this.isAnimating) {
            // Get current difficulty settings for animation speed
            const difficulty = getDifficultySettings();
            
            if (this.isVisible) {
                // Pop out animation (showing)
                this.animationProgress += difficulty.animationSpeed;
                if (this.animationProgress >= 1) {
                    this.animationProgress = 1;
                    this.isAnimating = false;
                }
            } else {
                // Pop in animation (hiding)
                this.animationProgress -= difficulty.animationSpeed;
                if (this.animationProgress <= 0) {
                    this.animationProgress = 0;
                    this.isAnimating = false;
                }
            }
            
            // Calculate animated Y position (pop out effect)
            const popHeight = 290; // How high the mole pops out
            this.y = this.baseY - (this.animationProgress * popHeight);
        }
    }

    startBashAnimation() {
        this.isBashAnimating = true;
        this.bashFrame = 1;
        
        // Show frame 1 for 150ms
        this.bashTimer = setTimeout(() => {
            this.bashFrame = 2;
            
            // Show frame 2 for 150ms, then end animation
            this.bashTimer = setTimeout(() => {
                this.isBashAnimating = false;
                this.bashFrame = 0;
                this.bashTimer = null;
            }, 350);
        }, 100);
    }

    hit() {
        if (this.isVisible && !this.isHit) {
            this.isHit = true;
            
            // Start bash animation
            this.startBashAnimation();
            
            // Award or deduct points based on mole type
            if (this.isGoodMole) {
                gameState.score += 10;
            } else {
                gameState.score -= 20;
            }
            
            // Hide after bash animation completes
            setTimeout(() => {
                this.hide();
            }, 400); // Longer delay to show bash animation
            
            return true;
        }
        return false;
    }

    draw(ctx) {
        if (this.animationProgress <= 0) return;
        
        // Draw mole using image if loaded, otherwise fallback to colored circle
        const useImages = !moleImages.loading && moleImages.good && moleImages.bad;
        
        if (useImages) {
            const image = this.isGoodMole ? moleImages.good : moleImages.bad;
            const size = this.radius * 2;
            
            try {
                // Draw the mole image
                ctx.drawImage(image, this.x - this.radius, this.y - this.radius, size, size);
                
                // Hit effect removed - bash animation provides visual feedback
            } catch (error) {
                console.error('Error drawing mole image:', error);
                // Fall back to colored circle if image drawing fails
                this.drawFallbackMole(ctx);
            }
            
        } else {
            // Fallback: draw colored circles if images aren't loaded
            this.drawFallbackMole(ctx);
        }
    }
    
    drawFallbackMole(ctx) {
        if (this.isHit) {
            ctx.fillStyle = '#ff6b6b'; // Red when hit
        } else if (this.isGoodMole) {
            ctx.fillStyle = '#4CAF50'; // Green for good moles
        } else {
            ctx.fillStyle = '#f44336'; // Red for bad moles
        }
        
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, 2 * Math.PI);
        ctx.fill();
        
        // Simple face for fallback
        ctx.fillStyle = '#000';
        
        // Eyes
        ctx.beginPath();
        ctx.arc(this.x - 18, this.y - 12, 4, 0, 2 * Math.PI);
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(this.x + 18, this.y - 12, 4, 0, 2 * Math.PI);
        ctx.fill();
        
        // Nose
        ctx.beginPath();
        ctx.arc(this.x, this.y + 3, 3, 0, 2 * Math.PI);
        ctx.fill();
        
        // Show type for fallback
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 12px Magic Alphabet';
        ctx.textAlign = 'center';
        ctx.fillText(this.isGoodMole ? 'GOOD' : 'BAD', this.x, this.y + 25);
    }
    
    drawBashAnimation(ctx) {
        if (!this.isBashAnimating || this.bashFrame === 0) return;
        
        // Draw bash animation using images if loaded
        const useImages = !bashImages.loading && bashImages.frame1 && bashImages.frame2;
        
        if (useImages) {
            const image = this.bashFrame === 1 ? bashImages.frame1 : bashImages.frame2;
            const size = this.radius * 1.5; // Slightly smaller than the bunny
            const offsetY = -this.radius * 1.18; // Position higher above the bunny
            
            try {
                // Draw the bash animation image above the mole
                ctx.drawImage(image, this.x - this.radius * 0.75, this.y + offsetY, size, size);
            } catch (error) {
                console.error('Error drawing bash animation image:', error);
                // Fall back to simple visual effect if image drawing fails
                this.drawFallbackBashAnimation(ctx);
            }
        } else {
            // Fallback: draw simple visual effect if images aren't loaded
            this.drawFallbackBashAnimation(ctx);
        }
    }
    
    drawFallbackBashAnimation(ctx) {
        // Simple fallback bash effect - a pulsing circle above the bunny
        const offsetY = -this.radius * 1.18; // Position higher above the bunny
        ctx.save();
        ctx.strokeStyle = '#ff6b6b';
        ctx.lineWidth = 8;
        ctx.beginPath();
        ctx.arc(this.x, this.y + offsetY, this.radius * 0.6, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.restore();
    }
}

// Difficulty progression system
function getDifficultySettings() {
    const timeElapsed = 60 - gameState.timeLeft;
    const difficultyLevel = Math.floor(timeElapsed / 10); // New level every 10 seconds
    
    // Update global difficulty level
    gameState.difficultyLevel = Math.min(difficultyLevel, 5); // Cap at level 5
    
    // Define difficulty settings for each level (0-5)
    const difficultySettings = [
        // Level 0 (0-9s): Very slow start
        { minShowTime: 800, maxShowTime: 2500, minHideTime: 1500, maxHideTime: 4000, animationSpeed: 0.02 },
        // Level 1 (10-19s): Slow
        { minShowTime: 600, maxShowTime: 2200, minHideTime: 1200, maxHideTime: 3800, animationSpeed: 0.025 },
        // Level 2 (20-29s): Medium-slow
        { minShowTime: 500, maxShowTime: 2000, minHideTime: 1000, maxHideTime: 3500, animationSpeed: 0.03 },
        // Level 3 (30-39s): Medium
        { minShowTime: 400, maxShowTime: 1800, minHideTime: 800, maxHideTime: 3200, animationSpeed: 0.035 },
        // Level 4 (40-49s): Fast
        { minShowTime: 300, maxShowTime: 1600, minHideTime: 600, maxHideTime: 3000, animationSpeed: 0.04 },
        // Level 5 (50-60s): Very fast
        { minShowTime: 200, maxShowTime: 1400, minHideTime: 400, maxHideTime: 2800, animationSpeed: 0.045 }
    ];
    
    return difficultySettings[gameState.difficultyLevel];
}

// Game logic
class WhackAMoleGame {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // Set canvas dimensions to match the container
        const container = canvas.parentElement;
        const rect = container.getBoundingClientRect();
        
        // Use fallback dimensions if container isn't ready
        this.logicalWidth = rect.width > 0 ? rect.width : 800;
        this.logicalHeight = rect.height > 0 ? rect.height : 400;
        
        console.log(`Initial canvas size: ${this.logicalWidth}x${this.logicalHeight}`);
        
        // Set the canvas size attributes
        canvas.width = this.logicalWidth;
        canvas.height = this.logicalHeight;

        // Handle high-DPI displays
        const dpr = window.devicePixelRatio || 1;

        // Upscale the backing store
        canvas.width = this.logicalWidth * dpr;
        canvas.height = this.logicalHeight * dpr;

        // Scale the drawing context so your coordinates stay the same
        this.ctx.scale(dpr, dpr);

        this.animationId = null;

        // Initialize 3 moles at bottom of screen with proper spacing to align with background holes
        const holeSpacing = this.logicalWidth / 8; // Space holes further apart
        this.moles = [
            new Mole(0, holeSpacing * 1.86, this.logicalHeight - 50), // Left hole - moved down 100px
            new Mole(1, holeSpacing * 4.04, this.logicalHeight - 50),   // Center hole - moved down 100px
            new Mole(2, holeSpacing * 6.22, this.logicalHeight - 50)  // Right hole - moved down 100px
        ];

        gameState.moles = this.moles;
    }

    start() {
        // Prevent starting if game is already running
        if (gameState.running && !gameState.paused) {
            console.log('Game is already running!');
            return;
        }
        
        // Clear any existing timer to prevent multiple timers running
        if (gameState.gameTimer) {
            clearInterval(gameState.gameTimer);
            gameState.gameTimer = null;
        }
        
        // Clear any existing mole timers to prevent multiple mole appearances
        this.moles.forEach(mole => {
            if (mole.visibilityTimer) {
                clearTimeout(mole.visibilityTimer);
                mole.visibilityTimer = null;
            }
            if (mole.bashTimer) {
                clearTimeout(mole.bashTimer);
                mole.bashTimer = null;
            }
            mole.isVisible = false;
            mole.isHit = false;
            mole.isAnimating = false;
            mole.animationProgress = 0;
            mole.isBashAnimating = false;
            mole.bashFrame = 0;
        });
        
        gameState.running = true;
        gameState.paused = false;
        gameState.score = 0;
        gameState.timeLeft = 60;
        gameState.difficultyLevel = 0; // Reset difficulty level
        
        console.log('Game started - Use A-F keys - Green moles: +10 pts, Red moles: -20 pts!');
        
        // Start game timer
        gameState.gameTimer = setInterval(() => {
            if (!gameState.paused) {
                gameState.timeLeft--;
                if (gameState.timeLeft <= 0) {
                    this.gameOver();
                }
            }
        }, 1000);
        
        // Start mole appearances with random delays
        this.moles.forEach((mole) => {
            // Random initial delay between 0-3 seconds
            const randomDelay = Math.random() * 3000;
            setTimeout(() => {
                mole.show();
            }, randomDelay);
        });
        
        this.gameLoop();
    }

    pause() {
        gameState.paused = !gameState.paused;
        console.log(gameState.paused ? 'Game paused' : 'Game resumed');
    }

    reset() {
        gameState.running = false;
        gameState.paused = false;
        gameState.score = 0;
        gameState.timeLeft = 60;
        
        // Clear timers
        if (gameState.gameTimer) {
            clearInterval(gameState.gameTimer);
            gameState.gameTimer = null;
        }
        
        // Hide all moles and clear their timers
        this.moles.forEach(mole => {
            mole.isVisible = false;
            mole.isHit = false;
            if (mole.visibilityTimer) {
                clearTimeout(mole.visibilityTimer);
                mole.visibilityTimer = null;
            }
            // Clear bash animation
            if (mole.bashTimer) {
                clearTimeout(mole.bashTimer);
                mole.bashTimer = null;
            }
            mole.isBashAnimating = false;
            mole.bashFrame = 0;
        });
        
        console.log('Game reset - Press Start to begin');
        
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        this.draw();
    }
    
    resize() {
        // Recalculate canvas dimensions
        const container = this.canvas.parentElement;
        const rect = container.getBoundingClientRect();
        
        // Ensure we have valid dimensions
        if (rect.width <= 0 || rect.height <= 0) {
            console.log('Container not ready, retrying...');
            setTimeout(() => this.resize(), 50);
            return;
        }
        
        this.logicalWidth = rect.width;
        this.logicalHeight = rect.height;
        
        console.log(`Resizing canvas to: ${this.logicalWidth}x${this.logicalHeight}`);
        
        // Set the canvas size attributes
        this.canvas.width = this.logicalWidth;
        this.canvas.height = this.logicalHeight;

        // Handle high-DPI displays
        const dpr = window.devicePixelRatio || 1;

        // Upscale the backing store
        this.canvas.width = this.logicalWidth * dpr;
        this.canvas.height = this.logicalHeight * dpr;

        // Scale the drawing context so your coordinates stay the same
        this.ctx.scale(dpr, dpr);
        
        // Update mole positions for new canvas size with proper spacing to align with background holes
        const holeSpacing = this.logicalWidth / 8;
        this.moles[0].x = holeSpacing * 1.86;
        this.moles[0].y = this.logicalHeight - 50;
        this.moles[0].baseY = this.logicalHeight - 50;
        this.moles[1].x = holeSpacing * 4.04;
        this.moles[1].y = this.logicalHeight - 50;
        this.moles[1].baseY = this.logicalHeight - 50;
        this.moles[2].x = holeSpacing * 6.22;
        this.moles[2].y = this.logicalHeight - 50;
        this.moles[2].baseY = this.logicalHeight - 50;
        
        // Redraw after resize
        this.draw();
    }

    handleKeyPress(key) {
        if (!gameState.running || gameState.paused) return;
        
        // Map keys A-C to mole indices 0-2 (only 3 moles now)
        const keyToIndex = {
            'a': 0, 'b': 1, 'c': 2
        };
        
        const moleIndex = keyToIndex[key.toLowerCase()];
        if (moleIndex !== undefined && this.moles[moleIndex]) {
            const mole = this.moles[moleIndex];
            if (mole.hit()) {
                // Visual feedback for successful hit
                console.log(`Hit ${mole.isGoodMole ? 'good' : 'bad'} mole! Score: ${gameState.score}`);
            }
        }
    }

    gameOver() {
        gameState.running = false;
        
        if (gameState.gameTimer) {
            clearInterval(gameState.gameTimer);
            gameState.gameTimer = null;
        }
        
        // Hide all moles
        this.moles.forEach(mole => {
            mole.isVisible = false;
            if (mole.visibilityTimer) {
                clearTimeout(mole.visibilityTimer);
                mole.visibilityTimer = null;
            }
        });
        
        console.log(`Game Over! Final Score: ${gameState.score} - Press Reset to play again`);
    }

    draw() {
        // Clear canvas using logical dimensions
        this.ctx.fillStyle = '#90EE90'; // Light green background
        this.ctx.fillRect(0, 0, this.logicalWidth, this.logicalHeight);
        
        // Draw background image if loaded
        if (!backgroundImages.loading && backgroundImages.background) {
            this.ctx.drawImage(backgroundImages.background, 0, 0, this.logicalWidth, this.logicalHeight);
        }
        
        // Hit effects removed - bash animation provides visual feedback
        
        // Draw visible moles (between background and overlay)
        this.moles.forEach(mole => mole.draw(this.ctx));
        
        // Draw bash animations on top of moles
        this.moles.forEach(mole => mole.drawBashAnimation(this.ctx));
        
        // Draw bottom overlay if loaded (covers bunnies when they're hidden)
        if (!backgroundImages.loading && backgroundImages.bottomOverlay) {
            this.ctx.drawImage(backgroundImages.bottomOverlay, 0, this.logicalHeight - backgroundImages.bottomOverlay.height, this.logicalWidth, backgroundImages.bottomOverlay.height);
        }
        
        // Draw score and time (scaled for high DPI)
        this.ctx.fillStyle = '#c3784f';
        this.ctx.font = '40px Magic Alphabet';
        
        // Score on the left
        this.ctx.textAlign = 'right';
        this.ctx.fillText(`Score: ${gameState.score}`, this.logicalWidth - 910, 82);
        
        // Time on the right
        if (gameState.running) {
            this.ctx.textAlign = 'left';
            this.ctx.fillText(`Time: ${gameState.timeLeft}s`, 910, 82);
            
            // Show difficulty level
            this.ctx.font = '30px Magic Alphabet';
            this.ctx.fillText(`Level: ${gameState.difficultyLevel + 1}`, 910, 120);
        }
    }


    gameLoop() {
        // Update mole animations
        this.moles.forEach(mole => mole.update());
        
        this.draw();
        
        if (gameState.running) {
            this.animationId = requestAnimationFrame(() => this.gameLoop());
        }
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Load mole images first
    loadImages();
    
    const canvas = document.getElementById('game-canvas');
    const game = new WhackAMoleGame(canvas);
    
    // Controls
    document.getElementById('start-btn').addEventListener('click', () => game.start());
    document.getElementById('pause-btn').addEventListener('click', () => game.pause());
    document.getElementById('reset-btn').addEventListener('click', () => game.reset());
    
    // Keyboard controls - A-C keys to hit moles
    document.addEventListener('keydown', (e) => {
        const key = e.key.toLowerCase();
        if (['a', 'b', 'c'].includes(key)) {
            game.handleKeyPress(key);
            e.preventDefault();
        }
    });
    
    // Initial draw
    game.draw();
    
    // Handle window resize
    window.addEventListener('resize', () => {
        game.resize();
    });
    
    // Call resize multiple times to ensure container is properly sized
    setTimeout(() => {
        game.resize();
    }, 100);
    
    setTimeout(() => {
        game.resize();
    }, 500);
    
    setTimeout(() => {
        game.resize();
    }, 1000);
});