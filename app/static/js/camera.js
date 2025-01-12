// Camera state management
let currentStream = null;

async function initCamera() {
    try {
        console.log('Initializing camera...');
        
        // First check if we have camera permissions
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        
        if (videoDevices.length === 0) {
            throw new Error('No camera devices found');
        }
        
        console.log('Found video devices:', videoDevices);
        
        // Stop any existing stream
        if (currentStream) {
            currentStream.getTracks().forEach(track => track.stop());
        }

        // Request camera access with fallback options
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { min: 640, ideal: 1280, max: 1920 },
                height: { min: 480, ideal: 720, max: 1080 },
                facingMode: "user",
                frameRate: { min: 15, ideal: 30 }
            },
            audio: false
        }).catch(async (err) => {
            console.log('Failed with high quality settings, trying basic settings:', err);
            // Fallback to basic settings if high quality fails
            return await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: false
            });
        });

        console.log('Got media stream:', stream);
        currentStream = stream;
        
        const video = document.getElementById('video');
        console.log('Video element:', video);
        
        if (video) {
            video.srcObject = stream;
            
            // Wait for video to be ready
            await new Promise((resolve) => {
                video.onloadedmetadata = () => {
                    console.log('Video metadata loaded');
                    video.play()
                        .then(() => {
                            console.log('Video playback started');
                            resolve();
                        })
                        .catch((err) => {
                            console.error('Video playback failed:', err);
                            handleCameraError(err);
                        });
                };
            });
            
            showToast('Camera initialized successfully', 'success');
        } else {
            throw new Error('Video element not found');
        }
    } catch (err) {
        console.error('Camera initialization error:', err);
        handleCameraError(err);
    }
}

function handleCameraError(error) {
    console.error('Camera Error Details:', error);
    
    let message = 'Could not access camera. ';
    
    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        message += 'Please grant camera permissions in your browser settings.';
    } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        message += 'No camera device found. Please connect a camera and try again.';
    } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        message += 'Camera is in use by another application. Please close other apps using the camera.';
    } else if (error.name === 'OverconstrainedError') {
        message += 'Camera does not support the required settings. Trying with basic settings...';
        // Retry with basic settings
        setTimeout(() => {
            navigator.mediaDevices.getUserMedia({ video: true, audio: false })
                .then(stream => {
                    currentStream = stream;
                    const video = document.getElementById('video');
                    if (video) {
                        video.srcObject = stream;
                        video.play()
                            .then(() => console.log('Video playback started (fallback)'))
                            .catch(err => console.error('Video playback failed (fallback):', err));
                    }
                })
                .catch(err => {
                    console.error('Camera fallback failed:', err);
                    handleCameraError(err);
                });
        }, 1000);
        return;
    } else {
        message += error.message || 'Please check your camera connection and permissions.';
    }

    // Show error in UI
    const container = document.querySelector('.camera-container');
    if (container) {
        const errorAlert = document.createElement('div');
        errorAlert.className = 'alert alert-error shadow-lg animate__animated animate__fadeIn';
        errorAlert.innerHTML = `
            <div class="flex items-center gap-2">
                <i class="ri-error-warning-line text-xl"></i>
                <span>${message}</span>
            </div>
            <button onclick="retryCamera()" class="btn btn-sm btn-ghost">
                <i class="ri-refresh-line mr-1"></i> Retry
            </button>
        `;
        container.appendChild(errorAlert);
    }
}

function stopCamera() {
    console.log('Stopping camera...');
    if (currentStream) {
        currentStream.getTracks().forEach(track => {
            console.log('Stopping track:', track);
            track.stop();
        });
        currentStream = null;
        
        const video = document.getElementById('video');
        if (video) {
            video.srcObject = null;
            console.log('Cleared video source');
        }
    }
}

async function retryCamera() {
    console.log('Retrying camera initialization...');
    const container = document.querySelector('.camera-container');
    if (container) {
        container.querySelectorAll('.alert').forEach(alert => alert.remove());
    }
    await initCamera();
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    console.log('Setting up camera event listeners...');
    const cameraModal = document.querySelector('.camera-modal');
    const cameraButtons = document.querySelectorAll('[data-action="open-camera"]');
    
    console.log('Found camera buttons:', cameraButtons.length);
    
    if (cameraModal && cameraButtons.length > 0) {
        cameraButtons.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                console.log('Camera button clicked');
                e.preventDefault();
                cameraModal.classList.add('active');
                await initCamera();
            });
        });
        
        // Close button and backdrop click
        cameraModal.addEventListener('click', (e) => {
            if (e.target === cameraModal || e.target.closest('[data-action="close-camera"]')) {
                console.log('Closing camera modal');
                cameraModal.classList.remove('active');
                stopCamera();
            }
        });
    } else {
        console.log('Camera modal or buttons not found:', {
            modal: cameraModal,
            buttons: cameraButtons
        });
    }
}); 