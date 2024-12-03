from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import requests
from YouTubeTranscriber import YouTubeTranscriber
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
API_KEY = "AIzaSyB8M5Pvuy5kbaBPupU9WeRHRq_VytvgUgM"



def search_youtube_videos(keyword, max_results=50):
    """
    유튜브에서 키워드로 비디오 검색 후 조회수 및 좋아요 높은 순으로 정렬하여 반환
    """
    # 유튜브 검색 API 호출
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "maxResults": max_results,
        "key": API_KEY,
    }
    search_response = requests.get(search_url, params=search_params)
    if search_response.status_code == 200:
        search_data = search_response.json()
        if "items" in search_data:
            # video_ids 추출
            video_ids = [item["id"]["videoId"] for item in search_data["items"] if "videoId" in item["id"]]
            
            # 비디오의 상세 정보 (statistics 및 contentDetails) 가져오기
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            videos_params = {
                "part": "statistics,contentDetails",
                "id": ",".join(video_ids),
                "key": API_KEY,
            }
            videos_response = requests.get(videos_url, params=videos_params)
            
            if videos_response.status_code == 200:
                videos_data = videos_response.json()
                filtered_videos = []

                for item in videos_data["items"]:
                    video_id = item["id"]
                    statistics = item.get("statistics", {})
                    content_details = item.get("contentDetails", {})
                    snippet = next(
                        (v["snippet"] for v in search_data["items"] if v["id"]["videoId"] == video_id), None
                    )
                    
                    # 필요한 데이터 확인 및 필터링
                    if not snippet or not content_details or not statistics:
                        continue
                    
                    # 영상 길이 (5분 이상 필터링)
                    duration = content_details.get("duration")
                    total_seconds = parse_iso8601_duration(duration) if duration else 0
                    if total_seconds < 300:
                        continue
                    
                    # 좋아요와 조회수 가져오기
                    view_count = int(statistics.get("viewCount", 0))
                    like_count = int(statistics.get("likeCount", 0))

                    filtered_videos.append({
                        "video_id": video_id,
                        "title": snippet.get("title"),
                        "channel": snippet.get("channelTitle"),
                        "published_at": snippet.get("publishedAt"),
                        "description": snippet.get("description"),
                        "thumbnails": snippet.get("thumbnails"),
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "view_count": view_count,
                        "like_count": like_count,
                    })
                
                # 좋아요 및 조회수를 기준으로 정렬 (그리디 방식)
                sorted_videos = sorted(
                    filtered_videos, 
                    key=lambda x: (x["like_count"], x["view_count"]), 
                    reverse=True
                )
                
                return sorted_videos
            else:
                raise HTTPException(status_code=videos_response.status_code, detail="YouTube Videos API 호출 실패")
        return []
    else:
        raise HTTPException(status_code=search_response.status_code, detail="YouTube Search API 호출 실패")
    

    
def parse_iso8601_duration(duration):
    """
    ISO 8601 duration 형식을 초 단위로 변환 (e.g., PT5M30S -> 330초)
    """
    import re
    match = re.match(r'PT((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?', duration)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return minutes * 60 + seconds




# YouTube 자막 처리
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["ko", "en"])
        if transcript is None:
            raise HTTPException(status_code=404, detail="No transcript available.")
        combined_text = " ".join([entry["text"] for entry in transcript])
        return combined_text
    except NoTranscriptFound:
        print("자막이 존재하지 않거나 사용할 수 없습니다.")
        return None
    except TranscriptsDisabled:
        print("영상의 자막 사용이 비활성화되었습니다.")
        return None
    except Exception as e:
        print(f"알 수 없는 오류 발생: {e}")
        return None


@app.get("/search")
async def search_videos(keyword: str):
    """
    키워드로 유튜브 비디오 검색
    """
    return search_youtube_videos(keyword)

@app.get("/transcript/{video_id}")
async def get_video_transcript(video_id: str):
    transcript = get_transcript(video_id)
    
    if not transcript:  # 자막이 없으면 Whisper로 대체
        transcriber = YouTubeTranscriber(model_size='base', language='ko')
        url = f"https://www.youtube.com/watch?v={video_id}"
        result = transcriber.transcribe(url)
        if result:
            return {"transcript": result['text']}
        else:
            raise HTTPException(status_code=500, detail="Failed to transcribe the video using Whisper.")
    
    return {"transcript": transcript}
