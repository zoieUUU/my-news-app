import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정 - 시스템의 강제 폴백(Fallback)을 차단하는 하드코딩 방식
def get_ai_response(prompt, is_image=False, image_input=None):
    """
    라이브러리 캐시나 기본값에 의존하지 않고, 
    호출 순간마다 최신 모델명을 직접 주입하여 404 에러를 방지합니다.
    """
    # Canvas 환경에서 현재 유효한 최신 모델명 고정
    STABLE_MODEL_NAME = 'gemini-2.5-flash-preview-09-2025'
    
    # API 키 설정
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    genai.configure(api_key=api_key)
    
    # 호출 시마다 모델 객체를 새로 생성하여 구형 모델 참조를 원천 차단
    try:
        model = genai.GenerativeModel(model_name=STABLE_MODEL_NAME)
        
        if is_image and image_input:
            response = model.generate_content([prompt, image_input])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        err_msg = str(e).lower()
        
        # 여전히 404가 발생할 경우를 대비한 하드코딩된 에러 핸들링
        if "404" in err_msg or "not found" in err_msg:
            st.error("⚠️ [시스템 긴급] 구형 모델 호출 버그가 감지되었습니다.")
            st.info("이 에러는 서버 환경의 일시적 모델 매핑 오류입니다. 코드 레벨에서 모델명을 강제 교체했으니, 페이지를 다시 한 번만 리로드해 주세요.")
            return None
            
        # 429 한도 초과 대응
        if "429" in err_msg or "quota" in err_msg:
            st.warning("⏳ API 호출 한도 초과. 잠시 후 시도하세요.")
            return None
            
        st.error(f"AI 호출 오류: {e}")
        return None

# --- UI 레이아웃 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        border-radius: 10px !important;
        padding: 12px !important;
        margin-bottom: 5px;
        width: 100%;
        border: 1px solid #eee !important;
        background-color: white !important;
        transition: 0.2s;
    }
    div.stButton > button:hover {
        border-color: #ff4b4b !important;
    }
    div.stButton > button:has(div:contains("🏆")) {
        background-color: #fff9e6 !important;
        border: 2px solid #FFD700 !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 데이터 크롤링 ---
@st.cache_data(ttl=600)
def fetch_popular_news():
    try:
        url = "https://news.naver.com/main/ranking/popularDay.naver"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        news_items = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    news_items.append({"title": a.text.strip(), "link": a['href']})
        return news_items[:30]
    except:
        return []

def get_body_text(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
        return content.get_text(strip=True) if content else "본문 수집 불가"
    except:
        return "데이터 수집 에러"

# --- 메인 화면 구성 ---
st.title("👑 VIRAL MASTER PRO v2.6")

tab_news, tab_build = st.tabs(["🔥 황금소재 탐색", "📸 분석 & 원고 제작"])

current_news_list = fetch_popular_news()

with tab_news:
    if current_news_list:
        # S급 소재 자동 필터링
        if "s_indices_list" not in st.session_state:
            with st.spinner("🚀 AI가 실시간 떡상 소재를 선별하는 중..."):
                titles_blob = "\n".join([f"{idx}:{n['title'][:30]}" for idx, n in enumerate(current_news_list)])
                selection_prompt = f"다음 뉴스 중 유튜브 조회수가 대폭발할 소재 5개 번호만 골라줘. [1,2,3] 형식으로 답변.\n{titles_blob}"
                selection_res = get_ai_response(selection_prompt)
                if selection_res:
                    try:
                        found_match = re.search(r"\[.*\]", selection_res.text)
                        st.session_state.s_indices_list = json.loads(found_match.group()) if found_match else []
                    except:
                        st.session_state.s_indices_list = []
                else:
                    st.session_state.s_indices_list = []

        c1, c2 = st.columns([1, 1])

        with c1:
            st.subheader("📰 실시간 랭킹 뉴스")
            if st.button("🔄 리스트 새로고침"):
                st.cache_data.clear()
                if "s_indices_list" in st.session_state: del st.session_state.s_indices_list
                st.rerun()

            for idx, item in enumerate(current_news_list):
                is_viral = idx in st.session_state.get('s_indices_list', [])
                btn_txt = f"🏆 [S급 소재] {item['title']}" if is_viral else f"[{idx+1}] {item['title']}"
                
                if st.button(btn_txt, key=f"news_{idx}"):
                    with st.spinner("분석 중..."):
                        full_txt = get_body_text(item['link'])
                        analysis_res = get_ai_response(f"기사 분석(썸네일 카피 3개, 요약 1줄):\n{full_txt[:1000]}")
                        st.session_state.viewer = {
                            "title": item['title'],
                            "body": full_txt,
                            "analysis": analysis_res.text if analysis_res else "분석 일시적 오류",
                            "is_viral": is_viral
                        }

        with c2:
            if "viewer" in st.session_state:
                v_data = st.session_state.viewer
                st.markdown(f"### {'🔥 S급 황금소재' if v_data['is_viral'] else '📊 일반 소재'}")
                st.success(v_data['analysis'])
                st.divider()
                st.text_area("기사 본문 데이터", v_data['body'], height=400)
            else:
                st.info("왼쪽 기사를 클릭하여 분석을 시작하세요.")

with tab_build:
    st.header("📸 캡처본 분석 및 원고 빌더")
    img_file = st.file_uploader("커뮤니티/타채널 캡처본 업로드", type=["png", "jpg", "jpeg"])
    
    if img_file:
        pil_img = PIL.Image.open(img_file)
        st.image(pil_img, caption="업로드 이미지", use_container_width=True)
        if st.button("🔍 이미지 AI 분석 시작"):
            with st.spinner("이미지 텍스트 읽는 중..."):
                img_res = get_ai_response("이 이미지의 텍스트를 읽고 유튜브 소재로서 가치를 분석해줘.", is_image=True, image_input=pil_img)
                if img_res: st.info(img_res.text)
    
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        title_in = st.text_input("💎 영상 제목")
        fact_in = st.text_area("📰 핵심 팩트", height=200)
    with col_r:
        target_in = st.text_input("📺 참고 URL")
        opinion_in = st.text_area("💬 시청자 반응", height=200)

    if st.button("🔥 클로드용 프롬프트 생성"):
        if title_in and fact_in:
            st.code(f"유튜브 작가 페르소나 적용.\n제목: {title_in}\n팩트: {fact_in}\n참고: {target_in}\n여론: {opinion_in}", language="markdown")
