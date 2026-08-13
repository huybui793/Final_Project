import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

def search_youtube_videos(query, max_results=3):
    youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
    request = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results
    )
    response = request.execute()
    
    videos = []
    for item in response["items"]:
        videos.append({
            "title": item["snippet"]["title"],
            "video_id": item["id"]["videoId"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        })
    return videos