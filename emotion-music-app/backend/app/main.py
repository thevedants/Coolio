from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from .processing.audio import process_audio
from .processing.video import process_video
from .processing.mistral import get_recommendations

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your React app's address
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")  # Add this new root endpoint
async def root():
    return {"message": "Emotion Music API is running"}

@app.post("/process")
async def process_media(video: UploadFile = File(...), audio: UploadFile = File(...)):
    try:
        print(f"Received files - Video: {video.filename}, Audio: {audio.filename}")

        # Process both files concurrently
        video_task = asyncio.create_task(process_video(video))
        audio_task = asyncio.create_task(process_audio(audio))
        print("Processing files...")        
        # Wait for both tasks to complete
        emotions, transcript = await asyncio.gather(video_task, audio_task)
        print(f"Processing complete - Emotions: {emotions}")
        print(f"Transcript: {transcript}")
        # Get song recommendations based on emotions and transcript
        recommendations = await get_recommendations(emotions, transcript)
        
        return {
            "status": "success",
            "emotions": emotions,
            "transcript": transcript,
            "recommendations": recommendations
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}