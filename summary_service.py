import re
import openai
from fastapi import HTTPException
from bs4 import BeautifulSoup

class SummaryService:
    def __init__(self, openai_api_key):
        openai.api_key = openai_api_key

    def preprocess_payload(self, payload, max_length=1200):
        cleaned = re.sub(r'\s+', ' ', payload)
        cleaned = re.sub(r'[^\w\s.,!?()\'\"가-힣]', '', cleaned)
        sentences = re.split(r'(?<=[.!?]) +', cleaned)
        return " ".join(sentences[:max_length // 15]) if len(cleaned) > max_length else cleaned

    def summarize_multiple_videos(self, video_data_list, category_name):
        """여러 비디오의 자막을 비교하여 요약"""
        if not video_data_list or len(video_data_list) == 0:
            raise HTTPException(status_code=400, detail="요약할 비디오가 없습니다.")
        
        # 각 비디오 정보 및 자막 추출
        video_contents = []
        for video_data in video_data_list:
            transcript = video_data.get("transcript", "")
            if not transcript:
                continue
                
            video_info = video_data.get("video_info", {})
            
            # 트랜스크립트 전처리
            transcript = self.preprocess_payload(transcript, 1500)
            
            video_contents.append({
                "title": video_info.get("title", ""),
                "channel": video_info.get("channel", ""),
                "transcript": transcript[:1500],  # 길이 제한
                "url": video_info.get("url", "")
            })
        
        if len(video_contents) == 0:
            raise HTTPException(status_code=400, detail="유효한 자막이 있는 비디오가 없습니다.")
            
        try:
            # 비디오 컨텐츠를 기반으로 비교 요약 생성
            prompt = self._create_comparison_prompt(video_contents, category_name)
            
            messages = [
                {"role": "system", "content": (
                    "You are a detailed content analysis expert that identifies common themes and differences "
                    "across multiple content pieces. Provide a comprehensive, well-structured analysis in Korean "
                    "that highlights both shared information and unique perspectives."
                )},
                {"role": "user", "content": prompt}
            ]
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.5,
                max_tokens=1800
            )
            
            summary = response.choices[0].message.content.strip()
            return self.postprocess_summary(summary)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"비교 요약 중 오류 발생: {str(e)}")

    def _create_comparison_prompt(self, video_contents, category_name):
        """여러 비디오를 비교하는 프롬프트 생성"""
        videos_text = ""
        for i, content in enumerate(video_contents):
            videos_text += f"\n비디오 {i+1} 제목: {content['title']}\n"
            videos_text += f"채널: {content['channel']}\n"
            videos_text += f"내용: {content['transcript']}\n\n"
            
        return (
            f"다음은 '{category_name}'에 관한 {len(video_contents)}개의 YouTube 영상 자막입니다. "
            "이 영상들의 내용을 비교 분석하여 공통된 정보와 각 영상의 고유한 관점을 정리해주세요.\n\n"
            f"{videos_text}\n"
            "다음 HTML 구조로 정리해주세요:\n\n"
            "<div class='comparison-container'>\n"
            "  <section class='common-section'>\n"
            "    <h3 class='section-title'>공통된 정보</h3>\n"
            "    <div class='content-block'>\n"
            "      <p class='key-point'>여러 영상에서 공통적으로 언급하는 핵심 정보 1</p>\n"
            "      <p class='key-point'>여러 영상에서 공통적으로 언급하는 핵심 정보 2</p>\n"
            "      <p class='key-point'>여러 영상에서 공통적으로 언급하는 핵심 정보 3</p>\n"
            "    </div>\n"
            "  </section>\n"
            "  <section class='unique-section'>\n"
            "    <h3 class='section-title'>고유한 관점</h3>\n"
            "    <div class='content-block'>\n"
            "      <div class='video-perspective'>\n"
            "        <h4 class='video-title'>비디오 1 제목</h4>\n"
            "        <p class='unique-point'>이 영상만의 고유한 관점 1</p>\n"
            "        <p class='unique-point'>이 영상만의 고유한 관점 2</p>\n"
            "      </div>\n"
            "      <!-- 다른 비디오에 대해서도 반복 -->\n"
            "    </div>\n"
            "  </section>\n"
            "  <section class='conclusion-section'>\n"
            "    <h3 class='section-title'>종합 분석</h3>\n"
            "    <div class='content-block'>\n"
            "      <p class='conclusion-point'>여러 영상을 종합한 주요 결론 1</p>\n"
            "      <p class='conclusion-point'>여러 영상을 종합한 주요 결론 2</p>\n"
            "      <p class='conclusion-point'>여러 영상을 종합한 주요 결론 3</p>\n"
            "    </div>\n"
            "  </section>\n"
            "</div>\n\n"
            "요구사항:\n"
            "1. 각 섹션은 상세하게 작성하되, 중요한 정보에 집중해주세요.\n"
            "2. 공통된 정보는 모든 영상에서 언급된 핵심 내용을 포함해주세요.\n"
            "3. 고유한 관점은 각 영상별로 다른 영상과 차별화된 내용을 포함해주세요.\n"
            "4. 종합 분석은 모든 영상의 내용을 종합하여 전체적인 관점을 제시해주세요.\n"
            "5. 중요한 수치나 핵심 정보는 <b> 태그로 강조해주세요.\n"
            "6. HTML 코드 외의 메타설명은 포함하지 마세요."
        )

    def summarize(self, payload, context=None):
        """단일 비디오 요약(기존 기능)"""
        if not payload:
            raise HTTPException(status_code=400, detail="요약할 텍스트가 없습니다.")

        max_length = 1200
        payload = self.preprocess_payload(payload, max_length)
        chunks = [payload[i:i+max_length] for i in range(0, len(payload), max_length)]
        summaries = []

        try:
            for chunk in chunks:
                context_prompt = ""
                if context:
                    context_prompt = (
                        f"영상 제목: {context['title']}\n"
                        f"검색 키워드: {context['keyword']}\n"
                    )
                
                prompt = (
                    f"{context_prompt}"
                    "다음 텍스트의 내용을 상세하게 정리하여 아래 HTML 구조로 작성해주세요:\n\n"
                    "<div class='summary-container'>\n"
                    "  <section class='summary-section'>\n"
                    "    <h3 class='section-title'>주요 맥락과 배경</h3>\n"
                    "    <div class='content-block'>\n"
                    "      <p class='main-point'>핵심 주제와 배경 (2-3문장)</p>\n"
                    "      <p class='detail-point'>구체적인 상황 설명 (2-3문장)</p>\n"
                    "      <p class='supporting-info'>관련된 맥락과 추가 정보 (2-3문장)</p>\n"
                    "    </div>\n"
                    "  </section>\n"
                    "  <!-- 위 구조로 총 3개 섹션 작성 -->\n"
                    "</div>\n\n"
                    "요구사항:\n"
                    "1. 정확히 3개의 섹션으로 구성 (주요 맥락/핵심 내용/결론)\n"
                    "2. 각 섹션은 반드시 3개의 단락으로 구성\n"
                    "3. 각 단락은 최소 2-3개의 완성된 문장으로 작성\n"
                    "4. 요약하지 말고 원문의 중요한 내용을 상세하게 포함\n"
                    "5. 중요한 수치는 <b> 태그로 강조\n"
                    "6. 메타설명이나 불필요한 설명 제외\n\n"
                    f"텍스트 내용:\n{chunk}"
                )

                messages = [
                    {"role": "system", "content": (
                        "You are a detailed content organization expert that creates "
                        "comprehensive, well-structured content in Korean. Include "
                        "sufficient detail and context while maintaining clear organization. "
                        "Each section should have three distinct paragraphs with "
                        "2-3 complete sentences each."
                    )},
                    {"role": "user", "content": prompt}
                ]
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.5,
                    max_tokens=1500
                )
                summary = response.choices[0].message.content.strip()
                summaries.append(summary)

            full_summary = "\n".join(summaries)
            return self.postprocess_summary(full_summary)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"요약 중 오류 발생: {str(e)}")

    def postprocess_summary(self, summary):
        css_style = """
        <style>
        .summary-container, .comparison-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: 'Noto Sans KR', sans-serif;
            line-height: 1.6;
            color: #333;
        }
        .summary-section, .common-section, .unique-section, .conclusion-section {
            margin-bottom: 35px;
            padding: 25px;
            background-color: #f8f9fa;
            border-radius: 12px;
            box-shadow: 0 3px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        .summary-section:hover, .common-section:hover, .unique-section:hover, .conclusion-section:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .section-title {
            color: #1a73e8;
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e8eaed;
            font-weight: 600;
        }
        .content-block {
            margin: 20px 0;
        }
        .main-point, .key-point, .conclusion-point {
            font-size: 1.1em;
            line-height: 1.8;
            margin-bottom: 15px;
            color: #202124;
        }
        .detail-point, .unique-point {
            font-size: 1.05em;
            line-height: 1.7;
            margin-bottom: 15px;
            color: #3c4043;
            padding-left: 15px;
            border-left: 3px solid #1a73e8;
        }
        .supporting-info {
            font-size: 1em;
            line-height: 1.6;
            color: #5f6368;
            background-color: #fff;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }
        .video-perspective {
            margin-bottom: 25px;
            padding: 15px;
            background-color: #fff;
            border-radius: 8px;
        }
        .video-title {
            font-size: 1.2em;
            color: #1a73e8;
            margin-bottom: 12px;
        }
        b {
            color: #202124;
            background-color: #e8f0fe;
            padding: 3px 6px;
            border-radius: 4px;
            font-weight: 600;
        }
        @media (max-width: 768px) {
            .summary-container, .comparison-container {
                padding: 10px;
            }
            .summary-section, .common-section, .unique-section, .conclusion-section {
                padding: 15px;
                margin-bottom: 25px;
            }
            .detail-point, .unique-point {
                padding-left: 10px;
            }
        }
        </style>
        """

        try:
            summary = re.sub(r"```html|```", "", summary)
            summary = re.sub(r"위의 HTML.*$", "", summary, flags=re.MULTILINE)
            summary = re.sub(r"이 HTML.*$", "", summary, flags=re.MULTILINE)
            summary = re.sub(r"요약된 내용.*$", "", summary, flags=re.MULTILINE)
            
            soup = BeautifulSoup(summary, "html.parser")

            # 중복 섹션 제거
            seen_titles = set()
            for section in soup.find_all(['section', 'div']):
                title = section.find('h3')
                if title:
                    title_text = title.get_text().strip()
                    if title_text in seen_titles:
                        section.decompose()
                    else:
                        seen_titles.add(title_text)
            
            # 허용된 태그와 클래스 목록
            allowed_tags = {
                'div': ['summary-container', 'content-block', 'comparison-container', 'video-perspective'],
                'section': ['summary-section', 'common-section', 'unique-section', 'conclusion-section'],
                'h3': ['section-title'],
                'h4': ['video-title'],
                'p': ['main-point', 'detail-point', 'supporting-info', 'key-point', 'unique-point', 'conclusion-point'],
                'b': []
            }
            
            # 태그 정리
            for tag in soup.find_all(True):
                if tag.name not in allowed_tags:
                    tag.unwrap()
                else:
                    if tag.get('class'):
                        tag['class'] = [c for c in tag['class'] if c in allowed_tags[tag.name]]
            
            final_html = css_style + str(soup.prettify())
            final_html = re.sub(r'\n\s*\n', '\n', final_html)
            
            return final_html

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"HTML 처리 중 오류 발생: {str(e)}")