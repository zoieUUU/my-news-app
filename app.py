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
        # 무료 티어에서 가장 안정적인 모델명 사용
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

# 2. API 호출 최적화 함수 (쿼터 제한 대응)
def call_gemini_optimized(prompt, is_image=False, images=None):
    if not model:
        return None
    
    max_retries = 3
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
                # 무료 티어 제한 도달 시 대기 시간 안내
                wait_sec = 15 + (i * 10) 
                placeholder = st.empty()
                placeholder.warning(f"⚠️ API 호출 한도 초과! {wait_sec}초 후 자동으로 다시 시도합니다. (잠시만 기다려 주세요)")
                time.sleep(wait_sec)
                placeholder.empty()
                continue
            else:
                st.error(f"알 수 없는 오류 발생: {e}")
                break
    return None

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- UI 스타일 커스터마이징 ---
st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        border-radius: 8px !important;
        background-color: #ffffff !important;
        border: 1px solid #eee !important;
        margin-bottom: 2px;
        width: 100%;
        font-size: 14px !important;
    }
    /* S급 기사 하이라이트 */
    div.stButton > button:has(div:contains("🏆")) {
        background-color: #fff9e6 !important;
        border: 2px solid #FFD700 !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 수집 로직 ---
@st.cache_data(ttl=600) # 10분간 캐시 유지하여 중복 호출 방지
def fetch_news_data():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    items.append({"title": a.text.strip(), "link": a['href']})
        return items[:60] # 최대 60개
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

news_list = fetch_news_data()

if news_list:
    # 1. S급 선별 (세션에 저장하여 1일 1회 혹은 새로고침 시에만 작동하도록)
    if "s_indices" not in st.session_state:
        with st.spinner("🚀 AI가 황금 소재를 선별 중입니다..."):
            # 제목을 짧게 압축해서 보내 쿼터 소모 줄임
            short_titles = "\n".join([f"{i}:{n['title'][:30]}" for i, n in enumerate(news_list)])
            prompt = f"다음 뉴스 번호 중 유튜버가 다루기 좋은 '국뽕/방산/반도체/외신반응' 소재 5개 번호만 골라줘. 예: [1,2,3]\n{short_titles}"
            resp = call_gemini_optimized(prompt)
            if resp:
                try:
                    match = re.search(r"\[.*\]", resp.text)
                    st.session_state.s_indices = json.loads(match.group()) if match else []
                except:
                    st.session_state.s_indices = []
            else:
                st.session_state.s_indices = []

    s_idx = st.session_state.s_indices

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📰 실시간 뉴스 (S급 표시)")
        if st.button("🔄 리스트 새로고침 (API 소모 주의)"):
            st.cache_data.clear()
            if "s_indices" in st.session_state: del st.session_state.s_indices
            st.rerun()

        for i, item in enumerate(news_list):
            is_s = i in s_idx
            label = f"🏆 [S급] {item['title']}" if is_s else f"[{i+1}] {item['title']}"
            
            if st.button(label, key=f"news_{i}"):
                with st.spinner("AI 분석 중..."):
                    txt = get_content(item['link'])
                    # 분석 호출
                    ana_resp = call_gemini_optimized(f"기사 분석해서 썸네일 카피 3개랑 핵심 요약해줘:\n{txt[:1000]}")
                    st.session_state.current_view = {
                        "title": item['title'],
                        "content": txt,
                        "analysis": ana_resp.text if ana_resp else "분석 실패 (API 제한)",
                        "is_s": is_s
                    }

    with col2:
        if "current_view" in st.session_state:
            view = st.session_state.current_view
            st.markdown(f"### {'🔥 S급 황금소재' if view['is_s'] else '📊 일반소재'}")
            st.info(f"**제목: {view['title']}**")
            st.success(view['analysis'])
            st.text_area("본문 데이터", view['content'], height=400)
        else:
            st.write("분석할 뉴스를 선택해 주세요.")
