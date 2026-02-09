import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정 - 모델명 고정 및 캐시 강제 초기화 로직
# 캐시 파라미터(hash_funcs)를 추가하여 이전 1.5-flash 캐시를 완전히 무효화합니다.
@st.cache_resource(show_spinner=False, hash_funcs={genai.GenerativeModel: lambda _: None})
def load_ai_model(version_tag="v2.6_stable"):
    try:
        # Canvas 환경 전용 최신 모델명
        target_model = 'gemini-2.5-flash-preview-09-2025'
        
        # API 키 설정
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        genai.configure(api_key=api_key)
        
        # 모델 객체 생성 (명시적으로 모델명을 다시 주입)
        model = genai.GenerativeModel(model_name=target_model)
        return model
    except Exception as e:
        st.error(f"AI 모델 초기화 실패: {e}")
        return None

# 전역 모델 인스턴스 (버전 태그를 변경하여 캐시 리프레시 유도)
ai_engine = load_ai_model(version_tag="fixed_404_v1")

# 2. AI 호출 함수 - 에러 방어 및 리라이트 로직
def call_gemini_api(prompt, is_image=False, images=None):
    if not ai_engine:
        # 모델이 로드되지 않았을 경우 재시도 유도
        st.warning("AI 엔진이 준비되지 않았습니다. 새로고침을 시도하세요.")
        return None
    
    max_retries = 3
    for i in range(max_retries):
        try:
            if is_image and images:
                response = ai_engine.generate_content([prompt, *images])
            else:
                response = ai_engine.generate_content(prompt)
            return response
        except Exception as e:
            error_msg = str(e).lower()
            
            # 404 에러 발생 시 (가장 문제되는 부분)
            if "404" in error_msg or "not found" in error_msg:
                # 즉각적으로 사용자에게 캐시 삭제 가이드 제공
                st.error("⚠️ 시스템에 구형 모델 정보가 남아있습니다. 우측 상단 'Clear Cache' 후 새로고침하세요.")
                return None
                
            # 429 에러 발생 시 (할당량 초과)
            if "429" in error_msg or "quota" in error_msg:
                wait_time = 15 + (i * 10)
                status_box = st.empty()
                status_box.warning(f"⏳ API 한도 도달: {wait_time}초 후 다시 시도합니다...")
                time.sleep(wait_time)
                status_box.empty()
                continue
                
            st.error(f"AI 호출 오류: {e}")
            break
    return None

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- UI 디자인 ---
st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        border-radius: 10px !important;
        padding: 12px !important;
        margin-bottom: 4px;
        width: 100%;
        border: 1px solid #ddd !important;
        background-color: white !important;
    }
    div.stButton > button:has(div:contains("🏆")) {
        background-color: #fff9e6 !important;
        border: 2px solid #FFD700 !important;
        font-weight: bold !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 18px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 수집 함수 ---
@st.cache_data(ttl=600)
def fetch_top_news():
    try:
        url = "https://news.naver.com/main/ranking/popularDay.naver"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        news_list = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    news_list.append({"title": a.text.strip(), "link": a['href']})
        return news_list[:30]
    except:
        return []

def get_news_body(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        body = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
        return body.get_text(strip=True) if body else "본문 수집 불가"
    except:
        return "데이터 수집 오류"

# --- 메인 화면 ---
st.title("👑 VIRAL MASTER PRO v2.6")

tab1, tab2 = st.tabs(["🔥 실시간 이슈 탐색", "🎯 초격차 원고 제작"])

news_items = fetch_top_news()

with tab1:
    if news_items:
        if "s_class_indices" not in st.session_state:
            with st.spinner("🚀 AI 소재 선별 중..."):
                titles_summary = "\n".join([f"{i}:{n['title'][:30]}" for i, n in enumerate(news_items)])
                select_prompt = f"다음 뉴스 중 유튜브 조회수가 높을법한 소재 5개 번호만 골라줘. [1,2,3] 형식으로 답변:\n{titles_summary}"
                selection_resp = call_gemini_api(select_prompt)
                if selection_resp:
                    try:
                        match = re.search(r"\[.*\]", selection_resp.text)
                        st.session_state.s_class_indices = json.loads(match.group()) if match else []
                    except:
                        st.session_state.s_class_indices = []
                else:
                    st.session_state.s_class_indices = []

        left_col, right_col = st.columns([1, 1])

        with left_col:
            st.subheader("📰 실시간 랭킹 뉴스")
            if st.button("🔄 리스트 새로고침"):
                st.cache_data.clear()
                if "s_class_indices" in st.session_state: del st.session_state.s_class_indices
                st.rerun()

            for i, item in enumerate(news_items):
                is_viral = i in st.session_state.get('s_class_indices', [])
                btn_label = f"🏆 [S급] {item['title']}" if is_viral else f"[{i+1}] {item['title']}"
                
                if st.button(btn_label, key=f"news_btn_{i}"):
                    with st.spinner("분석 중..."):
                        body_txt = get_news_body(item['link'])
                        analysis_resp = call_gemini_api(f"다음 기사 분석(썸네일 3개, 요약 1줄):\n{body_txt[:1000]}")
                        st.session_state.current_news = {
                            "title": item['title'],
                            "body": body_txt,
                            "analysis": analysis_resp.text if analysis_resp else "분석 불가 (API 한도 초과)",
                            "is_viral": is_viral
                        }

        with right_col:
            if "current_news" in st.session_state:
                data = st.session_state.current_news
                st.markdown(f"### {'🔥 S급 소재 분석' if data['is_viral'] else '📊 일반 소재 분석'}")
                st.success(data['analysis'])
                st.text_area("뉴스 원문", data['body'], height=400)
            else:
                st.info("왼쪽 기사를 클릭하세요.")

with tab2:
    st.header("🎯 원고 마스터 빌더")
    c_left, c_right = st.columns(2)
    with c_left:
        final_title = st.text_input("💎 제목")
        final_fact = st.text_area("📰 팩트", height=200)
    with c_right:
        final_target = st.text_input("📺 타겟 URL")
        final_comment = st.text_area("💬 댓글 반응", height=200)

    if st.button("🔥 원고 프롬프트 생성"):
        if final_title and final_fact:
            script_prompt = f"유튜브 작가로서 원고 작성.\n제목: {final_title}\n팩트: {final_fact}\n타겟: {final_target}\n민심: {final_comment}"
            st.code(script_prompt, language="markdown")
            st.success("프롬프트를 복사하세요!")
