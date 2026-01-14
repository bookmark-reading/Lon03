# Audio WebSocket Client

A Node.js web application that provides a browser interface for recording audio and sending it to a WebSocket server.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

Or for development with auto-reload:
```bash
npm run dev
```

3. Open your browser and navigate to `http://localhost:3000`

## Features

- **WebSocket Connection**: Connects to the audio server at `ws://localhost:8765`
- **Audio Recording**: Records audio from user's microphone
- **Real-time Visualization**: Shows audio frequency visualization while recording
- **Base64 Encoding**: Converts audio to base64 format before sending
- **Live Status**: Shows connection and microphone status
- **Activity Log**: Displays all connection and recording activities
- **Chunked Sending**: Sends audio data in 1-second chunks for real-time processing

## Usage

1. **Connect to Server**: Click "Connect to Server" to establish WebSocket connection
2. **Start Recording**: Click "Start Recording" to begin audio capture (browser will ask for microphone permission)
3. **Monitor Activity**: Watch the visualizer and activity log for real-time feedback
4. **Stop Recording**: Click "Stop Recording" to end audio capture
5. **Disconnect**: Click "Disconnect" to close the WebSocket connection

## Browser Requirements

- Modern browser with WebRTC support (Chrome, Firefox, Safari, Edge)
- Microphone access permission
- WebSocket support

## Audio Format

- **Input**: Microphone audio (WebM with Opus codec)
- **Output**: Base64 encoded audio chunks sent via WebSocket
- **Frequency**: 1-second chunks for real-time streaming

## Server Integration

This client is designed to work with the Python WebSocket server in the `../server` directory. Make sure the server is running on `localhost:8765` before connecting.