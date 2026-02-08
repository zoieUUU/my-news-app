import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# AI 설정
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="유메이커 MASTER", layout="wide")

# --- 뉴스 통합 수집 함수 ---
def get_multiple_contents(urls):
    combined_text = ""
    url_list = [u.strip() for u in urls.split('\n') if u.strip()]
    for url in url_list:
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, 'html.parser')
            content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
            if content:
                combined_text += f"\n\n[참고기사 본문]\n{content.text.strip()}"
        except: continue
    return combined_text

# --- 화면 구성 ---
st.title("🚀 유메이커 MASTER : 초바이럴 1차 원고 빌더")
left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.subheader("🔥 실시간 TOP 100 (소재 발굴)")
    # (뉴스 리스트 코드는 기존과 동일하게 유지)
    # ...

with right_col:
    st.subheader("🛠️ 멀티 링크 통합 및 1차 원고 생성")
    # 링크 입력창 (여러 개 입력 가능)
    ref_urls = st.text_area("🔗 관련 기사 링크들을 모두 넣어주세요 (한 줄에 하나씩)", 
                            value=st.session_state.get('url', ''), height=100)
    
    if st.button("🎯 통합 분석 및 초바이럴 원고 생성", type="primary", use_container_width=True):
        with st.spinner('여러 기사 데이터를 통합하여 1차 원고 집필 중...'):
            all_content = get_multiple_contents(ref_urls)
            
            prompt = f"""
            너는 유튜브 100만 기획자야. 제공된 여러 개의 기사 내용을 통합해서 
            '클로드(Claude) 2차 가공용' 초바이럴 1차 원고를 작성해줘.

            [입력된 통합 데이터]
            {all_content}

            [작성 가이드라인]
            1. 분석 등급: 이 소재들이 합쳐졌을 때의 최종 등급 (S~C)
            2. 핵심 갈등: 여러 기사에서 공통적으로 나타나는 '민심 폭발' 포인트
            3. 1차 원고 구조:
               - [HOOK] 0~25초: 가장 자극적인 팩트 중심의 충격 오프닝
               - [BODY] 기사들의 팩트를 논리적으로 연결한 사건 전개
               - [EPILOGUE] 시청자 댓글 유도용 논란 거리 제시
            4. 클로드 전달용 요약: 이 원고를 클로드에서 더 정교하게 만들 때 강조할 핵심 키워드들
            """
            response = model.generate_content(prompt)
            st.markdown("---")
            st.write("✅ **이 내용을 복사해서 클로드(Claude)로 가져가세요!**")
            st.code(response.text, language="markdown") # 복사하기 편하게 코드블록으로 출력
