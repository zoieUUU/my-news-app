import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import json
import time
import re

# 1. AI 엔진 설정 - 404 에러 및 모델 불일치 해결을 위한 정적 설정
# Canvas 환경에서 가장 안정적인 2.5-flash-preview 모델로 강제 고정합니다.
STABLE_MODEL_NAME = 'gemini-2.5-flash-preview-09-2025'

def call_ai_api(prompt, is_image=False, image_input=None):
    """
    모든 API 호출 시점에 모델 이름을 명시적으로 주입하여 
    시스템이 1.5-flash를 찾으려고 시도하는 버그를 원천 차단합니다.
    """
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            st.error("API Key not found in secrets.")
            return None
            
        genai.configure(api_key=api_key)
        
        # 호출 시마다 명시적으로 모델 객체를 생성하여 폴백(Fallback) 방지
        model = genai.GenerativeModel(model_name=STABLE_MODEL_NAME)
        
        if is_image and image_input:
            response = model.generate_content([prompt, image_input])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        err_str = str(e).lower()
        if "404" in err_str:
            st.error("⚠️ 시스템 환경 오류: 구형 모델 캐시 감지. [Clear Cache] 버튼을 클릭해 주세요.")
        elif "429" in err_str:
            st.warning("⏳ API 호출 한도 초과. 잠시 후 다시 시도해 주세요.")
        else:
            st.error(f"API Error: {e}")
        return None

# --- UI 레이아웃 및 스타일 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO v3.0", layout="wide")

# 버튼 및 탭 스타일 최적화
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 2rem;
    }
    div.stButton > button {
        text-align: left !important;
        border-radius: 12px !important;
        padding: 15px !important;
        margin-bottom: 8px;
        width: 100%;
        border: 1px solid #e0e0e0 !important;
        background-color: #ffffff !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        border-color: #ff4b4b !important;
        background-color: #fffafa !important;
    }
    div.stButton > button:has(div:contains("🏆")) {
        background-color: #fff9e6 !important;
        border: 2px solid #FFD700 !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 데이터 크롤링 및 수집 함수 ---
@st.cache_data(ttl=600)
def fetch_naver_popular_news():
    try:
        url = "https://news.naver.com/main/ranking/popularDay.naver"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_list = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    news_list.append({"title": a.text.strip(), "link": a['href']})
        return news_list[:30]
    except Exception as e:
        st.error(f"News Fetch Error: {e}")
        return []

def get_article_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
        return content.get_text(strip=True) if content else "본문을 가져올 수 없습니다."
    except:
        return "데이터 연결 오류"

# --- 메인 비즈니스 로직 ---
st.title("👑 VIRAL MASTER PRO v3.0")

# 탭이 증발하는 문제를 해결하기 위해 명시적으로 정의
tabs = st.tabs(["🔥 황금소재 탐색기", "📸 캡처분석 & 원고 작가"])

news_data = fetch_naver_popular_news()

# TAB 1: 실시간 뉴스 분석
with tabs[0]:
    if not news_data:
        st.warning("데이터를 불러오지 못했습니다. 새로고침을 해주세요.")
    else:
        # S급 소재 선정 로직
        if "viral_picks" not in st.session_state:
            with st.spinner("🚀 AI가 대박 소재 선별 중..."):
                titles_text = "\n".join([f"{i}:{n['title'][:30]}" for i, n in enumerate(news_data)])
                prompt = f"다음 뉴스 제목 중 유튜브 조회수가 터질만한 5개 번호만 골라줘. 반드시 [1,2,3] 형식으로 번호만 출력해.\n{titles_text}"
                res = call_ai_api(prompt)
                if res:
                    try:
                        matches = re.search(r"\[.*\]", res.text)
                        st.session_state.viral_picks = json.loads(matches.group()) if matches else []
                    except:
                        st.session_state.viral_picks = []
                else:
                    st.session_state.viral_picks = []

        col_list, col_view = st.columns([1, 1.2])

        with col_list:
            st.subheader("📰 오늘의 랭킹 뉴스")
            if st.button("🔄 리스트 & AI 엔진 강제 초기화"):
                st.cache_data.clear()
                if "viral_picks" in st.session_state: del st.session_state.s_indices_list
                st.rerun()

            for i, news in enumerate(news_data):
                is_viral = i in st.session_state.get('viral_picks', [])
                label = f"🏆 [S급] {news['title']}" if is_viral else f"[{i+1}] {news['title']}"
                
                if st.button(label, key=f"news_btn_{i}"):
                    with st.spinner("소재 정밀 분석 중..."):
                        body = get_article_content(news['link'])
                        analysis = call_ai_api(f"다음 기사의 1.썸네일 카피 3개 2.핵심 요약 1줄을 작성해줘:\n{body[:1000]}")
                        st.session_state.detail_info = {
                            "title": news['title'],
                            "body": body,
                            "analysis": analysis.text if analysis else "분석 결과 생성 중 오류가 발생했습니다.",
                            "is_viral": is_viral
                        }

        with col_view:
            if "detail_info" in st.session_state:
                di = st.session_state.detail_info
                st.markdown(f"### {'🔥 S급 황금 소재 분석' if di['is_viral'] else '📊 소재 분석 결과'}")
                st.success(di['analysis'])
                st.divider()
                st.markdown("**📄 원문 데이터 (복사용)**")
                st.text_area("Article Body", di['body'], height=450)
            else:
                st.info("왼쪽 뉴스 리스트에서 분석할 소재를 선택해 주세요.")

# TAB 2: 이미지 분석 및 원고 제작
with tabs[1]:
    st.subheader("📸 커뮤니티/타채널 캡처본 정밀 분석")
    st.write("인기글 목록이나 타 채널의 제목 리스트를 캡처해서 올려주세요.")
    
    img_upload = st.file_uploader("이미지 파일 업로드 (JPG, PNG)", type=["jpg", "png", "jpeg"])
    
    if img_upload:
        img_obj = PIL.Image.open(img_upload)
        st.image(img_obj, caption="업로드된 캡처본", use_container_width=True)
        
        if st.button("🔍 AI 시각 분석 시작"):
            with st.spinner("이미지의 텍스트와 맥락을 파악 중..."):
                img_res = call_ai_api("이 이미지에 있는 모든 텍스트를 추출하고, 유튜브 소재로서의 가치와 추천 전략을 분석해줘.", is_image=True, image_input=img_obj)
                if img_res:
                    st.write("### 📋 AI 분석 레포트")
                    st.info(img_res.text)
    
    st.divider()
    st.subheader("📝 고밀도 원고 프롬프트 생성기")
    
    col_a, col_b = st.columns(2)
    with col_a:
        inp_title = st.text_input("💎 타겟 제목", placeholder="조회수 터질만한 제목 입력")
        inp_fact = st.text_area("📰 핵심 팩트/사건", height=200, placeholder="뉴스 본문이나 팩트 나열")
    with col_b:
        inp_ref = st.text_input("📺 참고 채널/URL", placeholder="벤치마킹할 채널")
        inp_react = st.text_area("💬 커뮤니티/댓글 여론", height=200, placeholder="시청자가 보일만한 반응들")

    if st.button("🔥 100만 작가 프롬프트 추출"):
        if inp_title and inp_fact:
            final_p = f"""당신은 유튜브 100만 채널 전문 작가입니다.
아래 데이터를 바탕으로 시청자 이탈율을 최소화하는 원고를 작성하세요.

1. 영상 제목: {inp_title}
2. 핵심 팩트: {inp_fact}
3. 벤치마킹 타겟: {inp_ref}
4. 예상 여론: {inp_react}

작성 지침: 첫 10초에 시청자의 흥미를 폭발시키고, 사실 관계를 드라마틱하게 재구성하세요."""
            st.code(final_p, language="markdown")
            st.success("위 프롬프트를 복사하여 클로드(Claude)나 GPT에 입력하세요.")
        else:
            st.error("제목과 핵심 팩트는 필수 입력 항목입니다.")
