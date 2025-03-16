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
            driver.get(url)

            search_box = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#srcKeyword"))
            )
            search_box.send_keys(keyword)

            WebDriverWait(driver, 10).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.blockUI.blockOverlay"))
            )

            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "btn.medium.type01.ht100per.fill"))
            )
            driver.execute_script("arguments[0].click();", search_button)

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

                    try:
                        WebDriverWait(driver, 10).until_not(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.blockUI.blockOverlay"))
                        )

                        next_button_xpath = f"//*[@id='mForm']/div[2]/div/div[2]/div/div/div/button[{page_index}]"
                        next_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, next_button_xpath))
                        )
                        driver.execute_script("arguments[0].click();", next_button)
                        page_index += 1
                        time.sleep(2)
                    except:
                        break

                except Exception as e:
                    print(f"Error occurred: {str(e)}")
                    break

            return all_data

        finally:
            driver.quit()