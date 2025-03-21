from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class JobService:
    def get_job_listings(self, keyword: str):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=options)
        try:
            url = "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do"
            print(f"[INFO] 접속 중: {url}")
            driver.get(url)

            try:
                search_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#srcKeyword"))
                )
                search_box.send_keys(keyword)
            except Exception as e:
                print(f"[ERROR] 검색창 요소 로드 실패: {e}")
                return []

            try:
                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "btn.large.type01.fill.wd180px"))
                )
                driver.execute_script("arguments[0].click();", search_button)
            except Exception as e:
                print(f"[ERROR] 검색 버튼 클릭 실패: {e}")
                return []

            all_data = []
            page_index = 2

            while True:
                try:
                    WebDriverWait(driver, 10).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.blockUI.blockOverlay"))
                    )
                    
                    results_table = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "box_table.type_pd24"))
                    )
                    
                    rows = results_table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        row_id = row.get_attribute("id")
                        if not row_id:
                            continue

                        columns = row.find_elements(By.TAG_NAME, "td")
                        data = [col.text.strip() for col in columns]
                        
                        location = "위치 정보 없음"
                        if len(data) > 1:
                            position_info = data[1].split('\n')
                            if len(position_info) > 3:
                                location = position_info[-1]
                                data[1] = '\n'.join(position_info[:-1])
                        
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

                    next_buttons = driver.find_elements(By.XPATH, f"//*[@id='mForm']/div[2]/div/div[2]/div/div/div/button[{page_index}]")
                    if not next_buttons:
                        print("[INFO] 마지막 페이지 도달")
                        break

                    driver.execute_script("arguments[0].click();", next_buttons[0])
                    page_index += 1
                    time.sleep(2)
                except Exception as e:
                    print(f"[ERROR] 크롤링 중 오류 발생: {e}")
                    break

            print(f"[INFO] 총 {len(all_data)}개의 채용 공고 수집 완료!")
            return all_data
        finally:
            driver.quit()