from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from youtube_service import YouTubeService
from summary_service import SummaryService
from job_service import JobService
from d_job_service import DisabilityJobService
from fastapi import HTTPException  
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from d_sup import scrape_data

import logging
import threading
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 초기화
YOUTUBE_API_KEY = "AIzaSyBqmqqFslgj9ktmWrQmmkuCgk4-p469u84"
OPENAI_API_KEY = "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"


# 서비스 초기화
try:
    youtube_service = YouTubeService(YOUTUBE_API_KEY)
    summary_service = SummaryService(OPENAI_API_KEY)
    job_service = JobService()
    disability_job_service = DisabilityJobService()
    
    logger.info("서비스 초기화 완료")
except Exception as e:
    logger.error(f"서비스 초기화 중 오류 발생: {str(e)}")
    raise

@app.get("/search")
async def search_videos(keyword: str):
    try:
        logger.info(f"영상 검색 시작: {keyword}")
        results = youtube_service.search_youtube_videos(keyword)
        logger.info(f"검색 결과 수: {len(results)}")
        return results
    except Exception as e:
        logger.error(f"검색 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search-categories")
async def search_videos_by_category(keyword: str, max_results_per_category: int = Query(3, ge=1, le=10)):
    """
    키워드를 기반으로 카테고리별 YouTube 영상을 검색합니다.
    각 카테고리는 '장단점', '준비방법', '후기'로 분류됩니다.
    """
    try:
        logger.info(f"카테고리별 영상 검색 시작: {keyword}")
        results = youtube_service.search_youtube_videos_by_category(keyword, max_results_per_category)
        logger.info(f"카테고리별 검색 완료")
        return results
    except Exception as e:
        logger.error(f"카테고리별 검색 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transcript/{video_id}")
async def get_video_transcript(
    video_id: str,
    keyword: str = Query(None, description="원본 검색 키워드"),
    category: str = Query(None, description="비디오 카테고리")
):
    try:
        logger.info(f"트랜스크립트 요청 - Video ID: {video_id}, Keyword: {keyword}, Category: {category}")
        
        # 비디오 정보 가져오기
        video_info = youtube_service.get_video_info(video_id, keyword, category)
        logger.info(f"비디오 정보 retrieved: {video_info['title']}")
        
        # 트랜스크립트 가져오기
        transcript = youtube_service.get_transcript(video_id)
        logger.info(f"트랜스크립트 길이: {len(transcript) if transcript else 0}")
        
        if not transcript:
            raise HTTPException(status_code=404, detail="자막을 찾을 수 없습니다.")
        
        # 요약을 위한 컨텍스트 생성
        summary_context = {
            "title": video_info["title"],
            "keyword": keyword or video_info.get("search_keyword", "")
        }
        
        # 요약 생성
        summary = summary_service.summarize(transcript, summary_context)
        if not summary:
            raise HTTPException(status_code=500, detail="요약 생성 실패")
            
        logger.info("요약 생성 완료")
        
        return {
            "transcript": summary,
            "video_info": video_info
        }
    except HTTPException as he:
        logger.error(f"HTTP 오류: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"트랜스크립트 처리 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/compare-category")
async def compare_videos(request_data: dict):
    """
    여러 비디오의 자막을 비교하여 분석합니다.
    """
    try:
        logger.info("비디오 비교 분석 시작")
        
        video_data_list = request_data.get("video_data_list", [])
        category_name = request_data.get("category_name", "비디오 비교")
        
        if not video_data_list or len(video_data_list) == 0:
            raise HTTPException(status_code=400, detail="비교할 비디오가 없습니다.")
        
        # 각 비디오에 대해 트랜스크립트 가져오기
        for video_data in video_data_list:
            video_id = video_data.get("video_id")
            if not video_id:
                continue
                
            try:
                # 트랜스크립트 가져오기
                transcript = youtube_service.get_transcript(video_id)
                if transcript:
                    video_data["transcript"] = transcript
                    print(transcript)
                
                # 비디오 정보 가져오기 (이미 있으면 생략)
                if not video_data.get("video_info"):
                    video_info = youtube_service.get_video_info(
                        video_id, 
                        video_data.get("keyword"), 
                        video_data.get("category")
                    )
                    video_data["video_info"] = video_info
            except Exception as e:
                logger.warning(f"비디오 {video_id} 처리 중 오류: {str(e)}")
        
        # 비교 요약 생성
        comparison_result = summary_service.summarize_multiple_videos(video_data_list, category_name)
        print('비교요약결과')
        print(comparison_result)
        
        logger.info("비디오 비교 분석 완료")
        return {
            "comparison": comparison_result,
            "video_count": len([v for v in video_data_list if v.get("transcript")])
        }
        
    except HTTPException as he:
        logger.error(f"HTTP 오류: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"비디오 비교 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs")
async def get_jobs(keyword: str):
    try:
        logger.info(f"채용 정보 검색 시작: {keyword}")
        job_listings = job_service.get_job_listings(keyword)
        return JSONResponse(content={"jobs": job_listings})
    except Exception as e:
        logger.error(f"채용 정보 검색 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/disability-jobs")
async def get_disability_jobs(keyword: str):
    try:
        logger.info(f"장애인 채용 정보 검색 시작: {keyword}")
        jobs = disability_job_service.get_disability_jobs(keyword)
        return JSONResponse(content={"jobs": jobs})
    except Exception as e:
        logger.error(f"장애인 채용 정보 검색 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/disability-search")
async def search_disability_videos(keyword: str):
    try:
        logger.info(f"장애인 관련 영상 검색 시작: {keyword}")
        youtube_service.set_disability_search(True)
        result = youtube_service.search_youtube_videos_by_category(keyword)
        youtube_service.set_disability_search(False)
        return result
    except Exception as e:
        logger.error(f"장애인 관련 영상 검색 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/disability-category-search")
async def search_disability_videos_by_category(keyword: str, max_results_per_category: int = Query(3, ge=1, le=10)):
    """
    장애인 관련 키워드를 기반으로 카테고리별 YouTube 영상을 검색합니다.
    """
    try:
        logger.info(f"장애인 관련 카테고리별 영상 검색 시작: {keyword}")
        youtube_service.set_disability_search(True)
        result = youtube_service.search_youtube_videos_by_category(keyword, max_results_per_category)
        youtube_service.set_disability_search(False)
        return result
    except Exception as e:
        logger.error(f"장애인 관련 카테고리별 영상 검색 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# 크롤링 진행 상태 변수 추가
crawl_status = {
    "progress": 0,
    "status": "대기 중",
    "completed": False,
    "data": []  # 실제 데이터를 저장할 곳
}

# 진행 상태 업데이트 콜백 함수
def update_progress(percent, message):
    global crawl_status
    crawl_status["progress"] = percent
    crawl_status["status"] = message
    if percent == 100 or percent == -1:  # 완료 또는 오류
        crawl_status["completed"] = True

# 실제 크롤링 작업을 수행하는 백그라운드 태스크
def crawl_task():
    global crawl_status
    try:
        # 진행 상황 초기화
        crawl_status["progress"] = 0
        crawl_status["status"] = "크롤링 시작"
        crawl_status["completed"] = False
        crawl_status["data"] = []
        
        # 실제 크롤링 함수 호출 - 진행 콜백 전달
        data = scrape_data(progress_callback=update_progress)
        
        # 데이터 저장
        crawl_status["data"] = data
        
        # 완료 처리 (scrape_data에서 이미 100%로 설정했을 수 있음)
        if crawl_status["progress"] != 100:
            crawl_status["progress"] = 100
            crawl_status["status"] = "크롤링 완료"
            crawl_status["completed"] = True
            
    except Exception as e:
        logger.error(f"크롤링 작업 중 오류: {str(e)}")
        crawl_status["status"] = f"오류 발생: {str(e)}"
        crawl_status["progress"] = -1
        crawl_status["completed"] = True

# 크롤링 진행 상황 엔드포인트
@app.get("/crawl-progress")
def get_crawl_progress():
    return crawl_status

# 크롤링 데이터 엔드포인트 - 진행 중인 데이터 또는 완료된 데이터 반환
@app.get("/crawl-data")
def get_crawl_data():
    return {"data": crawl_status["data"]}

# 크롤링 시작 엔드포인트
@app.post("/start-crawling")
def start_crawling(background_tasks: BackgroundTasks):
    # 이미 진행 중인지 확인
    if crawl_status["progress"] > 0 and not crawl_status["completed"]:
        return {"message": "이미 크롤링이 진행 중입니다."}
    
    # 백그라운드 태스크 시작
    background_tasks.add_task(crawl_task)
    return {"message": "크롤링을 시작했습니다."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)