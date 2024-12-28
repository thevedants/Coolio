import os
import requests

async def get_recommendations(emotions, transcript):
    API_KEY = os.getenv('MISTRAL_API_KEY')
    
    # Create prompt based on emotions and transcript
    prompt = f"""Based on the following emotional analysis and speech transcript, 
    suggest 5 songs that match the mood and content:
    
    Emotions detected: {emotions}
    Speech transcript: {transcript}
    
    Please suggest songs in this format:
    1. Song - Artist
    2. Song - Artist
    etc."""
    
    # Call Mistral API
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "mistral-tiny",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    response = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        songs = response.json()['choices'][0]['message']['content'].strip().split('\n')
        return songs
    else:
        raise Exception(f"Mistral API error: {response.text}")