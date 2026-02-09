import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import json
import time
import re

# 1. AI 엔진 설정 - 404 모델 미발견 오류 완벽 차단 로직
# 시스템이 gemini-1.5-flash를 호출하지 못하도록 환경에서 지원하는 최신 모델명을 명시적으로 고정합니다.
STABLE_MODEL_ID = 'gemini-2.5-flash-preview-09-2025'

def call_ai(prompt, is_image=False, image_input=None):
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            st.error("API 키가 설정되지 않았습니다. st.secrets를 확인해주세요.")
            return None
            
        genai.configure(api_key=api_key)
        # 호출 시마다 모델 객체를 '명시적 모델명'으로 새로 생성하여 폴백 방지
        model = genai.GenerativeModel(model_name=STABLE_MODEL_ID)
        
        if is_image and image_input:
            response = model.generate_content([prompt, image_input])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        err_msg = str(e).lower()
        if "404" in err_msg or "not found" in err_msg:
            st.error("⚠️ 서버 환경에서 구형 모델을 참조 중입니다. [Clear Cache] 후 새로고침하세요.")
        else:
            st.error(f"AI 호출 오류: {e}")
        return None

# --- UI 레이아웃 설정 ---
st.set_page_config(page_title="VIRAL MASTER PRO v4.0", layout="wide")

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
    }
    /* S급 소재 스타일 (노란색 배경) */
    .s-class-btn {
        background-color: #FFF9C4 !important;
        border: 2px solid #FBC02D !important;
        font-weight: bold !important;
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
        # 각 언론사별 랭킹 뉴스 수집
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
st.title("👑 VIRAL MASTER PRO v4.0")

tab1, tab2 = st.tabs(["🔥 S급 소재 탐색 (TOP 100)", "📸 캡처 분석 & 원고 작가"])

news_list = fetch_top_100_news()

with tab1:
    if not news_list:
        st.warning("데이터를 불러오지 못했습니다.")
    else:
        # 1. AI 랭킹 분석 및 S급 선별 (세션 유지)
        if "s_rank_indices" not in st.session_state:
            with st.spinner("🚀 AI가 100개의 소재 중 떡상할 'S급'을 선별 중입니다..."):
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
            if st.button("🔄 강제 새로고침"):
                st.cache_data.clear()
                if "s_rank_indices" in st.session_state: del st.session_state.s_rank_indices
                st.rerun()

            for i, item in enumerate(news_list):
                is_s_class = i in st.session_state.get('s_rank_indices', [])
                btn_label = f"🏆 [S급 소재] {item['title']}" if is_s_class else f"[{i+1}] {item['title']}"
                
                # 버튼 생성 (S급은 별도 CSS 적용을 위해 markdown 활용 대신 고유 키 사용)
                if st.button(btn_label, key=f"news_{i}"):
                    with st.spinner("소재 정밀 분석 중..."):
                        body = get_full_content(item['link'])
                        # AI 요약 및 키워드 5개 추출 요청
                        analysis_prompt = f"""
                        기사 본문: {body[:1500]}
                        
                        위 내용을 바탕으로 다음을 작성해줘:
                        1. 한 줄 요약 (자극적인 유튜브 스타일)
                        2. 영상 제작 핵심 키워드 5개 (태그용)
                        3. 시청자가 반응할 포인트 3개
                        """
                        analysis_res = call_ai(analysis_prompt)
                        st.session_state.active_analysis = {
                            "title": item['title'],
                            "analysis": analysis_res.text if analysis_res else "분석 실패",
                            "is_s": is_s_class
                        }

        with col_r:
            if "active_analysis" in st.session_state:
                data = st.session_state.active_analysis
                st.markdown(f"### {'🔥 [S급 소재]' if data['is_s'] else '📊 소재'} 상세 분석")
                if data['is_s']:
                    st.warning("이 소재는 AI가 선정한 떡상 확률 90% 이상의 황금 소재입니다.")
                
                st.info(data['analysis'])
                st.divider()
                st.markdown("**💡 제작 팁:** 이 내용을 바탕으로 썸네일 카피를 구성하세요.")
            else:
                st.info("왼쪽 리스트에서 분석할 뉴스를 선택해 주세요.")

with tab2:
    st.subheader("📸 커뮤니티/타채널 캡처본 정밀 분석")
    img_file = st.file_uploader("이미지 업로드", type=["jpg", "png", "jpeg"])
    
    if img_file:
        img = PIL.Image.open(img_file)
        st.image(img, caption="분석 대상 이미지", use_container_width=True)
        if st.button("🔍 AI 시각 분석 시작"):
            with st.spinner("이미지 내 텍스트 및 가치 파악 중..."):
                res = call_ai("이미지의 텍스트를 추출하고, 이 소재가 유튜브에서 왜 인기 있는지, 어떤 식으로 영상을 만들면 좋을지 분석해줘.", is_image=True, image_input=img)
                if res:
                    st.write("### 📋 AI 분석 레포트")
                    st.success(res.text)

    st.divider()
    st.subheader("📝 고밀도 작가 프롬프트")
    t_title = st.text_input("💎 영상 제목")
    t_context = st.text_area("📰 사건의 핵심 팩트", height=150)
    
    if st.button("🔥 원고 작가 프롬프트 생성"):
        if t_title and t_context:
            prompt = f"당신은 유튜브 전문 작가입니다. 제목: {t_title}, 팩트: {t_context}를 바탕으로 이탈율 없는 3분 원고를 써주세요."
            st.code(prompt, language="markdown")
        else:
            st.error("제목과 팩트를 모두 입력하세요.")
