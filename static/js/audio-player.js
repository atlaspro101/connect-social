// Custom Audio Player
class AudioPlayer {
    constructor(container) {
        this.container = container;
        this.audio = container.querySelector('audio');
        this.init();
    }
    
    init() {
        // Create custom controls
        const controls = document.createElement('div');
        controls.className = 'custom-audio-player';
        controls.innerHTML = `
            <button class="play-pause-btn">
                <svg viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                </svg>
            </button>
            <div class="progress-bar-container">
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <span class="time-display">0:00</span>
            </div>
            <div class="volume-control">
                <button class="volume-btn">
                    <svg viewBox="0 0 24 24">
                        <path d="M3 9v6h4l5 5V4L7 9H3z"/>
                        <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
                    </svg>
                </button>
                <div class="volume-slider">
                    <div class="volume-fill"></div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = '';
        this.container.appendChild(this.audio);
        this.container.appendChild(controls);
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        const playBtn = this.container.querySelector('.play-pause-btn');
        const progressBar = this.container.querySelector('.progress-bar');
        const volumeSlider = this.container.querySelector('.volume-slider');
        const volumeBtn = this.container.querySelector('.volume-btn');
        
        playBtn.addEventListener('click', () => this.togglePlay());
        progressBar.addEventListener('click', (e) => this.seek(e));
        volumeSlider.addEventListener('click', (e) => this.setVolume(e));
        volumeBtn.addEventListener('click', () => this.toggleMute());
        
        this.audio.addEventListener('timeupdate', () => this.updateProgress());
        this.audio.addEventListener('ended', () => this.onEnded());
    }
    
    togglePlay() {
        if (this.audio.paused) {
            this.audio.play();
            this.updatePlayButton(true);
        } else {
            this.audio.pause();
            this.updatePlayButton(false);
        }
    }
    
    updatePlayButton(isPlaying) {
        const btn = this.container.querySelector('.play-pause-btn');
        if (isPlaying) {
            btn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`;
        } else {
            btn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>`;
        }
    }
    
    updateProgress() {
        const progress = (this.audio.currentTime / this.audio.duration) * 100;
        const fill = this.container.querySelector('.progress-fill');
        fill.style.width = `${progress}%`;
        
        const timeDisplay = this.container.querySelector('.time-display');
        timeDisplay.textContent = this.formatTime(this.audio.currentTime);
    }
    
    seek(e) {
        const rect = e.currentTarget.getBoundingClientRect();
        const percent = (e.clientX - rect.left) / rect.width;
        this.audio.currentTime = percent * this.audio.duration;
    }
    
    setVolume(e) {
        const rect = e.currentTarget.getBoundingClientRect();
        const percent = (e.clientX - rect.left) / rect.width;
        this.audio.volume = Math.min(1, Math.max(0, percent));
        const fill = this.container.querySelector('.volume-fill');
        fill.style.width = `${percent * 100}%`;
    }
    
    toggleMute() {
        this.audio.muted = !this.audio.muted;
        const volumeBtn = this.container.querySelector('.volume-btn');
        if (this.audio.muted) {
            volumeBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>`;
        } else {
            volumeBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3z"/><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>`;
        }
    }
    
    onEnded() {
        this.updatePlayButton(false);
        this.audio.currentTime = 0;
    }
    
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

// Initialize all audio players
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.audio-player-container').forEach(container => {
        new AudioPlayer(container);
    });
});