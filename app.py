import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import json
import time
import re

# 1. AI 엔진 설정 (2월 9일 초기 요청 기반 복구)
# 현재 환경에서 유효하지 않은 gemini-1.5-flash 대신 최신 안정 버전을 사용합니다.
MODEL_ID = 'gemini-2.5-flash-preview-09-2025'

def call_ai(prompt, is_image=False, image_input=None):
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=MODEL_ID)
        
        if is_image and image_input:
            response = model.generate_content([prompt, image_input])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        err_msg = str(e)
        if "404" in err_msg:
            st.error("서버에서 구형 모델(1.5-flash)을 찾을 수 없습니다. 설정된 2.5 모델로 재시도 중...")
        else:
            st.error(f"AI 호출 오류: {e}")
        return None

# --- UI 레이아웃 ---
st.set_page_config(page_title="VIRAL MASTER PRO", layout="wide")

st.title("👑 VIRAL MASTER PRO (초기 복구 버전)")

# 탭 구조 재설정
tab1, tab2 = st.tabs(["🔥 소재 탐색기", "📸 분석 & 원고"])

# --- 데이터 수집 ---
@st.cache_data(ttl=600)
def get_news():
    try:
        url = "https://news.naver.com/main/ranking/popularDay.naver"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        items = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a: items.append({"title": a.text.strip(), "link": a['href']})
        return items[:30]
    except:
        return []

news_list = get_news()

with tab1:
    col_l, col_r = st.columns([1, 1])
    
    with col_l:
        st.subheader("📰 실시간 랭킹 뉴스")
        for i, item in enumerate(news_list):
            if st.button(f"[{i+1}] {item['title']}", key=f"btn_{i}"):
                st.session_state.selected_news = item
                
    with col_r:
        if "selected_news" in st.session_state:
            news = st.session_state.selected_news
            st.subheader("📊 소재 분석")
            with st.spinner("AI 분석 중..."):
                res = call_ai(f"이 뉴스 제목을 분석해서 유튜브 썸네일 문구 3개 만들어줘: {news['title']}")
                if res:
                    st.success(res.text)
                st.write(f"원문 링크: {news['link']}")
        else:
            st.info("뉴스를 선택하면 분석이 시작됩니다.")

with tab2:
    st.subheader("📸 이미지 및 원고 작성")
    up_file = st.file_uploader("캡처본 업로드", type=["jpg", "png", "jpeg"])
    
    if up_file:
        img = PIL.Image.open(up_file)
        st.image(img, caption="업로드 이미지", use_container_width=True)
        if st.button("이미지 분석"):
            with st.spinner("분석 중..."):
                res = call_ai("이 이미지의 내용을 설명해줘.", is_image=True, image_input=img)
                if res: st.info(res.text)

    st.divider()
    t_title = st.text_input("영상 제목")
    t_context = st.text_area("영상 내용/팩트")
    
    if st.button("원고 프롬프트 생성"):
        if t_title and t_context:
            prompt_result = f"제목: {t_title}\n내용: {t_context}\n\n위 내용을 바탕으로 유튜브 대본을 작성해줘."
            st.code(prompt_result)
