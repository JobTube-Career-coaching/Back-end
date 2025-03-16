from fastapi import HTTPException
import requests
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

class YouTubeService:
    def __init__(self, api_key):
        self.API_KEY = api_key
        self._latest_keyword = None
        self._is_disability_search = False

    def set_disability_search(self, is_disability: bool):
        """장애인 전용 검색 모드 설정"""
        self._is_disability_search = is_disability

    def generate_category_keywords(self, keyword):
        """키워드를 세 가지 카테고리로 확장"""
        base_keyword = f"장애인 {keyword}" if self._is_disability_search and "장애인" not in keyword else keyword
        
        categories = [
            {"id": "pros_cons", "name": "장단점", "search_terms": [f"{base_keyword} 장단점", f"{base_keyword} 특징", f"{base_keyword} 어려움"]},
            {"id": "how_to", "name": "준비방법", "search_terms": [f"{base_keyword} 되는법", f"{base_keyword} 준비", f"{base_keyword} 자격증", f"{base_keyword} 공부"]},
            {"id": "review", "name": "후기", "search_terms": [f"{base_keyword} 후기", f"{base_keyword} 경험", f"{base_keyword} 인터뷰"]}
        ]
        
        return categories

    def get_video_info(self, video_id, keyword=None, category=None):
        """
        비디오 정보를 가져오는 메서드
        keyword 파라미터와 category 파라미터 추가
        """
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            "part": "snippet,statistics",
            "id": video_id,
            "key": self.API_KEY,
        }
        
        try:
            videos_response = requests.get(videos_url, params=videos_params)
            videos_response.raise_for_status()
            videos_data = videos_response.json()

            if not videos_data.get("items"):
                raise HTTPException(status_code=404, detail="비디오를 찾을 수 없습니다.")

            item = videos_data["items"][0]
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})

            search_keyword = keyword or self._latest_keyword

            return {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "description": snippet.get("description", ""),
                "thumbnails": snippet.get("thumbnails", {}),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "view_count": int(statistics.get("viewCount", 0)),
                "like_count": int(statistics.get("likeCount", 0)),
                "tags": snippet.get("tags", []),
                "search_keyword": search_keyword,
                "category": category,
                "is_disability_content": self._is_disability_search
            }

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"YouTube API 호출 중 오류 발생: {str(e)}")

    def search_youtube_videos_by_category(self, keyword, max_results_per_category=3):
        """카테고리별로 YouTube 비디오를 검색하는 메서드"""
        self._latest_keyword = keyword
        categories = self.generate_category_keywords(keyword)
        all_videos_by_category = {}
        
        for category in categories:
            category_videos = []
            
            for search_term in category["search_terms"]:
                try:
                    # 각 검색어로 검색 수행
                    search_url = "https://www.googleapis.com/youtube/v3/search"
                    search_params = {
                        "part": "snippet",
                        "q": search_term,
                        "type": "video",
                        "videoDuration": "medium",
                        "maxResults": 10,  # 더 많은 결과를 요청하여 필터링할 여지를 둠
                        "key": self.API_KEY,
                    }
                    
                    search_response = requests.get(search_url, params=search_params)
                    search_response.raise_for_status()
                    search_data = search_response.json()
                    
                    if "items" not in search_data:
                        continue

                    # 비디오 정보 가져오기
                    video_ids = [item["id"]["videoId"] for item in search_data["items"] if "videoId" in item["id"]]
                    videos_with_transcript = []
                    
                    for video_id in video_ids:
                        try:
                            # 자막이 있는지 확인
                            try:
                                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["ko", "en"])
                                if not transcript:
                                    continue
                            except Exception:
                                continue
                                
                            # 비디오 정보 가져오기
                            video_info = self.get_video_info(video_id, keyword, category["id"])
                            videos_with_transcript.append(video_info)
                            
                        except HTTPException:
                            continue
                    
                    # 조회수 기준으로 정렬
                    videos_with_transcript.sort(key=lambda x: x["view_count"], reverse=True)
                    category_videos.extend(videos_with_transcript)
                    
                    # 충분한 비디오를 찾았으면 다음 검색어로 넘어감
                    if len(category_videos) >= max_results_per_category:
                        break
                        
                except requests.exceptions.RequestException as e:
                    continue
            
            # 중복 제거 (같은 비디오가 여러 검색어에서 나올 수 있음)
            unique_videos = []
            seen_ids = set()
            
            for video in category_videos:
                if video["video_id"] not in seen_ids:
                    seen_ids.add(video["video_id"])
                    unique_videos.append(video)
            
            # 최종 결과 저장
            all_videos_by_category[category["id"]] = {
                "category_name": category["name"],
                "videos": unique_videos[:max_results_per_category]  # 카테고리당 최대 비디오 수 제한
            }
            
        return all_videos_by_category

    def get_transcript(self, video_id):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["ko", "en"])
            if not transcript:
                raise HTTPException(status_code=404, detail="자막이 없습니다.")
            return " ".join([entry["text"] for entry in transcript])
        except (NoTranscriptFound, TranscriptsDisabled) as e:
            raise HTTPException(status_code=404, detail="자막을 사용할 수 없습니다.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"자막 처리 중 오류 발생: {str(e)}")