import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "react-router-dom";
import { 
  MessageSquare, 
  ChevronLeft, 
  ChevronRight, 
  Settings, 
  X,
  Send,
  Users,
  Minus,
  Plus,
  Loader2,
  Mic,
  MicOff,
  Play,
  Square
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Slider } from "@/components/ui/slider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { fetchBook } from "@/services/bookService";
import { Book, ChatMessage, UserPreferences, UserProfile, ReadingProgress } from "@/types";

const defaultPreferences: UserPreferences = {
  fontSize: 16,
  lineSpacing: 1.6,
  theme: "dark",
  readingLevel: "beginner",
};

// PDF Viewer Component
const PDFViewer = ({ pdfUrl, className }: { pdfUrl: string; className?: string }) => {
  return (
    <div className={`w-full h-full ${className}`}>
      <iframe
        src={pdfUrl}
        className="w-full h-full border-0"
        title="PDF Viewer"
        style={{ minHeight: '600px' }}
      />
    </div>
  );
};

const defaultProfile: UserProfile = {
  id: "user-1",
  name: "Reader",
  avatarUrl: "",
  bio: "",
};

const initialMessages: ChatMessage[] = [];

const Reading = () => {
  const [searchParams] = useSearchParams();
  const bookId = searchParams.get("book") || "1";
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  
  const [currentChapterIndex, setCurrentChapterIndex] = useState(0);
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [preferences] = useLocalStorage<UserPreferences>("user-preferences", defaultPreferences);
  const [profile] = useLocalStorage<UserProfile>("user-profile", defaultProfile);
  const [, setReadingHistory] = useLocalStorage<ReadingProgress[]>("reading-history", []);
  const [localFontSize, setLocalFontSize] = useState(preferences.fontSize);
  const [onlineUsers] = useState(12);
  
  // WebSocket and audio states
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [wsStatus, setWsStatus] = useState<'disconnected' | 'connected'>('disconnected');
  const [isRecording, setIsRecording] = useState(false);
  const [activityLog, setActivityLog] = useState<string[]>([]);
  
  const chatEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<{
    audioContext: AudioContext;
    processor: ScriptProcessorNode;
    source: MediaStreamAudioSourceNode;
  } | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);

  const addToLog = (message: string, type: 'info' | 'success' | 'error' = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setActivityLog(prev => [...prev, `[${timestamp}] ${message}`]);
  };

  // WebSocket connection
  useEffect(() => {
    let websocket: WebSocket | null = null;
    
    const connectWebSocket = () => {
      try {
        addToLog('🔄 Attempting to connect to WebSocket server on port 8765...');
        websocket = new WebSocket('ws://localhost:8765');
        
        websocket.onopen = () => {
          setWsStatus('connected');
          addToLog('✅ Connected to WebSocket server on port 8765', 'success');
          
          const testMessage = {
            type: 'connection_test',
            message: 'Client connected successfully',
            timestamp: Date.now()
          };
          websocket?.send(JSON.stringify(testMessage));
          addToLog('📤 Sent connection test message', 'info');
        };
        
        websocket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            addToLog(`📥 Received message: ${message.type}`, 'info');
            
            if (message.type === 'transcription') {
              const transcriptionMessage: ChatMessage = {
                id: `${Date.now()}-${Math.random()}`,
                userId: 'transcription',
                userName: message.is_partial ? 'Listening...' : 'Transcription',
                avatarUrl: '',
                content: message.text,
                timestamp: new Date().toISOString(),
              };
              
              if (message.is_partial) {
                // Update or add partial transcription
                setMessages(prev => {
                  const filtered = prev.filter(m => !(m.userId === 'transcription' && m.userName === 'Listening...'));
                  return [...filtered, transcriptionMessage];
                });
              } else {
                // Add final transcription as new message
                setMessages(prev => {
                  const filtered = prev.filter(m => !(m.userId === 'transcription' && m.userName === 'Listening...'));
                  return [...filtered, transcriptionMessage];
                });
                addToLog(`Transcribed: "${message.text}"`, 'success');
              }
            }
          } catch (error) {
            addToLog('❌ Error parsing WebSocket message', 'error');
          }
        };
        
        websocket.onclose = (event) => {
          setWsStatus('disconnected');
          addToLog(`❌ Disconnected from WebSocket server (Code: ${event.code})`, 'error');
        };
        
        websocket.onerror = (error) => {
          addToLog('❌ WebSocket connection error - Check if server is running on port 8765', 'error');
          console.error('WebSocket error:', error);
        };
        
        setWs(websocket);
      } catch (error) {
        addToLog('❌ Failed to create WebSocket connection', 'error');
        console.error('Connection error:', error);
      }
    };
    
    connectWebSocket();
    
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []);

  const testConnection = () => {
    addToLog('🔄 Manual connection test initiated');
    if (ws && ws.readyState === WebSocket.OPEN) {
      const testMessage = {
        type: 'ping',
        message: 'Manual connection test',
        timestamp: Date.now()
      };
      ws.send(JSON.stringify(testMessage));
      addToLog('📤 Sent manual test message', 'success');
    } else {
      addToLog('❌ WebSocket not connected', 'error');
    }
  };

  useEffect(() => {
    const loadBook = async () => {
      setLoading(true);
      const fetchedBook = await fetchBook(bookId);
      setBook(fetchedBook);
      setLoading(false);
    };
    loadBook();
  }, [bookId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (book && book.chapters && book.chapters[currentChapterIndex]) {
      const currentChapter = book.chapters[currentChapterIndex];
      const progress = ((currentChapterIndex + 1) / book.chapters.length) * 100;
      
      setReadingHistory((prev) => {
        const existing = prev.findIndex((p) => p.bookId === book.id);
        const newProgress: ReadingProgress = {
          bookId: book.id,
          chapterId: currentChapter.id,
          progress: Math.round(progress),
          lastRead: new Date().toISOString(),
        };
        
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = newProgress;
          return updated;
        }
        return [...prev, newProgress];
      });
    }
  }, [currentChapterIndex, book, setReadingHistory]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      });
      
      audioStreamRef.current = stream;
      
      // Create AudioContext for PCM conversion
      const audioContext = new AudioContext({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      
      processor.onaudioprocess = (event) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          const inputBuffer = event.inputBuffer;
          const inputData = inputBuffer.getChannelData(0);
          
          // Convert float32 to int16 PCM
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
          }
          
          // Convert to base64
          const base64Data = btoa(String.fromCharCode(...new Uint8Array(pcmData.buffer)));
          
          const message = {
            type: 'audio',
            data: base64Data,
            timestamp: Date.now(),
            format: 'pcm',
            sampleRate: 16000
          };
          ws.send(JSON.stringify(message));
          addToLog(`Sent PCM audio chunk (${pcmData.length * 2} bytes)`);
        }
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      // Store references for cleanup
      mediaRecorderRef.current = { audioContext, processor, source };
      
      setIsRecording(true);
      addToLog('Started recording audio in PCM format', 'success');
    } catch (error) {
      addToLog('Failed to access microphone', 'error');
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      const { audioContext, processor, source } = mediaRecorderRef.current;
      if (processor) {
        source.disconnect(processor);
        processor.disconnect();
      }
      if (audioContext) {
        audioContext.close();
      }
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
    }
    setIsRecording(false);
    addToLog('Stopped recording audio');
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const sendMessage = (content: string) => {
    if (!content.trim()) return;
    
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      userId: profile.id,
      userName: profile.name,
      avatarUrl: profile.avatarUrl,
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, newMessage]);
    
    if (ws && ws.readyState === WebSocket.OPEN) {
      const wsMessage = {
        type: 'chat_message',
        message: content.trim(),
        user: profile.name,
        timestamp: Date.now()
      };
      ws.send(JSON.stringify(wsMessage));
      addToLog(`Sent chat message: "${content.trim()}"`, 'success');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const input = e.target as HTMLInputElement;
      sendMessage(input.value);
      input.value = '';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!book) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Book not found</h2>
          <p className="text-gray-400">The requested book could not be loaded.</p>
        </div>
      </div>
    );
  }

  const currentChapter = book.chapters?.[currentChapterIndex];
  const progress = book.chapters ? ((currentChapterIndex + 1) / book.chapters.length) * 100 : 0;

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Main Reading Area */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${
        isChatOpen ? 'mr-96' : 'mr-0'
      }`}>
        {/* Header */}
        <header className="flex items-center justify-between p-4 border-b border-gray-800">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold truncate">{book.title}</h1>
            <div className="flex items-center space-x-2 text-sm text-gray-400">
              <Users className="h-4 w-4" />
              <span>{onlineUsers} reading</span>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs ${
              wsStatus === 'connected' 
                ? 'bg-green-900/50 text-green-400' 
                : 'bg-red-900/50 text-red-400'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                wsStatus === 'connected' ? 'bg-green-400' : 'bg-red-400'
              }`} />
              {wsStatus === 'connected' ? 'Connected' : 'Disconnected'}
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={testConnection}
              className="text-gray-400 hover:text-white"
            >
              Test Connection
            </Button>
            
            <ThemeToggle />
            
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="sm">
                  <Settings className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent>
                <SheetHeader>
                  <SheetTitle>Reading Settings</SheetTitle>
                </SheetHeader>
                <div className="space-y-6 mt-6">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Font Size</label>
                    <div className="flex items-center space-x-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setLocalFontSize(Math.max(12, localFontSize - 2))}
                      >
                        <Minus className="h-4 w-4" />
                      </Button>
                      <span className="text-sm w-12 text-center">{localFontSize}px</span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setLocalFontSize(Math.min(24, localFontSize + 2))}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </SheetContent>
            </Sheet>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsChatOpen(!isChatOpen)}
            >
              <MessageSquare className="h-4 w-4" />
            </Button>
          </div>
        </header>

        {/* Reading Content */}
        <div className="flex-1 overflow-auto">
          {book?.pdfUrl ? (
            <PDFViewer pdfUrl={book.pdfUrl} className="h-full" />
          ) : (
            <div className="max-w-4xl mx-auto p-8">
              {currentChapter && (
                <motion.div
                  key={currentChapter.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <h2 className="text-2xl font-bold mb-6">{currentChapter.title}</h2>
                  <div 
                    className="prose prose-invert max-w-none leading-relaxed"
                    style={{ 
                      fontSize: `${localFontSize}px`,
                      lineHeight: preferences.lineSpacing 
                    }}
                  >
                    {currentChapter.content.split('\n\n').map((paragraph, index) => (
                      <p key={index} className="mb-4">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </motion.div>
              )}
            </div>
          )}
        </div>

        {/* Navigation - Only show for books without PDF */}
        {!book?.pdfUrl && book?.chapters?.length && (
          <div className="flex items-center justify-between p-4 border-t border-gray-800">
            <Button
              variant="ghost"
              onClick={() => setCurrentChapterIndex(Math.max(0, currentChapterIndex - 1))}
              disabled={currentChapterIndex === 0}
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Previous
            </Button>
            
            <span className="text-sm text-gray-400">
              {currentChapter?.title}
            </span>
            
            <Button
              variant="ghost"
              onClick={() => setCurrentChapterIndex(Math.min((book.chapters?.length || 1) - 1, currentChapterIndex + 1))}
              disabled={currentChapterIndex >= (book.chapters?.length || 1) - 1}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        )}
      </div>

      {/* Chat Sidebar */}
      <AnimatePresence>
        {isChatOpen && (
          <motion.div
            initial={{ x: 384 }}
            animate={{ x: 0 }}
            exit={{ x: 384 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-full w-96 bg-gray-800 border-l border-gray-700 flex flex-col"
          >
            {/* Chat Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <div className="flex items-center space-x-2">
                <MessageSquare className="h-5 w-5" />
                <h3 className="font-semibold">Reading Chat</h3>
                <span className="text-xs text-gray-400">({onlineUsers} online)</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsChatOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Voice Controls */}
            <div className="p-4 border-b border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Voice Chat</span>
                <div className={`text-xs px-2 py-1 rounded ${
                  wsStatus === 'connected' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                }`}>
                  {wsStatus === 'connected' ? 'Ready' : 'Offline'}
                </div>
              </div>
              <Button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={wsStatus !== 'connected'}
                className={`w-full ${
                  isRecording 
                    ? 'bg-red-600 hover:bg-red-700' 
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {isRecording ? (
                  <>
                    <Square className="h-4 w-4 mr-2" />
                    Stop Recording
                  </>
                ) : (
                  <>
                    <Mic className="h-4 w-4 mr-2" />
                    Start Recording
                  </>
                )}
              </Button>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                {messages.map((message) => (
                  <div key={message.id} className="flex space-x-3">
                    <Avatar className="h-8 w-8 flex-shrink-0">
                      <AvatarImage src={message.avatarUrl} />
                      <AvatarFallback className="text-xs">
                        {message.userId === 'transcription' ? '🎤' : message.userName.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className={`text-sm font-medium ${
                          message.userId === 'transcription' ? 'text-blue-400' : 'text-white'
                        }`}>
                          {message.userName}
                        </span>
                        <span className="text-xs text-gray-400">
                          {formatTimestamp(message.timestamp)}
                        </span>
                      </div>
                      <p className={`text-sm break-words ${
                        message.userId === 'transcription' 
                          ? message.userName === 'Listening...' 
                            ? 'text-gray-400 italic' 
                            : 'text-blue-300'
                          : 'text-gray-300'
                      }`}>
                        {message.content}
                      </p>
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
            </ScrollArea>

            {/* Activity Log */}
            <div className="p-4 border-t border-gray-700 bg-gray-900">
              <div className="text-xs text-gray-400 mb-2">Activity Log:</div>
              <ScrollArea className="h-20">
                <div className="space-y-1">
                  {activityLog.slice(-10).map((log, index) => (
                    <div key={index} className="text-xs text-gray-500 font-mono">
                      {log}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Reading;