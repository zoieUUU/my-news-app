import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import json
import time
import re

# 1. AI 엔진 설정 - 404 에러 원천 차단을 위한 강제 고정
# 시스템이 gemini-1.5-flash를 기본값으로 호출하지 못하도록 명시적으로 최신 모델명을 주입합니다.
MODEL_ID = 'gemini-2.5-flash-preview-09-2025'

def call_ai(prompt, is_image=False, image_input=None):
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            st.error("API 키가 설정되지 않았습니다. st.secrets를 확인해주세요.")
            return None
            
        genai.configure(api_key=api_key)
        # 호출 시마다 모델 객체를 생성하여 구형 모델로의 폴백을 방지합니다.
        model = genai.GenerativeModel(model_name=MODEL_ID)
        
        if is_image and image_input:
            response = model.generate_content([prompt, image_input])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        err_msg = str(e).lower()
        if "404" in err_msg or "not found" in err_msg:
            st.error("⚠️ 서버 환경 오류: 구형 모델(1.5-flash) 정보가 감지되었습니다.")
            st.info("💡 해결 방법: 우측 상단 'Clear Cache' 클릭 후 브라우저 새로고침(F5)을 해주세요.")
        else:
            st.error(f"AI 호출 오류: {e}")
        return None

# --- UI 레이아웃 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO", layout="wide")

st.title("👑 VIRAL MASTER PRO (최종 복구 버전)")

# 탭 구조: 렌더링 오류 방지를 위해 명시적으로 세션과 연동
tab1, tab2 = st.tabs(["🔥 소재 탐색기", "📸 분석 & 원고"])

# --- 데이터 수집 및 크롤링 ---
@st.cache_data(ttl=600)
def get_news():
    try:
        url = "https://news.naver.com/main/ranking/popularDay.naver"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    items.append({"title": a.text.strip(), "link": a['href']})
        return items[:30]
    except:
        return []

news_list = get_news()

# TAB 1: 실시간 뉴스 기반 소재 분석
with tab1:
    col_l, col_r = st.columns([1, 1.2])
    
    with col_l:
        st.subheader("📰 실시간 랭킹 뉴스")
        if st.button("🔄 뉴스 새로고침"):
            st.cache_data.clear()
            st.rerun()
            
        for i, item in enumerate(news_list):
            if st.button(f"[{i+1}] {item['title']}", key=f"btn_{i}"):
                st.session_state.selected_news = item
                
    with col_r:
        if "selected_news" in st.session_state:
            news = st.session_state.selected_news
            st.markdown(f"### 📊 분석 중: {news['title']}")
            
            with st.spinner("AI가 썸네일 카피와 소재를 분석 중입니다..."):
                analysis_prompt = f"이 뉴스 제목을 분석해서 유튜브 썸네일 문구 3개와 100만 조회수를 유도할 수 있는 후킹 포인트를 요약해줘: {news['title']}"
                res = call_ai(analysis_prompt)
                if res:
                    st.success(res.text)
                st.divider()
                st.write(f"🔗 [원문 기사 보기]({news['link']})")
        else:
            st.info("왼쪽 뉴스 리스트에서 분석하고 싶은 소재를 선택해 주세요.")

# TAB 2: 이미지 분석 및 원고 작가 모드
with tab2:
    st.subheader("📸 이미지 분석 및 커스텀 원고")
    up_file = st.file_uploader("커뮤니티/타채널 캡처본 업로드", type=["jpg", "png", "jpeg"])
    
    if up_file:
        img = PIL.Image.open(up_file)
        st.image(img, caption="업로드된 소재 이미지", use_container_width=True)
        if st.button("🔍 이미지 AI 분석 시작"):
            with st.spinner("이미지 텍스트 및 가치 분석 중..."):
                res = call_ai("이 이미지에 담긴 내용을 상세히 설명하고, 이를 활용한 유튜브 영상 기획 아이디어를 제안해줘.", is_image=True, image_input=img)
                if res:
                    st.info(res.text)

    st.divider()
    st.subheader("📝 고성능 원고 프롬프트 생성")
    t_title = st.text_input("영상 제목 (가제)")
    t_context = st.text_area("핵심 팩트 및 내용", placeholder="기사 내용이나 정리된 팩트를 입력하세요.")
    
    if st.button("🔥 100만 작가 프롬프트 생성"):
        if t_title and t_context:
            final_prompt = f"""
당신은 유튜브 전문 작가입니다. 다음 소재로 조회수가 터질 원고를 작성하세요.

제목: {t_title}
팩트: {t_context}

작성 규칙: 첫 10초에 시청자를 고정시키고, 감정적인 타격감을 주는 멘트를 포함하세요.
            """
            st.code(final_prompt, language="markdown")
            st.success("프롬프트를 복사하여 Claude나 ChatGPT에 입력해 보세요.")
        else:
            st.warning("제목과 내용을 모두 입력해 주세요.")
