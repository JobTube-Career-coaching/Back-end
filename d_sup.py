from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
crawl_status_disabled = {
    "progress": 0,
    "status": "대기 중",
    "completed": False,
    "data": []  # 실제 데이터를 저장할 곳
}

def update_progress_disabled(percent, message):
    global crawl_status_disabled
    crawl_status_disabled["progress"] = percent
    crawl_status_disabled["status"] = message
    if percent == 100 or percent == -1:
        crawl_status_disabled["completed"] = True
def truncate_text(text, max_len=30):
    return text[:max_len] + "..." if len(text) > max_len else text

def scrape_data_disabled(progress_callback=None, target_url=None):
    driver = None
    data = []
    try:
        if progress_callback:
            progress_callback(5, "웹드라이버 초기화 중...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        
        if progress_callback:
            progress_callback(15, "웹페이지 접속 중...")
        # target_url가 없으면 기본 URL 사용
        if not target_url:
            target_url = "https://www.work24.go.kr/wk/a/b/1500/empList.do?searchMode=Y"
        driver.get(target_url)
        
        if progress_callback:
            progress_callback(30, "페이지 로딩 중...")
        time.sleep(5)
        
        if progress_callback:
            progress_callback(50, "HTML 분석 중...")
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # 실제 공고 데이터를 담고 있는 행 선택 (id가 'list'로 시작)
        rows = soup.select("tr[id^='list']")
        logger.info(f"발견된 행 수: {len(rows)}")
        
        if len(rows) == 0:
            logger.error("공고 데이터 행을 찾을 수 없습니다.")
            if progress_callback:
                progress_callback(100, "데이터를 찾을 수 없음")
            return []
        
        if progress_callback:
            progress_callback(70, "데이터 추출 중...")
        for i, row in enumerate(rows):
            try:
                company_tag = row.select_one("a.cp_name")
                title_tag = row.select_one("a.t3_sb")
                if not title_tag:
                    logger.warning(f"{i+1}번 행에 제목 태그가 없습니다.")
                    continue
                company = company_tag.text.strip() if company_tag else "회사 정보 없음"
                title = title_tag.text.strip()
                link = title_tag.get("href")
                full_link = f"https://www.work24.go.kr{link}" if link else None
                logger.info(f"[{i+1}] {title} | {company} | {full_link}")
                data.append({
                    "category": "공고",
                    "title": truncate_text(title, 50),
                    "institution": truncate_text(company, 50),
                    "link": full_link
                })
                if progress_callback:
                    current_progress = 70 + int((i+1)/len(rows)*20)
                    progress_callback(current_progress, f"데이터 {i+1}/{len(rows)} 처리 중...")
            except Exception as e:
                logger.error(f"{i+1}번 행 처리 중 오류: {e}")
                continue
        
        if progress_callback:
            progress_callback(95, "웹드라이버 정리 중...")
        driver.quit()
        if progress_callback:
            progress_callback(100, f"크롤링 완료 - {len(data)}개 항목 찾음")
        logger.info(f"크롤링 완료 - {len(data)}개 항목 찾음")
        return data
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")
        if progress_callback:
            progress_callback(-1, f"오류 발생: {e}")
        try:
            if driver:
                driver.quit()
        except:
            pass
        return []

def crawl_task_disabled():
    global crawl_status_disabled
    try:
        crawl_status_disabled["progress"] = 0
        crawl_status_disabled["status"] = "크롤링 시작"
        crawl_status_disabled["completed"] = False
        crawl_status_disabled["data"] = []

        data = scrape_data_disabled(progress_callback=update_progress_disabled)
        crawl_status_disabled["data"] = data

        if crawl_status_disabled["progress"] != 100:
            crawl_status_disabled["progress"] = 100
            crawl_status_disabled["status"] = "크롤링 완료"
            crawl_status_disabled["completed"] = True
    except Exception as e:
        logger.error(f"크롤링 작업 중 오류: {str(e)}")
        crawl_status_disabled["status"] = f"오류 발생: {str(e)}"
        crawl_status_disabled["progress"] = -1
        crawl_status_disabled["completed"] = True


# 모드 id에 따른 URL 매핑 (총 8개)
d_mode_url_mapping = {
    1: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=10&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EA%B2%BD%EB%B9%84%7C%EB%B3%B4%EC%95%88%7C%EC%95%88%EC%A0%84&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=Y%2CD&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EA%B2%BD%EB%B9%84%7C%EB%B3%B4%EC%95%88%7C%EC%95%88%EC%A0%84&academicGbnoEdu=noEdu&enterPriseGbn=&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    2: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=10&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EA%B2%BD%EB%B9%84%7C%EB%B3%B4%EC%95%88%7C%EC%95%88%EC%A0%84&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=Y%2CD&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EB%8F%8C%EB%B4%84%7C%EB%B3%B5%EC%A7%80%7C%EA%B5%90%EC%9C%A1&academicGbnoEdu=noEdu&enterPriseGbn=&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    3: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=10&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EB%8F%8C%EB%B4%84%7C%EB%B3%B5%EC%A7%80%7C%EA%B5%90%EC%9C%A1&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=Y%2CD&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EC%9A%B4%EC%A0%84%7C%EB%B0%B0%EC%86%A1%7C%EC%9D%B4%EB%8F%99&academicGbnoEdu=noEdu&enterPriseGbn=&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    4: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=10&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EC%9A%B4%EC%A0%84%7C%EB%B0%B0%EC%86%A1%7C%EC%9D%B4%EB%8F%99&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=Y%2CD&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EC%B2%AD%EC%86%8C%7C%ED%99%98%EA%B2%BD%7C%EB%AF%B8%ED%99%94&academicGbnoEdu=noEdu&enterPriseGbn=&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    5: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=10&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EC%B2%AD%EC%86%8C%7C%ED%99%98%EA%B2%BD%7C%EB%AF%B8%ED%99%94&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=Y%2CD&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EC%83%9D%EC%82%B0%7C%EA%B8%B0%EC%88%A0%7C%EC%A0%9C%EC%A1%B0+%EB%B3%B4%EC%A1%B0&academicGbnoEdu=noEdu&enterPriseGbn=&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    6: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=10&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EC%83%9D%EC%82%B0%7C%EA%B8%B0%EC%88%A0%7C%EC%A0%9C%EC%A1%B0+%EB%B3%B4%EC%A1%B0&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=Y%2CD&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%EC%82%AC%EB%AC%B4%7C%ED%96%89%EC%A0%95%7C%EA%B3%A0%EA%B0%9D+%EC%9D%91%EB%8C%80&academicGbnoEdu=noEdu&enterPriseGbn=&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    7: "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?basicSetupYn=&careerTo=&keywordJobCd=&occupation=&seqNo=&cloDateEndtParam=&payGbn=&templateInfo=&rot2WorkYn=&shsyWorkSecd=&resultCnt=10&keywordJobCont=Y&cert=&moreButtonYn=Y&minPay=&codeDepth2Info=11000&currentPageNo=1&eventNo=&mode=&major=&resrDutyExcYn=&eodwYn=&sortField=DATE&staArea=&sortOrderBy=DESC&keyword=%EC%82%AC%EB%AC%B4%7C%ED%96%89%EC%A0%95%7C%EA%B3%A0%EA%B0%9D+%EC%9D%91%EB%8C%80&termSearchGbn=&carrEssYns=&benefitSrchAndOr=O&disableEmpHopeGbn=Y%2CD&actServExcYn=&keywordStaAreaNm=&maxPay=&emailApplyYn=&codeDepth1Info=11000&keywordEtcYn=&regDateStdtParam=&publDutyExcYn=&keywordJobCdSeqNo=&viewType=&exJobsCd=&templateDepthNmInfo=&region=&employGbn=&empTpGbcd=1&computerPreferential=&infaYn=&cloDateStdtParam=&siteClcd=all&searchMode=Y&birthFromYY=&indArea=&careerTypes=&subEmpHopeYn=&tlmgYn=&academicGbn=&templateDepthNoInfo=&foriegn=&entryRoute=&mealOfferClcd=&basicSetupYnChk=&station=&holidayGbn=&srcKeyword=%ED%8C%90%EB%A7%A4%7C%EC%84%9C%EB%B9%84%EC%8A%A4%EC%97%85&academicGbnoEdu=noEdu&enterPriseGbn=&cloTermSearchGbn=&birthToYY=&keywordWantedTitle=Y&stationNm=&benefitGbn=&keywordFlag=&notSrcKeyword=&essCertChk=&depth2SelCode=&keywordBusiNm=&preferentialGbn=&rot3WorkYn=&regDateEndtParam=&pfMatterPreferential=&pageIndex=1&termContractMmcnt=&careerFrom=&laborHrShortYn=#scrollLoc",
    8: "",
}