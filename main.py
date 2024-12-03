from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
import requests

app = FastAPI()



# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # React 앱의 URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# YouTube Data API 키
API_KEY = "본인의 키로 대체"

def search_youtube_videos(keyword, max_results=5):
    """
    유튜브에서 키워드로 비디오 검색
    """
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "maxResults": max_results,
        "key": API_KEY,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if "items" in data:
            return [
                {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "published_at": item["snippet"]["publishedAt"],
                    "description": item["snippet"]["description"],
                    "thumbnails": item["snippet"]["thumbnails"],
                }
                for item in data["items"]
            ]
        return []
    else:
        raise HTTPException(status_code=response.status_code, detail="YouTube API 호출 실패")

def get_transcript(video_id):
    """
    유튜브 동영상 ID를 사용하여 자막 데이터를 가져옵니다.
    """
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["ko", "en"])
        return " ".join([entry["text"] for entry in transcript])
    except NoTranscriptFound:
        return "자막을 찾을 수 없습니다."
    except TranscriptsDisabled:
        return "자막이 비활성화되었습니다."
    except Exception as e:
        return f"알 수 없는 오류 발생: {e}"

@app.get("/search")
async def search_videos(keyword: str):
    """
    키워드로 유튜브 비디오 검색
    """
    return search_youtube_videos(keyword)

@app.get("/transcript/{video_id}")
async def get_video_transcript(video_id: str):
    """
    비디오 ID로 자막 가져오기
    """
    transcript = get_transcript(video_id)
    return {"transcript": transcript}
