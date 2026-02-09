import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정 - 최신 모델명으로 강제 고정
@st.cache_resource(show_spinner=False)
def load_ai_model():
    try:
        # Canvas 환경에서 현재 가장 안정적인 모델명입니다.
        target_model_name = 'gemini-2.5-flash-preview-09-2025'
        
        # API 키 설정
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        genai.configure(api_key=api_key)
        
        # 모델 객체 생성 (폴백 없이 이 모델만 사용하도록 설정)
        return genai.GenerativeModel(target_model_name)
    except Exception as e:
        st.error(f"AI 모델 초기화 실패: {e}")
        return None

# 전역 모델 인스턴스 생성
ai_engine = load_ai_model()

# 2. AI 호출 함수 - 404 및 429 에러 방어 로직
def call_gemini_api(prompt, is_image=False, images=None):
    if not ai_engine:
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
            
            # 404 에러 발생 시 (모델 이름 문제)
            if "404" in error_msg:
                st.error("⚠️ [404 에러] 모델 경로를 찾을 수 없습니다. 브라우저 캐시를 삭제하거나 잠시 후 다시 시도해 주세요.")
                return None
                
            # 429 에러 발생 시 (할당량 초과) - 지수 백오프 대기
            if "429" in error_msg or "quota" in error_msg:
                wait_time = 15 + (i * 10)
                status_box = st.empty()
                status_box.warning(f"⏳ API 호출 한도 초과: {wait_time}초 후 자동으로 다시 시도합니다...")
                time.sleep(wait_time)
                status_box.empty()
                continue
                
            st.error(f"AI 호출 오류: {e}")
            break
    return None

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- UI 디자인 (S급 강조 및 탭 스타일) ---
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
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        border-color: #FF4B4B !important;
        background-color: #fffafa !important;
    }
    /* S급(🏆) 버튼 특수 효과 */
    div.stButton > button:has(div:contains("🏆")) {
        background-color: #fff9e6 !important;
        border: 2px solid #FFD700 !important;
        color: #856404 !important;
        font-weight: bold !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 18px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 수집 함수 (가볍게 30개만) ---
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
        return body.get_text(strip=True) if body else "본문을 가져올 수 없습니다."
    except:
        return "데이터 수집 중 오류 발생"

# --- 앱 메인 화면 ---
st.title("👑 VIRAL MASTER PRO v2.6")

tab1, tab2 = st.tabs(["🔥 실시간 이슈 탐색", "🎯 초격차 원고 제작"])

news_items = fetch_top_news()

with tab1:
    if news_items:
        # S급 소재 선별 (세션 저장으로 중복 호출 방지)
        if "s_class_indices" not in st.session_state:
            with st.spinner("🚀 AI가 실시간으로 떡상 소재를 선별하고 있습니다..."):
                titles_summary = "\n".join([f"{i}:{n['title'][:30]}" for i, n in enumerate(news_items)])
                select_prompt = f"다음 뉴스 중 유튜브 조회수가 높을법한 소재 5개 번호만 골라줘. [1,2,3] 형식으로 번호만 답변해:\n{titles_summary}"
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
                    with st.spinner("AI가 전략을 수립 중입니다..."):
                        body_txt = get_news_body(item['link'])
                        analysis_resp = call_gemini_api(f"다음 기사를 분석해서 1.썸네일 제목 3개 2.내용 요약 1줄을 써줘:\n{body_txt[:1000]}")
                        st.session_state.current_news = {
                            "title": item['title'],
                            "body": body_txt,
                            "analysis": analysis_resp.text if analysis_resp else "분석 불가 (API 한도 초과)",
                            "is_viral": is_viral
                        }

        with right_col:
            if "current_news" in st.session_state:
                data = st.session_state.current_news
                st.markdown(f"### {'🔥 S급 황금 소재 분석' if data['is_viral'] else '📊 일반 소재 분석'}")
                st.success(data['analysis'])
                st.divider()
                st.markdown("**📄 뉴스 원문 데이터**")
                st.text_area("Original Text", data['body'], height=400)
            else:
                st.info("왼쪽 뉴스 리스트에서 분석할 기사를 클릭해 주세요.")

with tab2:
    st.header("🎯 초격차 원고 마스터 빌더")
    c_left, c_right = st.columns(2)
    with c_left:
        final_title = st.text_input("💎 영상 가제 (제목)")
        final_fact = st.text_area("📰 핵심 기사/팩트 내용", height=200)
    with c_right:
        final_target = st.text_input("📺 참고 유튜브 URL/채널")
        final_comment = st.text_area("💬 예상 시청자 반응/댓글", height=200)

    if st.button("🔥 클로드 전용 고밀도 원고 프롬프트 생성"):
        if final_title and final_fact:
            script_prompt = f"""당신은 100만 유튜버의 메인 작가입니다. 다음 데이터를 기반으로 8분 분량의 고밀도 원고를 작성하세요.\n\n주제: {final_title}\n팩트내용: {final_fact}\n벤치마킹: {final_target}\n민심반응: {final_comment}\n\n[지침] 후킹을 강하게 시작하고, 문장마다 감정 태그를 넣으세요."""
            st.code(script_prompt, language="markdown")
            st.success("위 프롬프트를 복사하여 Claude 또는 GPT에 입력하세요!")
