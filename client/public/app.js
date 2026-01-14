class AudioWebSocketClient {
    constructor() {
        this.ws = null;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.audioContext = null;
        this.analyser = null;
        this.isRecording = false;
        this.recordingStartTime = null;
        this.dataSentCount = 0;
        
        this.initializeElements();
        this.setupEventListeners();
        this.setupVisualizer();
    }

    initializeElements() {
        this.elements = {
            connectBtn: document.getElementById('connect-btn'),
            recordBtn: document.getElementById('record-btn'),
            stopBtn: document.getElementById('stop-btn'),
            wsStatus: document.getElementById('ws-status'),
            micStatus: document.getElementById('mic-status'),
            duration: document.getElementById('duration'),
            dataSent: document.getElementById('data-sent'),
            log: document.getElementById('log'),
            visualizer: document.getElementById('visualizer'),
            partialText: document.getElementById('partial-text'),
            finalText: document.getElementById('final-text'),
            helpSection: document.getElementById('help-section'),
            helpMessage: document.getElementById('help-message')
        };
        
        this.canvas = this.elements.visualizer;
        this.canvasCtx = this.canvas.getContext('2d');
    }

    setupEventListeners() {
        this.elements.connectBtn.addEventListener('click', () => this.toggleConnection());
        this.elements.recordBtn.addEventListener('click', () => this.startRecording());
        this.elements.stopBtn.addEventListener('click', () => this.stopRecording());
    }

    setupVisualizer() {
        this.canvasCtx.fillStyle = '#f8f9fa';
        this.canvasCtx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    log(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.textContent = `[${timestamp}] ${message}`;
        
        this.elements.log.appendChild(logEntry);
        this.elements.log.scrollTop = this.elements.log.scrollHeight;
    }

    updateStatus(element, text, className) {
        element.textContent = text;
        element.className = `status ${className}`;
    }

    toggleConnection() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.disconnect();
        } else {
            this.connect();
        }
    }

    connect() {
        try {
            this.ws = new WebSocket('ws://localhost:8765');
            
            this.ws.onopen = () => {
                this.log('Connected to WebSocket server', 'success');
                this.updateStatus(this.elements.wsStatus, 'Connected', 'connected');
                this.elements.connectBtn.textContent = 'Disconnect';
                this.elements.recordBtn.disabled = false;
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleServerMessage(message);
                } catch (error) {
                    console.error('Error parsing server message:', error);
                }
            };

            this.ws.onclose = () => {
                this.log('Disconnected from WebSocket server', 'warning');
                this.updateStatus(this.elements.wsStatus, 'Disconnected', 'disconnected');
                this.elements.connectBtn.textContent = 'Connect to Server';
                this.elements.recordBtn.disabled = true;
                this.elements.stopBtn.disabled = true;
            };

            this.ws.onerror = (error) => {
                this.log('WebSocket error occurred', 'error');
                console.error('WebSocket error:', error);
            };

        } catch (error) {
            this.log('Failed to connect to server', 'error');
            console.error('Connection error:', error);
        }
    }

    handleServerMessage(message) {
        if (message.type === 'transcription') {
            this.displayTranscription(message);
        } else if (message.type === 'help_needed') {
            this.displayHelpMessage(message);
        }
    }

    displayTranscription(transcription) {
        const timestamp = new Date(transcription.timestamp).toLocaleTimeString();
        
        if (transcription.is_partial) {
            // Update partial transcription display
            this.elements.partialText.textContent = `Partial: ${transcription.text}`;
        } else {
            // Add final transcription to the display
            const entry = document.createElement('div');
            entry.className = 'transcription-entry';
            
            const confidenceText = transcription.confidence !== 'N/A' 
                ? `${Math.round(transcription.confidence * 100)}%` 
                : 'N/A';
            
            entry.innerHTML = `
                <span class="timestamp">${timestamp}</span>
                <span class="confidence">Confidence: ${confidenceText}</span>
                <div>${transcription.text}</div>
            `;
            
            this.elements.finalText.appendChild(entry);
            
            // Clear partial text
            this.elements.partialText.textContent = '';
            
            // Auto-scroll to bottom
            this.elements.finalText.scrollTop = this.elements.finalText.scrollHeight;
            
            // Log the transcription
            this.log(`Transcribed: "${transcription.text}" (${confidenceText})`, 'success');
        }
    }

    disconnect() {
        if (this.isRecording) {
            this.stopRecording();
        }
        
        if (this.ws) {
            this.ws.close();
        }
    }

    async startRecording() {
        try {
            this.audioStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000  // Request 16kHz for Transcribe compatibility
                } 
            });

            this.setupAudioContext();
            this.setupMediaRecorder();  // This now sets up raw PCM capture
            
            // Clear previous transcriptions
            this.clearTranscriptions();
            
            this.isRecording = true;
            this.recordingStartTime = Date.now();
            this.dataSentCount = 0;
            
            this.log('Started recording raw PCM audio', 'success');
            this.updateStatus(this.elements.micStatus, 'Recording', 'active');
            this.elements.recordBtn.disabled = true;
            this.elements.stopBtn.disabled = false;
            
            this.startDurationTimer();
            this.startVisualizer();
            
        } catch (error) {
            this.log('Failed to access microphone', 'error');
            console.error('Microphone access error:', error);
        }
    }

    setupAudioContext() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        const source = this.audioContext.createMediaStreamSource(this.audioStream);
        source.connect(this.analyser);
        
        this.analyser.fftSize = 256;
        this.bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(this.bufferLength);
    }

    setupMediaRecorder() {
        // For better Transcribe compatibility, let's capture raw audio data
        // instead of using MediaRecorder which creates WebM containers
        console.log('Setting up raw audio capture for better Transcribe compatibility');
        
        // We'll use AudioWorklet or ScriptProcessor to get raw PCM data
        this.setupRawAudioCapture();
    }

    setupRawAudioCapture() {
        // Create audio context for raw audio processing
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000  // Use 16kHz for Transcribe compatibility
        });
        
        const source = this.audioContext.createMediaStreamSource(this.audioStream);
        
        // Use ScriptProcessor for raw audio data (deprecated but widely supported)
        const bufferSize = 4096;
        this.scriptProcessor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);
        
        this.scriptProcessor.onaudioprocess = (event) => {
            if (this.isRecording && this.ws && this.ws.readyState === WebSocket.OPEN) {
                const inputBuffer = event.inputBuffer;
                const inputData = inputBuffer.getChannelData(0); // Get mono channel
                
                // Convert float32 to int16 PCM
                const pcmData = this.float32ToInt16(inputData);
                const base64Data = this.arrayBufferToBase64(pcmData.buffer);
                
                const message = {
                    type: 'audio',
                    data: base64Data,
                    timestamp: Date.now(),
                    size: pcmData.buffer.byteLength,
                    mimeType: 'audio/pcm',
                    sampleRate: 16000,
                    channels: 1,
                    bitsPerSample: 16
                };

                this.ws.send(JSON.stringify(message));
                this.dataSentCount++;
                this.elements.dataSent.textContent = this.dataSentCount;
                
                this.log(`Sent PCM audio chunk (${pcmData.buffer.byteLength} bytes)`, 'info');
            }
        };
        
        // Connect the audio processing chain
        source.connect(this.scriptProcessor);
        this.scriptProcessor.connect(this.audioContext.destination);
        
        console.log('Raw PCM audio capture setup complete');
    }

    float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            // Convert float32 (-1 to 1) to int16 (-32768 to 32767)
            const sample = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }
        return int16Array;
    }

    async sendAudioData(audioBlob) {
        try {
            const arrayBuffer = await audioBlob.arrayBuffer();
            const base64Data = this.arrayBufferToBase64(arrayBuffer);
            
            const message = {
                type: 'audio',
                data: base64Data,
                timestamp: Date.now(),
                size: arrayBuffer.byteLength,
                mimeType: audioBlob.type  // Include the actual MIME type
            };

            this.ws.send(JSON.stringify(message));
            this.dataSentCount++;
            this.elements.dataSent.textContent = this.dataSentCount;
            
            this.log(`Sent audio chunk (${arrayBuffer.byteLength} bytes, ${audioBlob.type})`, 'info');
            
        } catch (error) {
            this.log('Failed to send audio data', 'error');
            console.error('Send error:', error);
        }
    }

    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    stopRecording() {
        if (this.isRecording) {
            this.isRecording = false;
            
            // Stop the script processor
            if (this.scriptProcessor) {
                this.scriptProcessor.disconnect();
                this.scriptProcessor = null;
            }
        }
        
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
        }
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
        
        this.log('Stopped recording audio', 'warning');
        this.updateStatus(this.elements.micStatus, 'Inactive', 'inactive');
        this.elements.recordBtn.disabled = false;
        this.elements.stopBtn.disabled = true;
        
        this.stopVisualizer();
    }

    startDurationTimer() {
        this.durationTimer = setInterval(() => {
            if (this.isRecording && this.recordingStartTime) {
                const duration = Math.floor((Date.now() - this.recordingStartTime) / 1000);
                this.elements.duration.textContent = `${duration}s`;
            }
        }, 1000);
    }

    startVisualizer() {
        const draw = () => {
            if (!this.isRecording) return;
            
            requestAnimationFrame(draw);
            
            this.analyser.getByteFrequencyData(this.dataArray);
            
            this.canvasCtx.fillStyle = '#f8f9fa';
            this.canvasCtx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            
            const barWidth = (this.canvas.width / this.bufferLength) * 2.5;
            let barHeight;
            let x = 0;
            
            for (let i = 0; i < this.bufferLength; i++) {
                barHeight = (this.dataArray[i] / 255) * this.canvas.height;
                
                const r = barHeight + 25 * (i / this.bufferLength);
                const g = 250 * (i / this.bufferLength);
                const b = 50;
                
                this.canvasCtx.fillStyle = `rgb(${r},${g},${b})`;
                this.canvasCtx.fillRect(x, this.canvas.height - barHeight, barWidth, barHeight);
                
                x += barWidth + 1;
            }
        };
        
        draw();
    }

    displayHelpMessage(helpData) {
        if (helpData.needs_help && helpData.help_message) {
            // Show help section
            this.elements.helpSection.style.display = 'block';
            
            // Display help message with audio indicator
            this.elements.helpMessage.innerHTML = `
                <div class="help-icon">💡</div>
                <div class="help-text">${helpData.help_message}</div>
                <div class="help-reason">Reason: ${helpData.reason}</div>
                ${helpData.audio ? '<div class="audio-indicator">🔊 Playing audio...</div>' : ''}
            `;
            
            // Play audio if available
            if (helpData.audio) {
                this.playHelpAudio(helpData.audio);
            }
            
            // Log the help event
            this.log(`Reading Assistant: Help offered (confidence: ${Math.round(helpData.confidence * 100)}%)`, 'warning');
            
            // Auto-hide after 15 seconds
            setTimeout(() => {
                this.elements.helpSection.style.display = 'none';
            }, 15000);
        }
    }

    playHelpAudio(audioBase64) {
        try {
            // Convert base64 to blob
            const audioData = atob(audioBase64);
            const arrayBuffer = new ArrayBuffer(audioData.length);
            const uint8Array = new Uint8Array(arrayBuffer);
            
            for (let i = 0; i < audioData.length; i++) {
                uint8Array[i] = audioData.charCodeAt(i);
            }
            
            const blob = new Blob([uint8Array], { type: 'audio/mp3' });
            const audioUrl = URL.createObjectURL(blob);
            
            // Create and play audio element
            const audio = new Audio(audioUrl);
            audio.volume = 0.8;  // Set volume to 80%
            
            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);  // Clean up
                this.log('Help audio playback completed', 'info');
            };
            
            audio.onerror = (error) => {
                console.error('Error playing help audio:', error);
                this.log('Error playing help audio', 'error');
            };
            
            audio.play().then(() => {
                this.log('Playing help audio message', 'success');
            }).catch(error => {
                console.error('Error starting audio playback:', error);
                this.log('Could not play help audio (browser may require user interaction)', 'warning');
            });
            
        } catch (error) {
            console.error('Error processing help audio:', error);
            this.log('Error processing help audio', 'error');
        }
    }

    clearTranscriptions() {
        this.elements.partialText.textContent = '';
        this.elements.finalText.innerHTML = '';
        this.elements.helpSection.style.display = 'none';
        this.elements.helpMessage.innerHTML = '';
    }

    stopVisualizer() {
        if (this.durationTimer) {
            clearInterval(this.durationTimer);
        }
        
        this.canvasCtx.fillStyle = '#f8f9fa';
        this.canvasCtx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.elements.duration.textContent = '0s';
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new AudioWebSocketClient();
});