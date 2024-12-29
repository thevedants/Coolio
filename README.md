# Coolio: Emotion-Based Music Recommender

An AI-powered web application that recommends music based on your emotional state. The system captures video and audio, analyzes your facial expressions and speech, and uses AI to suggest songs that match your current mood.

## Features

- Real-time video and audio recording
- Facial emotion detection using FER (Facial Expression Recognition)
- Speech-to-text transcription with Deepgram
- AI-powered song recommendations using Mistral

## Setup

### Prerequisites
- Node.js and npm
- Python 3.x
- API Keys:
  - Deepgram 
  - Mistral

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

pip install fastapi uvicorn python-multipart deepgram-sdk fer python-dotenv requests

# Create .env file
touch .env

# Add your API keys to .env
DEEPGRAM_API_KEY=your_key_here
MISTRAL_API_KEY=your_key_here

# Run server
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

## Usage

1. Start both backend and frontend servers
2. Open the web app in your browser
3. Click "Start Recording" 
4. Allow camera and microphone access
5. Record yourself speaking about your current mood
6. Click "Stop Recording"
7. View your emotion analysis and personalized song recommendations

## Environment Variables

Create a `.env` file in the backend directory with:
```
DEEPGRAM_API_KEY=your_key_here
MISTRAL_API_KEY=your_key_here
```

## Future Enhancements

- Last.fm integration for similar songs
- Lyrics analysis
- User accounts and history
- Song preview functionality

## License

MIT