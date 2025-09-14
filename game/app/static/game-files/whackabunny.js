// Game state
let gameState = {
    running: false,
    paused: false,
    score: 0,
    timeLeft: 60, // 60 second game
    gameTimer: null,
    moles: [],
    difficultyLevel: 0, // 0-5 (6 levels over 60 seconds)
    gameEnded: false, // Track if game ended naturally (not reset)
    backgroundMusic: null, // Background music audio element
    redFlash: false, // Red flash effect for bad bunny hits
    redFlashOpacity: 0, // Current opacity of red flash (0-1)
    redFlashAnimation: null // Animation frame for red flash
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

const sceneryImages = {
    bunny1: null,
    bunny2: null,
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
    const sceneryBunny1Img = new Image();
    const sceneryBunny2Img = new Image();
    
    let loadedCount = 0;
    const totalImages = 8; // Loading 8 images now (good, bad, background, bottom overlay, bash frames, scenery)
    const checkAllLoaded = () => {
        loadedCount++;
        if (loadedCount === totalImages) {
            moleImages.loading = false;
            backgroundImages.loading = false;
            bashImages.loading = false;
            sceneryImages.loading = false;
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
    
    sceneryBunny1Img.onload = () => {
        sceneryImages.bunny1 = sceneryBunny1Img;
        checkAllLoaded();
    };
    
    sceneryBunny2Img.onload = () => {
        sceneryImages.bunny2 = sceneryBunny2Img;
        checkAllLoaded();
    };
    
    // Set image sources
    goodImg.src = '/static/images/good-mole.png';
    badImg.src = '/static/images/bad-mole.png';
    backgroundImg.src = '/static/images/holes_background.png';
    bottomOverlayImg.src = '/static/images/holes_bottom_overlay.png';
    bashFrame1Img.src = '/static/images/bash_animation_1.png';
    bashFrame2Img.src = '/static/images/bash_animation_2.png';
    sceneryBunny1Img.src = '/static/images/bunny1.gif';
    sceneryBunny2Img.src = '/static/images/bunny2.gif';
    
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
    
    sceneryBunny1Img.onerror = () => {
        console.warn('Scenery bunny1 image failed to load');
        checkAllLoaded();
    };
    
    sceneryBunny2Img.onerror = () => {
        console.warn('Scenery bunny2 image failed to load');
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
        
        // Don't show if already visible or animating
        if (this.isVisible || this.isAnimating) return;
        
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
        // Add extra time to ensure animation completes (minimum 500ms for animation)
        const baseShowDuration = Math.random() * (difficulty.maxShowTime - difficulty.minShowTime) + difficulty.minShowTime;
        const animationBuffer = 500; // Extra time to ensure animation completes
        const showDuration = Math.max(baseShowDuration, animationBuffer);
        
        this.visibilityTimer = setTimeout(() => {
            this.hide();
        }, showDuration);
    }

    hide() {
        // Don't hide if already hiding or not visible
        if (!this.isVisible) return;
        
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
            const baseHideDuration = Math.random() * (difficulty.maxHideTime - difficulty.minHideTime) + difficulty.minHideTime;
            const animationBuffer = 500; // Extra time to ensure hide animation completes
            const hideDuration = Math.max(baseHideDuration, animationBuffer);
            
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
                // Trigger red flash for bad bunny hits
                triggerRedFlash();
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
            const baseSize = this.radius * 1.5; // Slightly smaller than the bunny
            const offsetY = -this.radius * 0.5; // Position higher above the bunny
            
            try {
                // Calculate aspect ratio to prevent stretching
                const aspectRatio = image.width / image.height;
                let width, height;
                
                if (aspectRatio > 1) {
                    // Image is wider than tall
                    width = baseSize;
                    height = baseSize / aspectRatio;
                } else {
                    // Image is taller than wide
                    height = baseSize;
                    width = baseSize * aspectRatio;
                }
                
                // Center the image
                const x = this.x - width / 2;
                const y = this.y + offsetY - height / 2;
                
                // Draw the bash animation image above the mole with correct aspect ratio
                ctx.drawImage(image, x, y, width, height);
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

// Background music system
function initializeBackgroundMusic() {
    gameState.backgroundMusic = new Audio('/static/audio/germany-bavarian-oktoberfest-background-music-401731.mp3');
    gameState.backgroundMusic.loop = true;
    gameState.backgroundMusic.volume = 0.3; // Set a reasonable volume
    
    // Handle audio loading errors
    gameState.backgroundMusic.onerror = () => {
        console.warn('Background music failed to load');
        gameState.backgroundMusic = null;
    };
    
    console.log('Background music initialized');
}

// Scenery bunnies system (HTML elements for animated GIFs)
function initializeSceneryBunnies() {
    const gameContainer = document.querySelector('.game-container');
    if (!gameContainer) return;
    
    // Create bunny1 element
    const bunny1 = document.createElement('img');
    bunny1.src = '/static/images/bunny1.gif';
    bunny1.style.position = 'absolute';
    bunny1.style.width = '100px';
    bunny1.style.height = '100px';
    bunny1.style.pointerEvents = 'none';
    bunny1.style.zIndex = '10';
    bunny1.id = 'scenery-bunny1';
    
    // Create bunny2 element
    const bunny2 = document.createElement('img');
    bunny2.src = '/static/images/bunny2.gif';
    bunny2.style.position = 'absolute';
    bunny2.style.width = '100px';
    bunny2.style.height = '100px';
    bunny2.style.pointerEvents = 'none';
    bunny2.style.zIndex = '10';
    bunny2.id = 'scenery-bunny2';
    
    // Add to container
    gameContainer.appendChild(bunny1);
    gameContainer.appendChild(bunny2);
    
    // Position the bunnies
    updateSceneryBunniesPosition();
    
    console.log('Scenery bunnies initialized');
}

function updateSceneryBunniesPosition() {
    const bunny1 = document.getElementById('scenery-bunny1');
    const bunny2 = document.getElementById('scenery-bunny2');
    
    if (!bunny1 || !bunny2) return;
    
    const container = document.querySelector('.game-container');
    if (!container) return;
    
    const rect = container.getBoundingClientRect();
    const containerHeight = rect.height;
    const containerWidth = rect.width;
    
    // Position bunny1 on the right side
    bunny1.style.left = (containerWidth * 0.66) + 'px';
    bunny1.style.bottom = '50px';
    
    // Position bunny2 on the left side
    bunny2.style.left = (containerWidth * 0.25) + 'px';
    bunny2.style.bottom = '20px';
}

function updateMusicSpeed() {
    if (!gameState.backgroundMusic || !gameState.running) return;
    
    // Calculate speed based on elapsed time (0.6x to 1.8x over 60 seconds)
    const timeElapsed = 60 - gameState.timeLeft;
    const speed = 0.5 + (timeElapsed / 60) * 1; // 0.5 + (0 to 1.0) = 0.5 to 1.5
    
    // Update playback rate
    gameState.backgroundMusic.playbackRate = speed;
}

function triggerRedFlash() {
    gameState.redFlash = true;
    gameState.redFlashOpacity = 0;
    
    // Clear any existing animation
    if (gameState.redFlashAnimation) {
        cancelAnimationFrame(gameState.redFlashAnimation);
    }
    
    const startTime = Date.now();
    const fadeInDuration = 100; // 100ms fade in
    const fadeOutDuration = 700; // 300ms fade out
    const totalDuration = fadeInDuration + fadeOutDuration;
    
    function animateFlash() {
        const elapsed = Date.now() - startTime;
        
        if (elapsed < fadeInDuration) {
            // Fade in phase
            gameState.redFlashOpacity = (elapsed / fadeInDuration) * 0.5;
        } else if (elapsed < totalDuration) {
            // Fade out phase
            const fadeOutProgress = (elapsed - fadeInDuration) / fadeOutDuration;
            gameState.redFlashOpacity = 0.5 * (1 - fadeOutProgress);
        } else {
            // Animation complete
            gameState.redFlash = false;
            gameState.redFlashOpacity = 0;
            gameState.redFlashAnimation = null;
            return;
        }
        
        gameState.redFlashAnimation = requestAnimationFrame(animateFlash);
    }
    
    animateFlash();
}

// Difficulty progression system
function getDifficultySettings() {
    const timeElapsed = 60 - gameState.timeLeft;
    const difficultyLevel = Math.floor(timeElapsed / 10); // New level every 10 seconds
    
    // Update global difficulty level
    gameState.difficultyLevel = Math.min(difficultyLevel, 5); // Cap at level 5
    
    // Define difficulty settings for each level (0-5) - Faster animations
    const difficultySettings = [
        // Level 0 (0-9s): Very slow start
        { minShowTime: 1000, maxShowTime: 2750, minHideTime: 1750, maxHideTime: 4500, animationSpeed: 0.025 },
        // Level 1 (10-19s): Slow
        { minShowTime: 800, maxShowTime: 2500, minHideTime: 1500, maxHideTime: 4300, animationSpeed: 0.030 },
        // Level 2 (20-29s): Medium-slow
        { minShowTime: 650, maxShowTime: 2300, minHideTime: 1300, maxHideTime: 4000, animationSpeed: 0.035 },
        // Level 3 (30-39s): Medium
        { minShowTime: 550, maxShowTime: 2100, minHideTime: 1100, maxHideTime: 3700, animationSpeed: 0.040 },
        // Level 4 (40-49s): Fast
        { minShowTime: 450, maxShowTime: 1900, minHideTime: 900, maxHideTime: 3500, animationSpeed: 0.045 },
        // Level 5 (50-60s): Very fast
        { minShowTime: 350, maxShowTime: 1700, minHideTime: 700, maxHideTime: 3300, animationSpeed: 0.050 }
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
        // Prevent starting if game is already running and not paused
        if (gameState.running && !gameState.paused) {
            console.log('Game is already running!');
            return;
        }
        
        // If resuming from pause, don't reset music
        const isResuming = gameState.running && gameState.paused;
        
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
        gameState.gameEnded = false; // Clear the game ended flag
        gameState.redFlash = false; // Clear red flash effect
        gameState.redFlashOpacity = 0; // Reset flash opacity
        
        // Force difficulty level recalculation to ensure correct speeds
        getDifficultySettings();
        
        console.log('Game started - Use A-F keys - Green moles: +10 pts, Red moles: -20 pts!');
        
        // Start background music (only if not already playing)
        if (gameState.backgroundMusic) {
            if (!isResuming && gameState.backgroundMusic.paused) {
                // Only reset to beginning if this is a new game (not resuming from pause)
                gameState.backgroundMusic.currentTime = 0;
            }
            gameState.backgroundMusic.play().catch(e => {
                console.warn('Could not play background music:', e);
            });
            
            // Reset music speed to current difficulty level
            updateMusicSpeed();
        }
        
        // Start game timer
        gameState.gameTimer = setInterval(() => {
            if (!gameState.paused) {
                gameState.timeLeft--;
                
                // Update music speed based on elapsed time
                updateMusicSpeed();
                
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
        // If game is not running, start it
        if (!gameState.running) {
            this.start();
            return;
        }
        
        // Toggle pause state
        gameState.paused = !gameState.paused;
        
        // Pause/resume background music
        if (gameState.backgroundMusic) {
            if (gameState.paused) {
                gameState.backgroundMusic.pause();
            } else {
                // Resume music from current position (don't restart)
                gameState.backgroundMusic.play().catch(e => {
                    console.warn('Could not resume background music:', e);
                });
            }
        }
        
        console.log(gameState.paused ? 'Game paused' : 'Game resumed');
    }
    
    fadeOutMusic() {
        if (!gameState.backgroundMusic) return;
        
        const fadeDuration = 3000; // 2 seconds fade out
        const fadeSteps = 20; // Number of steps for smooth fade
        const stepDuration = fadeDuration / fadeSteps;
        const volumeStep = gameState.backgroundMusic.volume / fadeSteps;
        
        let currentStep = 0;
        
        const fadeInterval = setInterval(() => {
            currentStep++;
            gameState.backgroundMusic.volume = Math.max(0, gameState.backgroundMusic.volume - volumeStep);
            
            if (currentStep >= fadeSteps || gameState.backgroundMusic.volume <= 0) {
                gameState.backgroundMusic.pause();
                gameState.backgroundMusic.volume = 0.3; // Reset volume for next game
                clearInterval(fadeInterval);
            }
        }, stepDuration);
    }

    reset() {
        gameState.running = false;
        gameState.paused = false;
        gameState.score = 0;
        gameState.timeLeft = 60;
        gameState.gameEnded = false; // Clear the game ended flag
        
        // Stop background music
        if (gameState.backgroundMusic) {
            gameState.backgroundMusic.pause();
            gameState.backgroundMusic.currentTime = 0;
        }
        
        // Clear red flash effect
        if (gameState.redFlashAnimation) {
            cancelAnimationFrame(gameState.redFlashAnimation);
            gameState.redFlashAnimation = null;
        }
        gameState.redFlash = false;
        gameState.redFlashOpacity = 0;
        
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
            
            // Check if there's a bunny visible in this slot
            if (mole.isVisible && mole.animationProgress > 0) {
                // There's a bunny to hit
            if (mole.hit()) {
                // Visual feedback for successful hit
                console.log(`Hit ${mole.isGoodMole ? 'good' : 'bad'} mole! Score: ${gameState.score}`);
            }
            }
            // No penalty for hitting empty slots - removed -10 point condition
        }
    }

    gameOver() {
        gameState.running = false;
        gameState.gameEnded = true; // Mark that game ended naturally
        
        // Fade out background music
        if (gameState.backgroundMusic) {
            this.fadeOutMusic();
        }
        
        if (gameState.gameTimer) {
            clearInterval(gameState.gameTimer);
            gameState.gameTimer = null;
        }
        
        // Hide all moles and clear their timers
        this.moles.forEach(mole => {
            mole.isVisible = false;
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
        
        console.log(`Game Over! Final Score: ${gameState.score} - Press Reset to play again`);
        
        // Draw the end screen
        this.drawEndScreen();
    }
    
    drawEndScreen() {
        // Draw background with fixed size anchored at bottom (same as normal game)
        if (!backgroundImages.loading && backgroundImages.background) {
            const backgroundHeight = 720; // Fixed height for background image
            const backgroundY = this.logicalHeight - backgroundHeight; // Anchor at bottom
            
            // Fill top area with solid color if screen is taller than background
            if (backgroundY > 0) {
                this.ctx.fillStyle = '#c5f1a4';
                this.ctx.fillRect(0, 0, this.logicalWidth, backgroundY);
            }
            
            // Draw background image at bottom with full width
            this.ctx.drawImage(backgroundImages.background, 0, backgroundY, this.logicalWidth, backgroundHeight);
        } else {
            // Fallback: fill entire screen with background color
            this.ctx.fillStyle = '#c5f1a4';
            this.ctx.fillRect(0, 0, this.logicalWidth, this.logicalHeight);
        }
        
        // Draw bottom overlay if loaded
        if (!backgroundImages.loading && backgroundImages.bottomOverlay) {
            const backgroundHeight = 720; // Same as background image
            const backgroundY = this.logicalHeight - backgroundHeight;
            const overlayHeight = backgroundImages.bottomOverlay.height;
            const overlayY = backgroundY + backgroundHeight - overlayHeight; // Position at bottom of background
            
            this.ctx.drawImage(backgroundImages.bottomOverlay, 0, overlayY, this.logicalWidth, overlayHeight);
        }
        
        // Note: Animated GIFs are handled by HTML elements, not canvas drawing
        
        // Draw final score in center of screen
        this.ctx.fillStyle = '#c3784f';
        this.ctx.font = '50px Magic Alphabet';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(`Final Score: ${gameState.score}`, this.logicalWidth / 2, 185);
        
        // Draw reset instruction below score
        this.ctx.font = '30px Magic Alphabet';
        this.ctx.fillText('Press Reset to play again', this.logicalWidth / 2, 225);
    }

    draw() {
        // If game ended naturally (not reset), draw end screen instead of normal game
        if (!gameState.running && gameState.gameEnded) {
            this.drawEndScreen();
            return;
        }
        
        // Draw background with fixed size anchored at bottom (drawn first as the very back)
        if (!backgroundImages.loading && backgroundImages.background) {
            const backgroundHeight = 720; // Fixed height for background image
            const backgroundY = this.logicalHeight - backgroundHeight; // Anchor at bottom
            
            // Fill top area with solid color if screen is taller than background
            if (backgroundY > 0) {
                this.ctx.fillStyle = '#c5f1a4';
                this.ctx.fillRect(0, 0, this.logicalWidth, backgroundY);
            }
            
            // Draw background image at bottom with full width
            this.ctx.drawImage(backgroundImages.background, 0, backgroundY, this.logicalWidth, backgroundHeight);
        } else {
            // Fallback: fill entire screen with background color
            this.ctx.fillStyle = '#c5f1a4';
            this.ctx.fillRect(0, 0, this.logicalWidth, this.logicalHeight);
        }
        
        // Hit effects removed - bash animation provides visual feedback
        
        // Draw visible moles (between background and overlay)
        this.moles.forEach(mole => mole.draw(this.ctx));
        
        // Draw bash animations on top of moles
        this.moles.forEach(mole => mole.drawBashAnimation(this.ctx));
        
        // Draw bottom overlay if loaded (covers bunnies when they're hidden)
        if (!backgroundImages.loading && backgroundImages.bottomOverlay) {
            const backgroundHeight = 720; // Same as background image
            const backgroundY = this.logicalHeight - backgroundHeight;
            const overlayHeight = backgroundImages.bottomOverlay.height;
            const overlayY = backgroundY + backgroundHeight - overlayHeight; // Position at bottom of background
            
            this.ctx.drawImage(backgroundImages.bottomOverlay, 0, overlayY, this.logicalWidth, overlayHeight);
        }
        
        // Note: Animated GIFs are handled by HTML elements, not canvas drawing
        
        // Draw red flash effect on top of everything if active
        if (gameState.redFlash && gameState.redFlashOpacity > 0) {
            this.ctx.fillStyle = `rgba(255, 0, 0, ${gameState.redFlashOpacity})`;
            this.ctx.fillRect(0, 0, this.logicalWidth, this.logicalHeight);
        }
        
        // Draw score and time (scaled for high DPI)
        this.ctx.fillStyle = '#c3784f';
        this.ctx.font = '40px Magic Alphabet';
        
        // Score on the left
        this.ctx.textAlign = 'right';
        this.ctx.fillText(`Score: ${gameState.score}`, this.logicalWidth*0.5 - 190, 82);
        
        // Time on the right
            this.ctx.textAlign = 'left';
        this.ctx.fillText(`Time: ${gameState.timeLeft}s`, this.logicalWidth*0.5 + 190, 82);
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
    
    // Initialize background music
    initializeBackgroundMusic();
    
    // Initialize scenery bunnies
    initializeSceneryBunnies();
    
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
        updateSceneryBunniesPosition();
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