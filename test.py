import requests
from bs4 import BeautifulSoup

class JobService:
    def get_job_listings(self, keyword: str):
        url = "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        data = {
            "srcKeyword": keyword,
            "pageIndex": 1  # 첫 페이지부터 시작
        }

        response = requests.post(url, headers=headers, data=data)
        if response.status_code != 200:
            print("❌ 요청 실패:", response.status_code)
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # ✅ 채용 공고 목록 찾기
        job_rows = soup.select(".box_table.type_pd24 tr")  # 테이블의 각 행 선택
        all_data = []

        for row in job_rows:
            columns = row.find_all("td")
            if len(columns) < 2:
                continue  # 데이터가 없는 경우 스킵

            # ✅ 직무명
            title = columns[0].get_text(strip=True) or "정보 없음"

            # ✅ 회사명 + 위치 (구분자 '\n'이 있을 수 있음)
            company_info = columns[1].get_text("\n", strip=True).split("\n")
            company = company_info[0] if len(company_info) > 0 else "회사 정보 없음"
            location = company_info[-1] if len(company_info) > 1 else "위치 정보 없음"

            # ✅ 상세 페이지 링크 추출
            link_tag = columns[0].find("a")
            job_link = link_tag["href"] if link_tag else "없음"

            job_data = {
                "title": title,
                "company": company,
                "location": location,
                "link": f"https://www.work24.go.kr{job_link}" if job_link != "없음" else "없음"
            }
            all_data.append(job_data)

        # ✅ 검색 결과 출력
        for job in all_data[:5]:  # 최대 5개만 출력
            print(f"🔹 직무: {job['title']}")
            print(f"🏢 회사: {job['company']}")
            print(f"📍 위치: {job['location']}")
            print(f"🔗 상세 링크: {job['link']}")
            print("-" * 30)

        return all_data


# ✅ 실행 예제
service = JobService()
service.get_job_listings("소프트웨어 개발자")
