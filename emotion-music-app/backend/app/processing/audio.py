from deepgram import DeepgramClient, PrerecordedOptions, FileSource
import os
import json
from dotenv import load_dotenv
import aiofiles
import asyncio
load_dotenv()
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')

async def process_audio(audio_file):
    # Save uploaded file temporarily
    temp_path = f"temp_{audio_file.filename}"
    try:
        async with aiofiles.open(temp_path, 'wb') as out_file:
            content = await audio_file.read()
            await out_file.write(content)

        # Initialize Deepgram
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)

        # Read the audio file
        with open(temp_path, "rb") as file:
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
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
