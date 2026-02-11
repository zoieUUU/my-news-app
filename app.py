import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import json
import time
import re

# 1. AI 엔진 설정 - 가용 모델 동적 확인 로직 (404 방지)
def get_valid_model_path():
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key: return None
        genai.configure(api_key=api_key)
        
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        priority_targets = [
            "models/gemini-2.0-flash-exp",
            "models/gemini-1.5-flash-latest",
            "models/gemini-1.5-flash",
            "models/gemini-pro"
        ]
        
        for target in priority_targets:
            if target in available_models:
                return target
        
        for m_name in available_models:
            if "flash" in m_name.lower():
                return m_name
        return available_models[0] if available_models else None
    except Exception:
        return "models/gemini-1.5-flash-latest"

def call_ai(prompt, is_image=False, image_input=None):
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            st.error("API 키가 설정되지 않았습니다.")
            return None
        genai.configure(api_key=api_key)
        
        if "verified_model_path" not in st.session_state:
            st.session_state.verified_model_path = get_valid_model_path()
        
        model = genai.GenerativeModel(model_name=st.session_state.verified_model_path)
        
        if is_image and image_input:
            response = model.generate_content([prompt, image_input])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        st.error(f"AI 호출 오류: {e}")
        return None

# --- UI 레이아웃 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO v4.1", layout="wide")

st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        border-radius: 8px !important;
        padding: 10px !important;
        width: 100%;
        border: 1px solid #ddd !important;
        margin-bottom: 5px;
    }
    div.stButton > button:contains("🏆") {
        background-color: #FFF9C4 !important;
        border: 2px solid #FBC02D !important;
    }
    .main-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
    }
    .content-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1d3557;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 데이터 수집 함수 ---
@st.cache_data(ttl=600)
def fetch_top_100_news():
    try:
        url = "https://news.naver.com/main/ranking/popularDay.naver"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_items = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    news_items.append({"title": a.text.strip(), "link": a['href']})
        return news_items[:100]
    except Exception:
        return []

def get_full_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
        return content.get_text(strip=True) if content else "본문 수집 불가"
    except:
        return "연결 실패"

# --- 메인 대시보드 ---
st.title("👑 VIRAL MASTER PRO v4.1")

tabs = st.tabs(["🔥 S급 소재 탐색 (TOP 100)", "📸 캡처 분석 & 원고 작가"])

news_list = fetch_top_100_news()

# --- TAB 1: 실시간 랭킹 ---
with tabs[0]:
    if not news_list:
        st.warning("뉴스를 불러오는 중입니다...")
    else:
        # S급 소재 자동 선별
        if "s_rank_indices" not in st.session_state:
            with st.spinner("🚀 AI 가용 모델 확인 및 소재 선별 중..."):
                titles_blob = "\n".join([f"{idx}:{n['title'][:40]}" for idx, n in enumerate(news_list)])
                selection_prompt = f"다음 뉴스 100개 중 유튜브 조회수가 폭발할 소재 7개의 번호만 [번호, 번호] 형식으로 답해.\n{titles_blob}"
                res = call_ai(selection_prompt)
                if res:
                    try:
                        matches = re.search(r"\[.*\]", res.text)
                        st.session_state.s_rank_indices = json.loads(matches.group()) if matches else []
                    except:
                        st.session_state.s_rank_indices = []

        col_l, col_r = st.columns([1, 1.2])

        with col_l:
            st.subheader("📰 실시간 랭킹")
            if st.button("🔄 리스트 새로고침", key="refresh_news"):
                st.cache_data.clear()
                for key in ["s_rank_indices", "active_analysis"]:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()

            for i, item in enumerate(news_list):
                is_s_class = i in st.session_state.get('s_rank_indices', [])
                label = f"🏆 [S급] {item['title']}" if is_s_class else f"[{i+1}] {item['title']}"
                
                if st.button(label, key=f"news_btn_{i}"):
                    with st.spinner("전문 분석 및 본문 추출 중..."):
                        body = get_full_content(item['link'])
                        # AI 분석 요청 (요약 + 키워드 5개 명시)
                        analysis_prompt = (
                            f"기사본문: {body[:1500]}\n\n"
                            "위 내용을 바탕으로 유튜브 쇼츠나 영상 소재로 사용할 수 있게 다음 형식으로 작성해줘:\n"
                            "1. [유튜브 요약]: 시청자의 시선을 끄는 강렬한 요약문 3문장\n"
                            "2. [핵심 키워드]: # 포함 키워드 5개"
                        )
                        analysis_res = call_ai(analysis_prompt)
                        st.session_state.active_analysis = {
                            "title": item['title'],
                            "analysis": analysis_res.text if analysis_res else "분석 실패",
                            "is_s": is_s_class,
                            "body": body,
                            "link": item['link']
                        }

        with col_r:
            if "active_analysis" in st.session_state:
                data = st.session_state.active_analysis
                
                # 상단 분석 영역
                st.markdown(f"### {'🔥 [S급 소재]' if data['is_s'] else '📊 소재'} 상세 분석")
                st.success(f"**제목: {data['title']}**")
                
                with st.container():
                    st.markdown("<div class='main-box'>", unsafe_allow_html=True)
                    st.markdown("#### 📺 유튜브용 요약 및 키워드")
                    st.info(data['analysis'])
                    st.markdown("</div>", unsafe_allow_html=True)
                
                st.divider()
                
                # 하단 원문 영역
                st.markdown("#### 📝 기사 원문 추출")
                st.link_button("🔗 네이버 뉴스 원문 보기", data['link'])
                with st.expander("본문 전체 내용 보기", expanded=True):
                    st.write(data['body'])
                
                if "verified_model_path" in st.session_state:
                    st.caption(f"Engine: {st.session_state.verified_model_path}")
            else:
                st.info("왼쪽 뉴스 리스트에서 분석할 기사를 선택하세요.")

# --- TAB 2: 캡처 분석 & 원고 작가 ---
with tabs[1]:
    st.subheader("📸 이미지 및 캡처 분석")
    uploaded_img = st.file_uploader("이미지 파일을 선택하세요", type=["jpg", "png", "jpeg"], key="img_up")
    
    if uploaded_img:
        image = PIL.Image.open(uploaded_img)
        st.image(image, caption="업로드 이미지", use_container_width=True)
        if st.button("🔍 이미지 정밀 분석", key="img_anal"):
            with st.spinner("이미지 분석 중..."):
                res = call_ai("이 이미지를 분석해서 유튜브 소재로서의 가치를 알려주고, 영상 기획 아이디어를 제안해줘.", is_image=True, image_input=image)
                if res:
                    st.success(res.text)

    st.divider()
    st.subheader("📝 원고 제작 프롬프트")
    script_title = st.text_input("💎 영상 제목", key="sc_title")
    script_fact = st.text_area("📰 핵심 내용", key="sc_body", height=100)
    
    if st.button("🔥 프롬프트 생성", key="sc_btn"):
        if script_title and script_fact:
            prompt_code = f"유튜브 전문 작가로서 '{script_title}'을 주제로 원고를 써줘. 핵심 내용은 다음과 같아: {script_fact}. 시청자가 끝까지 보게끔 자극적이고 흥미롭게 구성해줘."
            st.code(prompt_code)
        else:
            st.warning("제목과 내용을 입력해 주세요.")
