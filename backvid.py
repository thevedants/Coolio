from fer import Video
from fer import FER

video_filename = "path_to_your_video.mp4"
video = Video(video_filename)
detector = FER(mtcnn=True)
raw_data = video.analyze(detector, display=True)
df = video.to_pandas(raw_data)
emotion_averages = df[['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']].mean()
dominant_emotions = emotion_averages.sort_values(ascending=False)
print(dominant_emotions)

