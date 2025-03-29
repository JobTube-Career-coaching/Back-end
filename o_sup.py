from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import re
from uuid import uuid4

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


crawl_status_senior_map = {}  # task_id: status dict
def create_new_status():
    return {
        "progress": 0,
        "status": "대기 중",
        "completed": False,
        "data": []
    }
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_progress_senior(task_id, percent, message):
    status = crawl_status_senior_map.get(task_id)
    if status:
        status["progress"] = percent
        status["status"] = message
        if percent == 100 or percent == -1:
            status["completed"] = True

def truncate_text(text, max_len=30):
    return text[:max_len] + "..." if len(text) > max_len else text
def scrape_data_senior(progress_callback=None, target_url=None, max_pages=10):
    driver = None
    data = []

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=options)
        all_data = []
        
        try:
            driver.get(target_url)
            
            
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

    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")
        if progress_callback:
            progress_callback(-1, f"오류 발생: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return data


# crawl_task_senior 정의를 start-crawling-senior 보다 먼저! 
def crawl_task_senior():
    global crawl_status_senior
    try:
        crawl_status_senior["progress"] = 0
        crawl_status_senior["status"] = "크롤링 시작"
        crawl_status_senior["completed"] = False
        crawl_status_senior["data"] = []

        data = scrape_data_senior(progress_callback=update_progress_senior)
        crawl_status_senior["data"] = data

        if crawl_status_senior["progress"] != 100:
            crawl_status_senior["progress"] = 100
            crawl_status_senior["status"] = "크롤링 완료"
            crawl_status_senior["completed"] = True
    except Exception as e:
        logger.error(f"크롤링 작업 중 오류: {str(e)}")
        crawl_status_senior["status"] = f"오류 발생: {str(e)}"
        crawl_status_senior["progress"] = -1
        crawl_status_senior["completed"] = True


# 모드 id에 따른 URL 매핑 (총 8개)
o_mode_url_mapping = {
    1: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=1000&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EA%B2%BD%EB%B9%84%7C%EB%B3%B4%EC%95%88%7C%EC%95%88%EC%A0%84&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EA%B2%BD%EB%B9%84%7C%EB%B3%B4%EC%95%88%7C%EC%95%88%EC%A0%84&academicGbnoEdu=noEdu&enterPriseGbn=all&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=B&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    2: ("https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=1000&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EB%8F%8C%EB%B4%84%7C%EB%B3%B5%EC%A7%80&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EB%8F%8C%EB%B4%84%7C%EB%B3%B5%EC%A7%80&academicGbnoEdu=noEdu&enterPriseGbn=all&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=%EB%AF%B8%ED%99%94%2C%ED%99%98%EA%B2%BD%2C%EA%B2%BD%EB%B9%84&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=B&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc"),
    3: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=1000&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EC%9A%B4%EC%A0%84%7C%EB%B0%B0%EC%86%A1%7C%EC%9D%B4%EB%8F%99&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EC%9A%B4%EC%A0%84%7C%EB%B0%B0%EC%86%A1%7C%EC%9D%B4%EB%8F%99&academicGbnoEdu=noEdu&enterPriseGbn=all&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=%EC%9A%94%EC%96%91%2C%EB%AF%B8%ED%99%94%2C%ED%99%98%EA%B2%BD&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=B&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",  # 운전/배송/이동
    4:"https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=1000&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%ED%99%98%EA%B2%BD%7C%EB%AF%B8%ED%99%94%7C%EC%B2%AD%EC%86%8C&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%ED%99%98%EA%B2%BD%7C%EB%AF%B8%ED%99%94%7C%EC%B2%AD%EC%86%8C&academicGbnoEdu=noEdu&enterPriseGbn=all&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=%EC%9A%94%EC%96%91&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=B&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    5: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=1000&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EC%83%9D%EC%82%B0%7C%EA%B8%B0%EC%88%A0%7C%EC%A0%9C%EC%A1%B0&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EC%83%9D%EC%82%B0%7C%EA%B8%B0%EC%88%A0%7C%EC%A0%9C%EC%A1%B0&academicGbnoEdu=noEdu&enterPriseGbn=all&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=B&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    6: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=1000&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EC%82%AC%EB%AC%B4%7C%ED%96%89%EC%A0%95%7C%28%EA%B3%A0%EA%B0%9D+%EC%9D%91%EB%8C%80%29&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EC%82%AC%EB%AC%B4%7C%ED%96%89%EC%A0%95%7C%28%EA%B3%A0%EA%B0%9D+%EC%9D%91%EB%8C%80%29&academicGbnoEdu=noEdu&enterPriseGbn=all&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=B&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    7: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=1000&keywordJobCont=&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%ED%8C%90%EB%A7%A4&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%ED%8C%90%EB%A7%A4&academicGbnoEdu=noEdu&enterPriseGbn=all&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=B&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    8: "",
}