from flask import Flask, request, jsonify
import json
from flask_cors import CORS

import os
import aiohttp
import requests
from fer import Video
from mistralai import Mistral
from dotenv import load_dotenv
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
import cv2
import numpy as np
from fer import FER
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import redis
from datetime import timedelta
import hashlib

from asgiref.wsgi import WsgiToAsgi
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Create upload folder if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app = Flask(__name__)
asgi_app = WsgiToAsgi(app)

CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:8000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "expose_headers": ["Content-Type"],
        "max_age": 3600,
        "supports_credentials": True
    }
})

def create_cors_response(data, status_code=200):
    response = jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:8000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response, status_code


# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
MISTRAL_API_KEY = os.environ["MISTRAL_API_KEY"]
LASTFM_API_KEY = os.getenv('LASTFM_API_KEY')
MUSIXMATCH_API_KEY = os.getenv('MUSIXMATCH_API_KEY')

# Initialize Redis for caching
redis_client = redis.Redis(host='localhost', port=6379, db=0)
CACHE_EXPIRATION = timedelta(hours=24)

# Create ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=4)
def process_audio_file(filepath):
    """Process audio file using Deepgram"""
    try:
        # Initialize Deepgram client
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)

        # Read the audio file
        with open(filepath, "rb") as file:
            buffer_data = file.read()

        payload: FileSource = {
            "buffer": buffer_data,
        }

        # Configure Deepgram options
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True
        )

        # Transcribe the file
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
        # Parse response
        response_dict = json.loads(response.to_json())
        transcript = response_dict["results"]["channels"][0]["alternatives"][0]["transcript"]
        return transcript
    except Exception as e:
        print(f"Exception in process_audio_file: {e}")
        return None
def get_cache_key(*args):
    """Generate a cache key from arguments"""
    return hashlib.md5(str(args).encode()).hexdigest()

def cache_get(key):
    """Get value from cache"""
    value = redis_client.get(key)
    return json.loads(value) if value else None

def cache_set(key, value):
    """Set value in cache"""
    redis_client.setex(
        key,
        CACHE_EXPIRATION,
        json.dumps(value)
    )

@lru_cache(maxsize=100)
def analyze_video_mood(filepath):
    """Analyze mood from video using FER"""
    try:
        # Create Video object from the file
        video = Video(filepath)
        detector = FER(mtcnn=True, padding=0.3)
        
        # Analyze the video
        raw_data = video.analyze(detector, display=False)  # Set display=False for backend processing
        
        # Convert to pandas and get emotion averages
        df = video.to_pandas(raw_data)
        emotion_averages = df[['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']].mean()
        
        # Get the dominant emotion
        dominant_emotion = emotion_averages.idxmax()
        
        return dominant_emotion
    except Exception as e:
        print(f"Error in video analysis: {e}")
        return "neutral"


# Add this route after your other imports but before the upload route



@app.route('/', methods=['GET'])
def home():
    return '''
    <html>
        <head>
            <title>Mood-Based Music Recommender</title>
        </head>
        <body>
            <h1>Welcome to Mood-Based Music Recommender</h1>
            <p>This is the API server. To use the application, please access the frontend HTML page.</p>
        </body>
    </html>
    '''

# Also add a route to check if the server is running
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Server is running"}), 200
async def process_song_batch(songs, themes, mood):
    """Process a batch of songs in parallel"""
    async def process_single_song(song):
        cache_key = get_cache_key('song_analysis', song['title'], song['artist'], themes, mood)
        cached_result = cache_get(cache_key)
        
        if cached_result:
            return cached_result
            
        lyrics = await get_lyrics(song['title'], song['artist'])
        if lyrics:
            relevance_score = await analyze_lyrics_relevance(lyrics, themes, mood)
            result = {
                'title': song['title'],
                'artist': song['artist'],
                'relevance_score': relevance_score
            }
            cache_set(cache_key, result)
            return result
        return None

    tasks = [process_single_song(song) for song in songs]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]

@lru_cache(maxsize=50)
async def get_similar_songs(song_title, artist):
    """Get similar songs using Last.fm API with caching"""
    cache_key = get_cache_key('similar_songs', song_title, artist)
    cached_result = cache_get(cache_key)
    
    if cached_result:
        return cached_result
        
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        'method': 'track.getsimilar',
        'artist': artist,
        'track': song_title,
        'api_key': LASTFM_API_KEY,
        'format': 'json',
        'limit': 5
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                tracks = data.get('similartracks', {}).get('track', [])
                result = [{'title': track['name'], 'artist': track['artist']['name']} 
                         for track in tracks]
                cache_set(cache_key, result)
                return result
    except Exception as e:
        print(f"Error getting similar songs: {e}")
        return []

@lru_cache(maxsize=100)
async def get_lyrics(song_title, artist):
    """Get lyrics using Musixmatch API with caching"""
    cache_key = get_cache_key('lyrics', song_title, artist)
    cached_result = cache_get(cache_key)
    
    if cached_result:
        return cached_result

    base_url = "https://api.musixmatch.com/ws/1.1/"
    
    search_params = {
        'q_track': song_title,
        'q_artist': artist,
        'apikey': MUSIXMATCH_API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get track ID
            async with session.get(f"{base_url}track.search", params=search_params) as response:
                track_data = await response.json()
                track_id = track_data['message']['body']['track_list'][0]['track']['track_id']
            
            # Get lyrics
            lyrics_params = {
                'track_id': track_id,
                'apikey': MUSIXMATCH_API_KEY
            }
            async with session.get(f"{base_url}track.lyrics.get", params=lyrics_params) as response:
                lyrics_data = await response.json()
                lyrics = lyrics_data['message']['body']['lyrics']['lyrics_body']
                cache_set(cache_key, lyrics)
                return lyrics
    except Exception as e:
        print(f"Error getting lyrics: {e}")
        return None

async def analyze_lyrics_relevance(lyrics, themes, mood):
    """Analyze lyrics relevance using Mistral"""
    client = Mistral(api_key=MISTRAL_API_KEY)
    
    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {
                    "role": "system",
                    "content": "You are a lyrics analysis assistant. Rate how well lyrics match given themes and mood on a scale of 0-100. Return only the number."
                },
                {
                    "role": "user",
                    "content": f"Lyrics: {lyrics}\nThemes: {themes}\nMood: {mood}\nRate relevance (0-100):"
                }
            ]
        )
        return float(response.choices[0].message.content)
    except Exception as e:
        print(f"Error analyzing lyrics: {e}")
        return 0

async def get_recommendations(transcript, mood):
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
        
        chat_response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {
                    "role": "system",
                    "content": "You are a song recommender bot. You will be given a transcript of how a person is feeling today and their detected mood. You have to identify the themes and emotions/mood the person is feeling. You are supposed to use these to recommend up to 5 songs that are suitable for their mood and reflect any themes they have talked about in the transcript. Keep your response concise, just list the song title and song artist in a json format and nothing else. In your json response, also create a field where all the emotions/themes/mood will be returned in a list"
                },
                {
                    "role": "user",
                    "content": f"Transcript: {transcript}\nDetected Mood: {mood}"
                }
            ]
        )
        
        return chat_response.choices[0].message.content
    except Exception as e:
        print(f"Exception in get_recommendations: {e}")
        return None
    

@app.route('/upload', methods=['POST', 'OPTIONS'])
async def upload_file():
    if request.method == "OPTIONS":
        return create_cors_response({"status": "ok"})
    try:
        print("Upload request received")
        print("Files in request:", request.files)  # Debug
        print("Form data:", request.form)  # Debug        
        if 'file' not in request.files:
            print("No file in request")  # Debug log
            return jsonify({'error': 'No file part'}), 400

        
        file = request.files['file']
        initial_mood = request.form.get('mood', 'neutral')
        print(f"Received file: {file.filename}")
        print(f"Initial mood: {initial_mood}")
        if file:
            try:
                filename = f"recording_{initial_mood}_{os.urandom(4).hex()}.webm"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                print(f"File saved to: {filepath}")
                
                if not os.path.exists(filepath):
                    print("File was not saved successfully")
                    return jsonify({'error': 'Failed to save file'}), 500
                    
                filesize = os.path.getsize(filepath)
                print(f"File size: {filesize} bytes")
                
                if filesize == 0:
                    print("File is empty")
                    return jsonify({'error': 'Empty file uploaded'}), 400
            except:
                print("No File")
            
            # Run video and audio processing in parallel
            video_mood_task = executor.submit(analyze_video_mood, filepath)
            transcript_task = executor.submit(process_audio_file, filepath)
            
            video_mood = await asyncio.wrap_future(video_mood_task)
            transcript = await asyncio.wrap_future(transcript_task)
            
            if not transcript:
                return jsonify({'error': 'Failed to process audio'}), 500
            
            # Get initial recommendations
            initial_recommendations = await get_recommendations(transcript, video_mood)
            if not initial_recommendations:
                return jsonify({'error': 'Failed to get recommendations'}), 500
            
            recommendations_dict = json.loads(initial_recommendations)
            initial_songs = recommendations_dict.get('songs', [])
            themes = recommendations_dict.get('emotions/themes/mood', []) 

            # Get similar songs for all initial songs in parallel
            similar_songs_tasks = [
                get_similar_songs(song['title'], song['artist'])
                for song in initial_songs
            ]
            similar_songs_results = await asyncio.gather(*similar_songs_tasks)
            similar_songs = [song for sublist in similar_songs_results for song in sublist]
            
            # Process songs in batches for better performance
            BATCH_SIZE = 10
            final_songs = []
            for i in range(0, len(similar_songs), BATCH_SIZE):
                batch = similar_songs[i:i + BATCH_SIZE]
                scored_batch = await process_song_batch(batch, themes, video_mood)
                final_songs.extend(scored_batch)
            
            # Sort by relevance score and get top 5
            final_songs.sort(key=lambda x: x['relevance_score'], reverse=True)
            final_songs = final_songs[:5]
            
            # Clean up
            os.remove(filepath)
            
            formatted_response = await format_recommendations(recommendations_dict, video_mood, final_songs)
            return jsonify(formatted_response)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500
async def format_recommendations(recommendations_dict, video_mood, final_songs):
                """Format the recommendations to ensure consistent output"""
                return {
                    'songs': final_songs,
                    'themes': recommendations_dict.get('emotions/themes/mood', []),  # Get from correct field
                    'mood': video_mood,
                    'initial_songs': recommendations_dict.get('songs', [])  # Optionally keep initial recommendations
}



if __name__ == '__main__':
    config = Config()
    config.bind = ["localhost:5000"]
    asyncio.run(serve(asgi_app, config))