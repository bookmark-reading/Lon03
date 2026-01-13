import React from 'react';
import { Button, Icon } from '@cloudscape-design/components';
import './SessionPlayer.css';

class SessionPlayer extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            sessionTime: 0,
            isRunning: false
        };
        this.timerInterval = null;
    }

    componentDidMount() {
        if (this.props.sessionStarted) {
            this.startTimer();
        }
    }

    componentDidUpdate(prevProps) {
        if (this.props.sessionStarted !== prevProps.sessionStarted) {
            if (this.props.sessionStarted) {
                this.startTimer();
            } else {
                this.stopTimer();
            }
        }
    }

    componentWillUnmount() {
        this.stopTimer();
    }

    startTimer = () => {
        this.setState({ isRunning: true });
        this.timerInterval = setInterval(() => {
            this.setState(prev => ({ sessionTime: prev.sessionTime + 1 }));
        }, 1000);
    }

    stopTimer = () => {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        this.setState({ isRunning: false, sessionTime: 0 });
    }

    formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    formatCost = (tokens) => {
        // Rough estimate: $0.003 per 1K tokens (adjust based on your pricing)
        const cost = (tokens / 1000) * 0.003;
        return `$${cost.toFixed(4)}`;
    }

    render() {
        const { sessionStarted, onSessionToggle, tokens = 0 } = this.props;
        const { sessionTime } = this.state;

        return (
            <div className="session-player">
                <div className="player-container">
                    {/* Left section - Session info */}
                    <div className="player-left">
                        <div className="session-icon">
                            {sessionStarted ? '🎙️' : '📚'}
                        </div>
                        <div className="session-info">
                            <div className="session-title">
                                {sessionStarted ? 'Reading Session Active' : 'Ready to Read'}
                            </div>
                            <div className="session-subtitle">
                                {this.props.bookName || 'Select a book to begin'}
                            </div>
                        </div>
                    </div>

                    {/* Center section - Controls */}
                    <div className="player-center">
                        <div className="player-controls">
                            <Button
                                variant="primary"
                                className="play-button"
                                onClick={onSessionToggle}
                            >
                                <Icon 
                                    name={sessionStarted ? "microphone-off" : "microphone"} 
                                />
                                &nbsp;&nbsp;
                                {sessionStarted ? 'End Session' : 'Start Session'}
                            </Button>
                        </div>
                        <div className="progress-bar">
                            <div 
                                className="progress-fill" 
                                style={{ 
                                    width: sessionStarted ? '100%' : '0%',
                                    transition: 'width 0.3s ease'
                                }}
                            />
                        </div>
                    </div>

                    {/* Right section - Metrics */}
                    <div 
                        className="player-right" 
                        onClick={this.props.onMetricsClick}
                        title="Click for detailed metrics"
                    >
                        <Icon name="status-in-progress" className="metrics-icon" />
                        <span className="metrics-text">
                            {this.formatTime(sessionTime)} • {tokens.toLocaleString()} • {this.formatCost(tokens)}
                        </span>
                        <Icon name="angle-right" className="metrics-arrow" />
                    </div>
                </div>
            </div>
        );
    }
}

export default SessionPlayer;
