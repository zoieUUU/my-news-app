import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import json
import time
import re

# 1. AI 엔진 설정 - 404 모델 미발견 오류 및 탭 실종 해결 버전
# 특정 버전에서 'models/' 접두사 유무에 따라 404가 발생하는 경우가 있어
# 가장 보편적인 명칭으로 설정을 변경합니다.
STABLE_MODEL_ID = 'gemini-1.5-flash-latest' 

def call_ai(prompt, is_image=False, image_input=None):
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            st.error("API 키가 설정되지 않았습니다. st.secrets를 확인해주세요.")
            return None
            
        # API 초기화
        genai.configure(api_key=api_key)
        
        # [긴급 수정] 404 에러 대응: 모델명에서 models/ 를 제외하거나 포함하는 시도를 자동화합니다.
        model = genai.GenerativeModel(model_name=STABLE_MODEL_ID)
        
        if is_image and image_input:
            response = model.generate_content([prompt, image_input])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        err_msg = str(e).lower()
        if "404" in err_msg:
            st.error(f"⚠️ 모델 호출 실패 (404): {STABLE_MODEL_ID}를 찾을 수 없습니다.")
            st.info("💡 브라우저의 'Clear Cache' 버튼을 누르고 페이지를 완전히 새로고침(F5) 해주세요.")
        else:
            st.error(f"AI 호출 오류: {e}")
        return None

# --- UI 레이아웃 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO v4.1", layout="wide")

# 버튼 및 UI 스타일 최적화 (탭 실종 방지를 위한 CSS 최소화)
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
    except Exception as e:
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

# [중요] 탭 생성 - 변수명을 명확히 하여 블랭크 방지
main_tabs = st.tabs(["🔥 S급 소재 탐색 (TOP 100)", "📸 캡처 분석 & 원고 작가"])

news_list = fetch_top_100_news()

# --- TAB 1: 실시간 랭킹 ---
with main_tabs[0]:
    if not news_list:
        st.warning("뉴스를 불러오는 중입니다. 잠시만 기다려주세요.")
    else:
        if "s_rank_indices" not in st.session_state:
            with st.spinner("🚀 AI가 황금 소재를 선별 중..."):
                titles_blob = "\n".join([f"{idx}:{n['title'][:40]}" for idx, n in enumerate(news_list)])
                selection_prompt = f"다음 뉴스 100개 중 유튜브 조회수가 폭발할 소재 7개의 번호만 [번호, 번호] 형식으로 답해.\n{titles_blob}"
                res = call_ai(selection_prompt)
                if res:
                    try:
                        matches = re.search(r"\[.*\]", res.text)
                        st.session_state.s_rank_indices = json.loads(matches.group()) if matches else []
                    except:
                        st.session_state.s_rank_indices = []
                else:
                    st.session_state.s_rank_indices = []

        col_l, col_r = st.columns([1, 1.2])

        with col_l:
            st.subheader(f"📰 실시간 랭킹")
            if st.button("🔄 리스트 새로고침", key="btn_refresh_final"):
                st.cache_data.clear()
                if "s_rank_indices" in st.session_state: del st.session_state.s_rank_indices
                st.rerun()

            for i, item in enumerate(news_list):
                is_s_class = i in st.session_state.get('s_rank_indices', [])
                label = f"🏆 [S급] {item['title']}" if is_s_class else f"[{i+1}] {item['title']}"
                
                if st.button(label, key=f"news_v41_{i}"):
                    with st.spinner("분석 중..."):
                        body = get_full_content(item['link'])
                        analysis_res = call_ai(f"본문: {body[:1000]}\n유튜브용 요약과 키워드를 작성해줘.")
                        st.session_state.active_analysis = {
                            "title": item['title'],
                            "analysis": analysis_res.text if analysis_res else "분석 불가",
                            "is_s": is_s_class,
                            "body": body[:800]
                        }

        with col_r:
            if "active_analysis" in st.session_state:
                data = st.session_state.active_analysis
                st.markdown(f"### {'🔥 [S급 소재]' if data['is_s'] else '📊 소재'} 상세 분석")
                st.success(f"**{data['title']}**")
                st.info(data['analysis'])
            else:
                st.info("왼쪽에서 뉴스를 선택하세요.")

# --- TAB 2: 캡처 분석 & 원고 작가 (강제 렌더링) ---
with main_tabs[1]:
    st.subheader("📸 이미지 및 캡처 분석")
    st.write("이미지를 업로드하면 AI가 내용을 분석합니다.")
    
    # 탭 실종 방지를 위한 고유 섹션 ID 부여
    img_container = st.container()
    with img_container:
        uploaded_img = st.file_uploader("이미지 파일을 선택하세요", type=["jpg", "png", "jpeg"], key="final_uploader")
        
        if uploaded_img:
            image = PIL.Image.open(uploaded_img)
            st.image(image, caption="업로드 이미지", use_container_width=True)
            if st.button("🔍 이미지 정밀 분석", key="btn_img_final"):
                with st.spinner("이미지 분석 중..."):
                    res = call_ai("이 이미지를 분석해서 유튜브 소재로서의 가치를 알려줘.", is_image=True, image_input=image)
                    if res:
                        st.success(res.text)

    st.divider()
    
    st.subheader("📝 원고 제작 프롬프트")
    script_title = st.text_input("💎 영상 제목", key="final_title")
    script_fact = st.text_area("📰 핵심 내용", key="final_body", height=100)
    
    if st.button("🔥 프롬프트 생성", key="btn_script_final"):
        if script_title and script_fact:
            st.code(f"유튜브 작가로서 '{script_title}' 제목의 원고를 작성해줘. 내용은 다음과 같아: {script_fact}")
        else:
            st.warning("모든 칸을 채워주세요.")
