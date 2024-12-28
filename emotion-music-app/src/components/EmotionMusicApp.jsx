import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Video, StopCircle, Mic } from 'lucide-react';

const EmotionMusicApp = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [videoBlob, setVideoBlob] = useState(null);
  const [audioBlob, setAudioBlob] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [status, setStatus] = useState('');
  const [transcript, setTranscript] = useState('');
  const [emotions, setEmotions] = useState(null);
  
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const streamRef = useRef(null);
  
  const videoChunks = useRef([]);
  const audioChunks = useRef([]);

  const startRecording = async () => {
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true 
      });
      
      videoRef.current.srcObject = streamRef.current;
      
      mediaRecorderRef.current = new MediaRecorder(streamRef.current);
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          videoChunks.current.push(event.data);
        }
      };
      mediaRecorderRef.current.onstop = () => {
        const videoBlob = new Blob(videoChunks.current, { type: 'video/webm' });
        setVideoBlob(videoBlob);
        videoChunks.current = [];
      };

      const audioStream = new MediaStream([streamRef.current.getAudioTracks()[0]]);
      audioRecorderRef.current = new MediaRecorder(audioStream);
      audioRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.current.push(event.data);
        }
      };
      audioRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
        setAudioBlob(audioBlob);
        audioChunks.current = [];
      };

      mediaRecorderRef.current.start();
      audioRecorderRef.current.start();
      setIsRecording(true);
      setStatus('Recording in progress...');
      
    } catch (err) {
      console.error('Error starting recording:', err);
      setStatus('Error starting recording: ' + err.message);
    }
  };

  const stopRecording = () => {
    try {
      if (mediaRecorderRef.current && audioRecorderRef.current) {
        mediaRecorderRef.current.stop();
        audioRecorderRef.current.stop();
        
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          videoRef.current.srcObject = null;
        }
        
        setIsRecording(false);
        setStatus('Processing recording...');
      }
    } catch (err) {
      console.error('Error stopping recording:', err);
      setStatus('Error stopping recording: ' + err.message);
    }
  };

  const sendToBackend = async () => {
    if (!videoBlob || !audioBlob) return;

    setIsProcessing(true);
    setStatus('Analyzing media...');

    try {
      console.log('Sending blobs to backend:', {
        videoSize: videoBlob.size,
        audioSize: audioBlob.size
    });
      const formData = new FormData();
      formData.append('video', videoBlob, 'recording.webm');
      formData.append('audio', audioBlob, 'audio.webm');
      console.log('Sending request to backend...');
      const response = await fetch('http://localhost:8000/process', {
        method: 'POST',
        body: formData,
      });
      console.log('Response status:', response.status);
      if (!response.ok) {
        console.error('Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Received data:', data);      
      setEmotions(data.emotions);
      setTranscript(data.transcript);
      setRecommendations(data.recommendations);
      setStatus('Analysis complete!');

    } catch (error) {
      console.error('Error sending media:', error);
      setStatus('Error processing media: ' + error.message);
    } finally {
      setIsProcessing(false);
    }
  };

  useEffect(() => {
    if (videoBlob && audioBlob && !isProcessing) {
      sendToBackend();
    }
  }, [videoBlob, audioBlob]);

  return (
    <div className="w-full max-w-2xl mx-auto p-4">
      <Card className="p-6">
        <div className="space-y-4">
          <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
            />
          </div>

          <div className="flex justify-center gap-4">
            {!isRecording ? (
              <Button 
                onClick={startRecording}
                className="flex items-center gap-2"
                disabled={isProcessing}
              >
                <Video className="w-4 h-4" />
                <Mic className="w-4 h-4" />
                Start Recording
              </Button>
            ) : (
              <Button 
                onClick={stopRecording}
                variant="destructive"
                className="flex items-center gap-2"
              >
                <StopCircle className="w-4 h-4" />
                Stop Recording
              </Button>
            )}
          </div>

          {status && (
            <div className="text-center">
              <p className="text-lg font-semibold">{status}</p>
            </div>
          )}

          {transcript && (
            <div className="mt-4">
              <h3 className="text-lg font-semibold mb-2">Transcript:</h3>
              <p className="p-2 bg-gray-50 rounded">{transcript}</p>
            </div>
          )}

          {emotions && (
            <div className="mt-4">
              <h3 className="text-lg font-semibold mb-2">Detected Emotions:</h3>
              <div className="p-2 bg-gray-50 rounded">
                {Object.entries(emotions).map(([emotion, value]) => (
                  <div key={emotion} className="flex justify-between">
                    <span className="capitalize">{emotion}:</span>
                    <span>{(value * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {recommendations.length > 0 && (
            <div className="mt-4">
              <h3 className="text-lg font-semibold mb-2">Recommended Songs:</h3>
              <ul className="space-y-2">
                {recommendations.map((song, index) => (
                  <li key={index} className="p-2 bg-gray-50 rounded">
                    {song}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default EmotionMusicApp;