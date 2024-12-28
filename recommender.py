import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# Get access token from environment variable
access_token = os.getenv('SPOTIFY_ACCESS_TOKEN')

def get_available_genre_seeds(access_token):
    url = "https://api.spotify.com/v1/recommendations/available-genre-seeds"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['genres']
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

try:
    genres = get_available_genre_seeds(access_token)
    print("Available genre seeds:")
    print(", ".join(genres))
except Exception as e:
    print(f"An error occurred: {e}")
