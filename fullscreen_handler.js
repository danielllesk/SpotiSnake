// Fullscreen and canvas positioning handler for SpotiSnake
console.log('Fullscreen handler loaded');

// Handle window resize for fullscreen detection
function handleResize() {
    const canvas = document.querySelector('canvas.emscripten');
    if (!canvas) {
        console.log('Canvas not found, retrying...');
        setTimeout(handleResize, 100);
        return;
    }
    
    const isLargeWindow = window.innerWidth > 800 || window.innerHeight > 800;
    const isFullscreen = document.fullscreenElement || 
                       document.webkitFullscreenElement || 
                       document.mozFullScreenElement || 
                       document.msFullscreenElement;
    
    console.log('Window size:', window.innerWidth, 'x', window.innerHeight);
    console.log('Is large window:', isLargeWindow);
    console.log('Is fullscreen:', isFullscreen);
    
    if (isLargeWindow || isFullscreen) {
        console.log('Applying centered canvas styling');
        canvas.style.width = '600px';
        canvas.style.height = '600px';
        canvas.style.position = 'absolute';
        canvas.style.top = '50%';
        canvas.style.left = '50%';
        canvas.style.transform = 'translate(-50%, -50%)';
        canvas.style.margin = '0';
    } else {
        console.log('Applying full-window canvas styling');
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.transform = 'none';
        canvas.style.margin = '0';
    }
}

// Listen for window resize events
window.addEventListener('resize', handleResize);

// Listen for fullscreen changes
document.addEventListener('fullscreenchange', handleResize);
document.addEventListener('webkitfullscreenchange', handleResize);
document.addEventListener('mozfullscreenchange', handleResize);
document.addEventListener('MSFullscreenChange', handleResize);

// Call once on load
window.addEventListener('load', handleResize);

// Also call after a short delay to ensure canvas is ready
setTimeout(handleResize, 500);
setTimeout(handleResize, 1000);
setTimeout(handleResize, 2000);

console.log('Fullscreen handler setup complete');
