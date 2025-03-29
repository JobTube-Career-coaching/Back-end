from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from fastapi import HTTPException
import time
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisabilityJobService:
    def __init__(self):
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--window-size=1920,1080")
        self.base_url = "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do"

    def _setup_driver(self):
        try:
            return webdriver.Chrome(options=self.options)
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to initialize web driver")

    def _wait_for_element(self, driver, by, value, timeout=10):
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {value}")
            return None

    def _wait_for_clickable(self, driver, by, value, timeout=20):
        try:
            return WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for clickable element: {value}")
            return None

    def _process_job_row(self, row) -> Dict:
        try:
            row_id = row.get_attribute("id")
            if not row_id:
                return None

            columns = row.find_elements(By.TAG_NAME, "td")
            data = [col.text.strip() for col in columns]
            
            location = "위치 정보 없음"
            if len(data) > 1:
                position_info = data[1].split('\n')
                if len(position_info) > 3:
                    location = position_info[-1]
                    data[1] = '\n'.join(position_info[:-1])

            links = row.find_elements(By.TAG_NAME, "a")
            detail_link = next((a.get_attribute("href") for a in links if a.get_attribute("href")), "없음")

            return {
                "id": row_id,
                "data": data,
                "second_link": detail_link,
                "source": "worknet",
                "location": location,
                "is_disability_posting": True
            }
        except Exception as e:
            logger.error(f"Error processing job row: {str(e)}")
            return None

    def _perform_search(self, driver, keyword: str) -> bool:
        try:
            search_box = self._wait_for_clickable(driver, By.CSS_SELECTOR, "#srcKeyword")
            if not search_box:
                raise HTTPException(status_code=500, detail="Search box not found")
            
            search_box.clear()
            search_box.send_keys(keyword)

            disability_checkbox = self._wait_for_clickable(driver, By.XPATH, '//*[@id="disableEmpHopeGbnParamY"]')
            if disability_checkbox:
                driver.execute_script("arguments[0].click();", disability_checkbox)

            search_button = self._wait_for_clickable(driver, By.CLASS_NAME, "btn.large.type01.fill.wd180px")
            if not search_button:
                raise HTTPException(status_code=500, detail="Search button not found")
            
            driver.execute_script("arguments[0].click();", search_button)
            time.sleep(2)  
            
            return True
        except Exception as e:
            logger.error(f"Error performing search: {str(e)}")
            return False

    def get_disability_jobs(self, keyword: str) -> List[Dict]:
        driver = None
        try:
            driver = self._setup_driver()
            driver.get(self.base_url)
            
            more_btn = self._wait_for_clickable(driver, By.XPATH, '//*[@id="moreBtn"]')
            if more_btn:
                driver.execute_script("arguments[0].click();", more_btn)
                time.sleep(1)

            if not self._perform_search(driver, keyword):
                return []

            all_data = []
            page_index = 2

            while True:
                try:
                    WebDriverWait(driver, 10).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.blockUI.blockOverlay"))
                    )

                    results_table = self._wait_for_element(driver, By.CLASS_NAME, "box_table.type_pd24")
                    if not results_table:
                        break

                    rows = results_table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        job_data = self._process_job_row(row)
                        if job_data:
                            all_data.append(job_data)

                    next_buttons = driver.find_elements(By.XPATH, f"//*[@id='mForm']/div[2]/div/div[2]/div/div/div/button[{page_index}]")
                    
                    if not next_buttons:
                        break
                        
                    driver.execute_script("arguments[0].click();", next_buttons[0])
                    page_index += 1
                    time.sleep(2)

                except TimeoutException:
                    logger.warning("Timeout occurred while processing page")
                    break
                except Exception as e:
                    logger.error(f"Error processing page: {str(e)}")
                    break

            return all_data

        except Exception as e:
            logger.error(f"General error in get_disability_jobs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

        finally:
            if driver:
                driver.quit()
