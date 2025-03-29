from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import re

def preprocess_job_data(data):
    """
    전체 데이터를 한 줄로 합친 후, 유의미한 정보를 분리하여 반환.
    """
    processed_data = []

    item=" ".join(data)
    company_match = data[0].split("\n")[0]
    title=""
    if data[0].split("\n")[2]=="고용24 입사지원 가능":
        title= " ".join(data[0].split("\n")[1:2])
    else:
        title=data[0].split("\n")[1]
    # 줄바꿈을 스페이스로 변환
    combined_text = item.replace("\n", " ")

    # 회사명, 급여, 근로 조건, 마감일 추출하기 위한 정규식 패턴
    #cond= #경력/학력
    salary_match = re.search(r"월급 (\d+)\s?만원", combined_text)
    work_conditions_match = re.search(r"주(\d)일", combined_text)
    work_hours_match = re.search(r"주 (\d+)시간", combined_text)
    deadline_match = re.search(r"마감일 : (\d{4}-\d{2}-\d{2})", combined_text)

    # 회사명 (없으면 '회사 정보 없음'으로 처리)
    company = company_match if company_match else "회사 정보 없음"

    # 급여 (없으면 '급여 정보 없음'으로 처리)
    salary = salary_match.group(1) if salary_match else "급여 정보 없음"

    # 근로 조건 (없으면 '근로 조건 정보 없음'으로 처리)
    work_conditions = work_conditions_match.group(1) if work_conditions_match else "근로 조건 정보 없음"

    # 근로 시간 (없으면 '근로 시간 정보 없음'으로 처리)
    work_hours = work_hours_match.group(1) if work_hours_match else "근로 시간 정보 없음"

    # 마감일 (없으면 '마감일 정보 없음'으로 처리)
    deadline = deadline_match.group(1) if deadline_match else "채용시까지" 

    # 처리된 데이터 추가
    processed_data.append({
        "company": company.strip(),
        "salary": salary.strip(),
        "work_conditions": work_conditions.strip(),
        "work_hours": work_hours.strip(),
        "deadline": deadline.strip(),
        "title" :title.strip()
    })

    return processed_data


class Old_JobService:
   
    def get_job_listings_senior(self,url: str, keyword: str):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=options)
        all_data = []
        
        try:
            driver.get(url)
            
            # 검색 입력란이 나타날 때까지 대기 후 키워드 입력
            search_box = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#srcKeyword"))
            )
            search_box.send_keys(keyword)
            
            # 블록 오버레이가 사라질 때까지 대기
            WebDriverWait(driver, 10).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.blockUI.blockOverlay"))
            )
            
            # 페이지 번호 1부터 10까지 루프
            for current_page in range(1, 11):
                try:
                    # 결과 테이블이 로드될 때까지 대기
                    results_table = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "box_table.type_pd24"))
                    )
                    
                    rows = results_table.find_elements(By.TAG_NAME, "tr")
                    if not rows:
                        logger.info(f"페이지 {current_page}: 데이터 행이 없습니다. 루프 종료")
                        break

                    # 각 행의 데이터를 처리하여 all_data에 추가
                    for row in rows:
                        row_id = row.get_attribute("id")
                        if not row_id:
                            continue
                        columns = row.find_elements(By.TAG_NAME, "td")
                        data = [col.text.strip() for col in columns]
                        
                        # 위치 정보 예시 처리 (필요 시 수정)
                        location = "위치 정보 없음"
                        if len(data) > 1:
                            position_info = data[1].split('\n')
                            if len(position_info) > 3:
                                location = position_info[-1]
                                data[1] = '\n'.join(position_info[:-1])
                        
                        # 링크 추출
                        links = [a.get_attribute("href") for a in row.find_elements(By.TAG_NAME, "a") if a.get_attribute("href")]
                        second_link = links[1] if len(links) > 1 else "없음"
                        
                        job_data = {
                            "id": row_id,
                            "data": data,
                            "second_link": second_link,
                            "source": "worknet",
                            "location": location
                        }
                        all_data.append(job_data)
                    
                    logger.info(f"페이지 {current_page} 크롤링 완료. 데이터 수: {len(all_data)}")
                    
                    # 다음 페이지 버튼을 클릭하여 이동
                    next_page = current_page + 1
                    next_button_xpath = f"//*[@id='mForm']/div[2]/div/div[2]/div/div/div/button[{next_page}]"
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, next_button_xpath))
                    )
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(2)  # 페이지 전환 대기

                except Exception as page_e:
                    logger.error(f"페이지 {current_page} 처리 중 오류 발생: {page_e}. 루프 중단.")
                    break
            for datas in range(len(all_data)):
                all_data[datas]["data"]= preprocess_job_data(all_data[datas]["data"])
            return all_data

        finally:
            driver.quit()