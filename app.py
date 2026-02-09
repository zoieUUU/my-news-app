import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import json
import time
import re

# 1. AI 엔진 설정 - 404 모델 미발견 오류 완벽 차단 로직
# 모델 업데이트 정보 및 사용자 피드백에 따라 가장 안정적인 최신 명칭을 사용합니다.
# 1.5-flash-latest는 구형 버전 폐기 후 권장되는 안정적인 엔드포인트입니다.
STABLE_MODEL_ID = 'gemini-1.5-flash-latest' 

def call_ai(prompt, is_image=False, image_input=None):
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            st.error("API 키가 설정되지 않았습니다. st.secrets를 확인해주세요.")
            return None
            
        # API 초기화
        genai.configure(api_key=api_key)
        
        # [중요] 호출 시마다 모델 객체를 최신 모델명으로 새로 생성합니다.
        # models/ 접두사를 명시하여 v1beta 환경에서도 정확한 모델을 찾도록 강제합니다.
        model_name = f"models/{STABLE_MODEL_ID}"
        model = genai.GenerativeModel(model_name=model_name)
        
        if is_image and image_input:
            response = model.generate_content([prompt, image_input])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        err_msg = str(e).lower()
        # 404 에러 발생 시 최신 모델 목록 확인 제안 및 해결 방법 안내
        if "404" in err_msg or "not found" in err_msg:
            st.error(f"⚠️ 모델 미지원 오류: {STABLE_MODEL_ID} 모델을 찾을 수 없습니다.")
            st.info("💡 해결 방법: 우측 상단 'Clear Cache' 클릭 후 새로고침하거나, 앱 설정에서 모델명을 'gemini-2.0-flash-exp'로 변경해 보세요.")
        else:
            st.error(f"AI 호출 오류: {e}")
        return None

# --- UI 레이아웃 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO v4.1", layout="wide")

# S급 소재 하이라이트 스타일
st.markdown("""
    <style>
    div.stButton > button {
        text-align: left !important;
        border-radius: 8px !important;
        padding: 10px !important;
        width: 100%;
        border: 1px solid #ddd !important;
        margin-bottom: 5px;
        transition: 0.3s;
    }
    /* S급 소재 강조 (노란색) */
    div.stButton > button:contains("🏆") {
        background-color: #FFF9C4 !important;
        border: 2px solid #FBC02D !important;
        font-weight: bold !important;
    }
    div.stButton > button:hover {
        border-color: #FF4B4B !important;
        background-color: #FFF5F5 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 데이터 수집 (네이버 뉴스 랭킹 100위) ---
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
        st.error(f"뉴스 수집 실패: {e}")
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

# 탭 변수 할당
tabs = st.tabs(["🔥 S급 소재 탐색 (TOP 100)", "📸 캡처 분석 & 원고 작가"])

news_list = fetch_top_100_news()

# --- TAB 1: 실시간 랭킹 및 S급 선별 ---
with tabs[0]:
    if not news_list:
        st.warning("데이터를 불러오지 못했습니다.")
    else:
        if "s_rank_indices" not in st.session_state:
            with st.spinner("🚀 AI가 떡상할 'S급'을 선별 중입니다..."):
                titles_blob = "\n".join([f"{idx}:{n['title'][:40]}" for idx, n in enumerate(news_list)])
                selection_prompt = f"다음 뉴스 100개 중 유튜브 조회수가 대폭발할 소재 7개의 번호만 골라줘. 반드시 [번호1, 번호2] 형식으로만 답해.\n{titles_blob}"
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
            st.subheader(f"📰 실시간 랭킹 (수집: {len(news_list)}개)")
            if st.button("🔄 강제 새로고침", key="refresh_news"):
                st.cache_data.clear()
                if "s_rank_indices" in st.session_state: del st.session_state.s_rank_indices
                st.rerun()

            for i, item in enumerate(news_list):
                is_s_class = i in st.session_state.get('s_rank_indices', [])
                btn_label = f"🏆 [S급 황금소재] {item['title']}" if is_s_class else f"[{i+1}] {item['title']}"
                
                if st.button(btn_label, key=f"news_btn_v4_{i}"):
                    with st.spinner("소재 정밀 분석 중..."):
                        body = get_full_content(item['link'])
                        analysis_prompt = f"""
                        기사 본문: {body[:1500]}
                        
                        위 내용을 바탕으로 다음을 작성해줘:
                        1. 한 줄 요약 (자극적인 유튜브 스타일)
                        2. 영상 제작 핵심 키워드 5개
                        3. 시청자가 반응할 포인트 3개
                        """
                        analysis_res = call_ai(analysis_prompt)
                        st.session_state.active_analysis = {
                            "title": item['title'],
                            "analysis": analysis_res.text if analysis_res else "분석 실패",
                            "is_s": is_s_class,
                            "body": body[:1000]
                        }

        with col_r:
            if "active_analysis" in st.session_state:
                data = st.session_state.active_analysis
                st.markdown(f"### {'🔥 [S급 소재]' if data['is_s'] else '📊 소재'} 상세 분석")
                if data['is_s']:
                    st.warning("이 소재는 AI가 선정한 떡상 확률이 매우 높은 황금 소재입니다.")
                
                st.success(f"**제목:** {data['title']}")
                st.info(data['analysis'])
                with st.expander("📄 기사 본문 요약 보기"):
                    st.write(data['body'])
            else:
                st.info("왼쪽 뉴스 리스트에서 분석할 소재를 선택해 주세요.")

# --- TAB 2: 이미지 분석 및 원고 작가 ---
with tabs[1]:
    st.subheader("📸 캡처본 정밀 분석 및 원고 빌더")
    st.write("커뮤니티 인기글이나 타 채널 성과 지표 캡처본을 분석해 전략을 도출합니다.")
    
    img_file = st.file_uploader("이미지 업로드 (JPG, PNG)", type=["jpg", "png", "jpeg"], key="tab2_v4_uploader")
    
    if img_file:
        img = PIL.Image.open(img_file)
        st.image(img, caption="업로드된 분석 소재", use_container_width=True)
        
        if st.button("🔍 AI 시각 분석 시작", key="img_analysis_btn_v4"):
            with st.spinner("이미지 내 텍스트 및 가치 파악 중..."):
                img_res = call_ai("이미지의 텍스트를 추출하고, 이 소재의 핵심 가치와 유튜브 영상 기획 아이디어를 제안해줘.", is_image=True, image_input=img)
                if img_res:
                    st.write("### 📋 AI 분석 레포트")
                    st.success(img_res.text)

    st.divider()
    st.subheader("📝 고성능 원고 작가 프롬프트")
    
    t_title = st.text_input("💎 영상 제목", placeholder="제목을 입력하세요", key="t_title_v4")
    t_context = st.text_area("📰 핵심 팩트 및 내용", height=150, placeholder="사건의 흐름을 입력하세요.", key="t_context_v4")
    
    if st.button("🔥 고성능 원고 프롬프트 생성", key="prompt_gen_btn_v4"):
        if t_title and t_context:
            prompt_text = f"당신은 유튜브 전문 작가입니다. 제목: {t_title}, 팩트: {t_context}를 바탕으로 이탈 없는 원고를 작성해줘."
            st.code(prompt_text, language="markdown")
        else:
            st.error("제목과 내용을 모두 입력해 주세요.")
