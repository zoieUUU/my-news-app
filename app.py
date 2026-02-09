import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정 (캐시 강제 초기화 및 모델명 명시)
@st.cache_resource(show_spinner=False)
def load_ai_model():
    try:
        # 현재 Canvas 환경에서 가장 안정적인 최신 모델명으로 고정
        target_model = 'gemini-2.5-flash-preview-09-2025'
        
        # API 키 설정 (공백일 경우 환경 변수 참조)
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        genai.configure(api_key=api_key)
        
        # 모델 객체 생성
        return genai.GenerativeModel(target_model)
    except Exception as e:
        st.error(f"AI 모델 로드 실패: {e}")
        return None

# 전역 변수로 모델 로드
model_instance = load_ai_model()

# 2. API 호출 최적화 함수 (변수 오타 수정 및 에러 핸들링 강화)
def call_gemini_safe(prompt, is_image=False, images=None):
    if not model_instance:
        return None
    
    for i in range(3): # 최대 3번 재시도
        try:
            if is_image and images:
                response = model_instance.generate_content([prompt, *images])
            else:
                response = model_instance.generate_content(prompt)
            return response
        except Exception as e:
            err_str = str(e).lower()
            
            # 404 에러 발생 시 (모델명 불일치)
            if "404" in err_str:
                st.error("⚠️ [404 Error] 현재 환경에서 지원하지 않는 모델을 호출 중입니다. 모델 설정을 다시 확인하세요.")
                return None
                
            # 429(할당량 초과) 발생 시 대기 로직 (err_msg -> err_str 오타 수정)
            if "429" in err_str or "quota" in err_str:
                wait = 15 + (i * 10)
                msg = st.empty()
                msg.warning(f"⏳ API 제한 대기 중... ({wait}초 후 재시도)")
                time.sleep(wait)
                msg.empty()
                continue
                
            st.error(f"AI 응답 오류: {e}")
            break
    return None

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- CSS 스타일 ---
st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        border-radius: 8px !important;
        padding: 12px !important;
        margin-bottom: 2px;
        width: 100%;
        border: 1px solid #eee !important;
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

# --- 뉴스 데이터 수집 ---
@st.cache_data(ttl=600)
def fetch_news():
    try:
        url = "https://news.naver.com/main/ranking/popularDay.naver"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
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

def get_article_body(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
        return content.get_text(strip=True) if content else "내용 없음"
    except:
        return "수집 에러"

# --- 메인 대시보드 ---
st.title("👑 VIRAL MASTER PRO v2.6")

tab1, tab2 = st.tabs(["🔥 뉴스 이슈 탐색", "🎯 초격차 원고 빌더"])

news_data = fetch_news()

with tab1:
    if news_data:
        # S급 인덱스 세션 관리
        if "s_list" not in st.session_state:
            with st.spinner("🚀 AI가 떡상 소재를 분석 중입니다..."):
                titles_text = "\n".join([f"{i}:{n['title'][:30]}" for i, n in enumerate(news_data)])
                prompt = f"다음 리스트 중 유튜브 조회수가 높을법한 소재 5개 번호만 골라줘. [1,2,3] 형식으로 답변해.\n{titles_text}"
                resp = call_gemini_safe(prompt)
                if resp:
                    try:
                        found = re.search(r"\[.*\]", resp.text)
                        st.session_state.s_list = json.loads(found.group()) if found else []
                    except:
                        st.session_state.s_list = []
                else:
                    st.session_state.s_list = []

        c1, c2 = st.columns([1, 1])

        with c1:
            st.subheader("📰 실시간 랭킹")
            if st.button("🔄 데이터 갱신"):
                st.cache_data.clear()
                if "s_list" in st.session_state: del st.session_state.s_list
                st.rerun()

            for i, item in enumerate(news_data):
                is_s = i in st.session_state.get('s_list', [])
                label = f"🏆 [S급] {item['title']}" if is_s else f"[{i+1}] {item['title']}"
                
                if st.button(label, key=f"btn_{i}"):
                    with st.spinner("AI 전략 분석 중..."):
                        body = get_article_body(item['link'])
                        analysis = call_gemini_safe(f"다음 기사의 썸네일 카피 3개와 요약 1줄만 써줘:\n{body[:1000]}")
                        st.session_state.view_data = {
                            "title": item['title'],
                            "body": body,
                            "analysis": analysis.text if analysis else "분석 불가 (API 제한)",
                            "is_s": is_s
                        }

        with c2:
            if "view_data" in st.session_state:
                vd = st.session_state.view_data
                st.markdown(f"### {'🔥 S급 황금 소재' if vd['is_s'] else '📊 일반 소재'}")
                st.success(vd['analysis'])
                st.divider()
                st.text_area("기사 본문", vd['body'], height=400)
            else:
                st.info("왼쪽 뉴스를 클릭하세요.")

with tab2:
    st.header("🎯 초격차 원고 빌더")
    col_l, col_r = st.columns(2)
    with col_l:
        in_title = st.text_input("💎 영상 제목")
        in_fact = st.text_area("📰 핵심 팩트", height=200)
    with col_r:
        in_target = st.text_input("📺 벤치마킹 타겟")
        in_vibe = st.text_area("💬 시청자 반응", height=200)

    if st.button("🔥 클로드용 고밀도 프롬프트 생성"):
        if in_title and in_fact:
            final_p = f"유튜브 작가로서 원고 작성해줘.\n제목: {in_title}\n팩트: {in_fact}\n타겟: {in_target}\n여론: {in_vibe}"
            st.code(final_p, language="markdown")
            st.success("프롬프트가 생성되었습니다!")
