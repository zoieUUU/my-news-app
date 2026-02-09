import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정
@st.cache_resource
def load_ai_model():
    try:
        model_name = 'gemini-2.5-flash-preview-09-2025'
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            return genai.GenerativeModel(model_name)
        else:
            genai.configure(api_key="")
            return genai.GenerativeModel(model_name)
    except Exception as e:
        st.error(f"AI 모델 초기화 실패: {e}")
        return None

model = load_ai_model()

# 2. API 호출 최적화 함수 (재시도 로직 유지하며 가볍게 처리)
def call_gemini_optimized(prompt, is_image=False, images=None):
    if not model:
        return None
    
    max_retries = 2 # 재시도 횟수 축소 (속도 향상)
    for i in range(max_retries):
        try:
            if is_image and images:
                response = model.generate_content([prompt, *images])
            else:
                response = model.generate_content(prompt)
            return response
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg:
                wait_sec = 10 + (i * 5) 
                placeholder = st.empty()
                placeholder.warning(f"⚠️ API 한도 도달. {wait_sec}초 후 자동 재시도...")
                time.sleep(wait_sec)
                placeholder.empty()
                continue
            else:
                break
    return None

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- UI 스타일 ---
st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        border-radius: 8px !important;
        padding: 10px !important;
        margin-bottom: 2px;
        width: 100%;
    }
    div.stButton > button:has(div:contains("🏆")) {
        background-color: #fff9e6 !important;
        border: 2px solid #FFD700 !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 18px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 수집 (30개로 축소) ---
@st.cache_data(ttl=600)
def fetch_news_data():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        items = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    items.append({"title": a.text.strip(), "link": a['href']})
        return items[:30] # 60개 -> 30개로 줄여서 가볍게 만듦
    except:
        return []

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        area = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
        return area.get_text(strip=True) if area else "본문 없음"
    except:
        return "수집 실패"

# --- 메인 로직 ---
st.title("👑 VIRAL MASTER PRO v2.6")

# 탭 구조 복구
tab1, tab2 = st.tabs(["🔥 뉴스 이슈", "🎯 원고 빌더"])

news_list = fetch_news_data()

with tab1:
    if news_list:
        # S급 선별 결과 세션 저장
        if "s_indices" not in st.session_state:
            with st.spinner("🚀 소재 선별 중..."):
                titles = "\n".join([f"{i}:{n['title'][:25]}" for i, n in enumerate(news_list)])
                prompt = f"다음 중 '국뽕/기술/충격' 소재 5개 번호만 골라줘. [1,2,3] 형식으로 답변.\n{titles}"
                resp = call_gemini_optimized(prompt)
                if resp:
                    try:
                        match = re.search(r"\[.*\]", resp.text)
                        st.session_state.s_indices = json.loads(match.group()) if match else []
                    except:
                        st.session_state.s_indices = []
                else:
                    st.session_state.s_indices = []

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📰 실시간 이슈")
            if st.button("🔄 새로고침"):
                st.cache_data.clear()
                if "s_indices" in st.session_state: del st.session_state.s_indices
                st.rerun()

            for i, item in enumerate(news_list):
                is_s = i in st.session_state.s_indices
                label = f"🏆 [S급] {item['title']}" if is_s else f"[{i+1}] {item['title']}"
                
                if st.button(label, key=f"n_{i}"):
                    with st.spinner("분석 중..."):
                        txt = get_content(item['link'])
                        # 분석 프롬프트 간소화 (가볍게)
                        ana_resp = call_gemini_optimized(f"이 기사의 썸네일 카피 3개와 요약 1줄만 적어줘:\n{txt[:800]}")
                        st.session_state.current_view = {
                            "title": item['title'],
                            "content": txt,
                            "analysis": ana_resp.text if ana_resp else "제한 초과. 잠시 후 재시도.",
                            "is_s": is_s
                        }

        with col2:
            if "current_view" in st.session_state:
                v = st.session_state.current_view
                st.markdown(f"### {'🔥 S급 황금소재' if v['is_s'] else '📊 일반소재'}")
                st.success(v['analysis'])
                st.text_area("본문", v['content'], height=350)
            else:
                st.info("뉴스를 선택하면 분석이 시작됩니다.")

with tab2:
    st.header("🎯 초격차 원고 빌더")
    c_a, c_b = st.columns(2)
    with c_a:
        v_title = st.text_input("💎 제목")
        v_fact = st.text_area("📰 팩트", height=150)
    with c_b:
        v_target = st.text_input("📺 타겟 URL")
        v_vibe = st.text_area("💬 민심", height=150)

    if st.button("🔥 클로드 전용 프롬프트 생성"):
        if v_title and v_fact:
            p = f"이슈 채널 작가로서 다음 데이터를 기반으로 원고 작성해줘.\n제목: {v_title}\n내용: {v_fact}\n참고: {v_target}\n민심: {v_vibe}"
            st.code(p, language="markdown")
            st.success("복사해서 사용하세요!")
