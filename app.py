import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import json
import time
import re

# 1. AI 엔진 설정 - 404 모델 미발견 오류 완벽 차단 로직
# 구형 gemini-1.5-flash의 경로가 꼬이는 문제를 해결하기 위해 
# 현재 가장 안정적으로 2.0 성능을 제공하는 'gemini-2.0-flash-exp'를 사용합니다.
STABLE_MODEL_ID = 'gemini-2.0-flash-exp' 

def call_ai(prompt, is_image=False, image_input=None):
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            st.error("API 키가 설정되지 않았습니다. st.secrets를 확인해주세요.")
            return None
            
        # API 초기화
        genai.configure(api_key=api_key)
        
        # [핵심] 404 에러 원천 봉쇄: 
        # 라이브러리가 기본값인 'gemini-1.5-flash'로 폴백(Fallback)되지 않도록 
        # 명시적으로 'models/gemini-2.0-flash-exp' 경로를 지정합니다.
        model_name = f"models/{STABLE_MODEL_ID}"
        model = genai.GenerativeModel(model_name=model_name)
        
        if is_image and image_input:
            response = model.generate_content([prompt, image_input])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        err_msg = str(e).lower()
        if "404" in err_msg or "not found" in err_msg:
            st.error(f"⚠️ 모델 경로 오류: 시스템이 '{STABLE_MODEL_ID}'을 찾지 못했습니다.")
            st.info("💡 모델명이 'gemini-1.5-flash'로 표시된다면 캐시 문제입니다. Clear Cache 후 새로고침하세요.")
        else:
            st.error(f"AI 호출 오류: {e}")
        return None

# --- UI 레이아웃 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO v4.1", layout="wide")

# 버튼 및 UI 스타일 최적화
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
    /* S급 소재 강조 스타일 */
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

# 탭 생성
tabs = st.tabs(["🔥 S급 소재 탐색 (TOP 100)", "📸 캡처 분석 & 원고 작가"])

news_list = fetch_top_100_news()

# --- TAB 1: 실시간 랭킹 ---
with tabs[0]:
    if not news_list:
        st.warning("데이터를 불러오는 중이거나 수집에 실패했습니다.")
    else:
        # S급 선별 세션 관리
        if "s_rank_indices" not in st.session_state:
            with st.spinner("🚀 AI가 황금 소재를 선별 중입니다..."):
                titles_blob = "\n".join([f"{idx}:{n['title'][:40]}" for idx, n in enumerate(news_list)])
                selection_prompt = f"다음 뉴스 100개 중 유튜브 조회수가 폭발할 소재 7개의 번호만 골라줘. [번호1, 번호2] 형식으로 답해.\n{titles_blob}"
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
            st.subheader(f"📰 실시간 랭킹 뉴스")
            if st.button("🔄 리스트 갱신", key="refresh_v4_2"):
                st.cache_data.clear()
                if "s_rank_indices" in st.session_state: del st.session_state.s_rank_indices
                st.rerun()

            for i, item in enumerate(news_list):
                is_s_class = i in st.session_state.get('s_rank_indices', [])
                btn_label = f"🏆 [S급 소재] {item['title']}" if is_s_class else f"[{i+1}] {item['title']}"
                
                if st.button(btn_label, key=f"news_btn_v42_{i}"):
                    with st.spinner("본문 분석 중..."):
                        body = get_full_content(item['link'])
                        analysis_prompt = f"기사 본문: {body[:1500]}\n위 내용을 바탕으로 유튜브용 한줄 요약, 핵심 키워드 5개, 시청자 반응 포인트를 분석해줘."
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
                st.markdown(f"### {'🔥 [S급 소재]' if data['is_s'] else '📊 소재'} 분석 결과")
                st.success(f"**제목:** {data['title']}")
                st.info(data['analysis'])
                with st.expander("📄 본문 내용 확인"):
                    st.write(data['body'])
            else:
                st.info("왼쪽 뉴스 목록에서 분석할 기사를 선택하세요.")

# --- TAB 2: 캡처 분석 & 원고 작가 ---
with tabs[1]:
    st.subheader("📸 이미지 기반 전략 분석")
    st.write("스크린샷이나 이미지 소재를 업로드하여 AI의 정밀 분석을 받아보세요.")
    
    img_file = st.file_uploader("분석할 이미지 업로드", type=["jpg", "png", "jpeg"], key="v42_img_uploader")
    
    if img_file:
        try:
            img = PIL.Image.open(img_file)
            st.image(img, caption="업로드된 소재", use_container_width=True)
            
            if st.button("🔍 이미지 AI 분석 실행", key="v42_img_btn"):
                with st.spinner("AI가 이미지를 읽고 있습니다..."):
                    img_res = call_ai("이 이미지의 텍스트와 내용을 분석해서 유튜브 기획 방향을 제시해줘.", is_image=True, image_input=img)
                    if img_res:
                        st.markdown("### 📋 분석 레포트")
                        st.success(img_res.text)
        except Exception as e:
            st.error(f"이미지 로딩 오류: {e}")

    st.divider()
    
    st.subheader("📝 맞춤형 원고 빌더")
    v_title = st.text_input("💎 제목 (가제)", key="v42_script_title")
    v_body = st.text_area("📰 참고 내용 / 팩트", height=150, key="v42_script_body")
    
    if st.button("🔥 원고 프롬프트 생성", key="v42_script_btn"):
        if v_title and v_body:
            prompt = f"당신은 전문 유튜브 작가입니다. 제목: {v_title}, 내용: {v_body}를 바탕으로 시청자를 끝까지 잡아두는 원고를 써주세요."
            st.code(prompt, language="markdown")
            st.info("위 프롬프트를 복사해 Claude나 ChatGPT 등에 사용하세요.")
        else:
            st.warning("제목과 내용을 입력해주세요.")
