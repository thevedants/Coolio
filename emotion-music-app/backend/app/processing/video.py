from fer import FER
import cv2
import numpy as np
from tempfile import NamedTemporaryFile
import os

async def process_video(video_file):
    # Initialize FER
    detector = FER(mtcnn=True)
    
    # Save uploaded file temporarily
    temp_path = f"temp_{video_file.filename}"
    try:
        # Save the uploaded file
        content = await video_file.read()
        with open(temp_path, 'wb') as f:
            f.write(content)
            
        # Process video with OpenCV
        cap = cv2.VideoCapture(temp_path)
        emotions = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Detect emotions in frame
            result = detector.detect_emotions(frame)
            if result:
                emotions.append(result[0]['emotions'])
                
        cap.release()
        
        # Aggregate emotions
        if emotions:
            avg_emotions = {
                emotion: np.mean([frame[emotion] for frame in emotions])
                for emotion in emotions[0].keys()
            }
            return avg_emotions
        return {}
        
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)