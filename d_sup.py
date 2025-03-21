from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 텍스트 길이 제한 함수
def truncate_text(text, max_len=30):
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text

def scrape_data(progress_callback=None):
    driver = None
    try:
        # 진행 상태 업데이트 (시작)
        if progress_callback:
            progress_callback(5, "웹드라이버 초기화 중...")
        
        logger.info("웹드라이버 초기화 중...")
        # 웹드라이버 설정 (Chrome 기준)
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # 브라우저 창 없이 실행
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)

        # 진행 상태 업데이트
        if progress_callback:
            progress_callback(15, "웹페이지 접속 중...")
        
        logger.info("웹페이지 접속 중...")
        # 웹페이지 열기
        url = "https://www.worktogether.or.kr/eduInfo/trainInfo/eduTrainInfoList.do"
        driver.get(url)

        # 진행 상태 업데이트
        if progress_callback:
            progress_callback(30, "페이지 로딩 중...")
        
        logger.info("페이지 로딩 중...")
        # 페이지 로딩 대기 - 더 긴 시간 기다리기
        time.sleep(5)

        # 진행 상태 업데이트
        if progress_callback:
            progress_callback(50, "HTML 분석 중...")
        
        logger.info("HTML 분석 중...")
        # 페이지 소스 가져오기
        html = driver.page_source
        
        # HTML 소스 로깅 (일부만)
        html_preview = html[:500] + "..." if len(html) > 500 else html
        logger.info(f"HTML 미리보기: {html_preview}")
        
        soup = BeautifulSoup(html, "html.parser")

        # 테이블 가져오기 - 더 유연한 선택자 사용
        table = soup.select_one("#content table")
        
        if not table:
            logger.error("테이블을 찾을 수 없습니다.")
            # 다른 테이블 선택자 시도
            tables = soup.select("table")
            logger.info(f"페이지에서 발견된 테이블 수: {len(tables)}")
            
            if tables:
                # 첫 번째 테이블 사용
                table = tables[0]
                logger.info("첫 번째 테이블을 대신 사용합니다.")
            else:
                if progress_callback:
                    progress_callback(100, "데이터를 찾을 수 없음")
                return []

        # 테이블 행 가져오기
        rows = table.select("tbody tr")
        logger.info(f"발견된 행 수: {len(rows)}")
        
        if len(rows) == 0:
            logger.error("테이블 행을 찾을 수 없습니다.")
            # 테이블 구조 로깅
            logger.info(f"테이블 HTML: {table}")
            
            # 대체 행 선택자 시도
            rows = table.select("tr")
            logger.info(f"대체 선택자로 발견된 행 수: {len(rows)}")
            
            if len(rows) == 0:
                if progress_callback:
                    progress_callback(100, "데이터를 찾을 수 없음")
                return []
        
        # 상위 행만 가져오기
        rows = rows[:6] if len(rows) > 5 else rows

        # 진행 상태 업데이트
        if progress_callback:
            progress_callback(70, "데이터 추출 중...")
        
        logger.info("데이터 추출 중...")
        data = []
        
        # 데이터 저장
        for i, row in enumerate(rows):
            try:
                # 각 열에서 필요한 값들 추출 - 더 안전한 접근
                cols = row.select("td")
                logger.info(f"행 {i+1} - 열 수: {len(cols)}")
                
                if len(cols) >= 4:  # 최소한 4개 이상의 열이 있어야 함
                    category = cols[1].text.strip() if cols[1].text else "분류 없음"
                    title = cols[2].text.strip() if cols[2].text else "제목 없음"
                    institution = cols[3].text.strip() if cols[3].text else "기관 없음"
                    
                    # 링크 추출 시도 - 좀 더 안전하게
                    link = None
                    try:
                        if cols[2].select_one("a"):
                            link = cols[2].select_one("a").get("href")
                    except Exception as e:
                        logger.error(f"링크 추출 중 오류: {str(e)}")
                    
                    logger.info(f"추출된 데이터: {category}, {title[:20]}..., {institution[:20]}...")
                    
                    # 데이터 추가
                    data.append({
                        "category": truncate_text(category),
                        "title": truncate_text(title),
                        "institution": truncate_text(institution),
                        "link": link
                    })
                else:
                    logger.warning(f"행 {i+1}에 충분한 열이 없습니다: {len(cols)}")
                    
                # 개별 항목 처리 진행률 업데이트
                if progress_callback and rows:
                    current_progress = 70 + int((i + 1) / len(rows) * 20)  # 70%에서 90%까지
                    progress_callback(current_progress, f"데이터 {i+1}/{len(rows)} 처리 중...")
            except Exception as e:
                logger.error(f"행 {i+1} 처리 중 오류: {str(e)}")
                # 특정 행 처리 실패해도 계속 진행
                continue
        
        # 진행 상태 업데이트 (완료)
        if progress_callback:
            progress_callback(95, "웹드라이버 정리 중...")
        
        logger.info("웹드라이버 정리 중...")
        # 드라이버 종료
        driver.quit()
        driver = None

        # 진행 상태 업데이트 (완전 완료)
        if progress_callback:
            progress_callback(100, f"크롤링 완료 - {len(data)}개 항목 찾음")
        
        logger.info(f"크롤링 완료 - {len(data)}개 항목 찾음")
        return data
        
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {str(e)}")
        if progress_callback:
            progress_callback(-1, f"오류 발생: {str(e)}")
        # 오류가 발생해도 드라이버를 종료하려고 시도
        try:
            if driver:
                driver.quit()
        except:
            pass
        # 빈 리스트 반환
        return []