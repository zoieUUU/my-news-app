import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정 - 가장 안정적인 모델명 사용 및 에러 제어 강화
@st.cache_resource
def load_ai_model():
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            # 'gemini-1.5-flash'는 가장 널리 사용되는 안정적인 모델명입니다.
            return genai.GenerativeModel('gemini-1.5-flash')
        else:
            st.error("API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
            return None
    except Exception as e:
        st.error(f"AI 모델 초기화 실패: {e}")
        return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- UI 스타일 커스터마이징 (S급 리스트 강조) ---
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    
    /* 일반 뉴스 버튼 */
    div.stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        border-radius: 10px !important;
        background-color: #ffffff !important;
        border: 1px solid #ddd !important;
        padding: 12px 15px !important;
        margin-bottom: 4px;
        width: 100%;
        transition: all 0.2s ease;
    }
    
    /* S급 뉴스 버튼 (강제 스타일 적용) */
    div.stButton > button[data-testid="stBaseButton-secondary"]:has(div:contains("🏆")) {
        background-color: #fff9e6 !important;
        border: 2px solid #FFD700 !important;
        color: #856404 !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 6px rgba(255, 215, 0, 0.2) !important;
    }

    div.stButton > button:hover {
        border-color: #FF4B4B !important;
        background-color: #fff0f0 !important;
    }

    .analysis-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #eee;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 수집 및 AI 로직 ---
def get_content_safe(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('.article_body')
        if content:
            return content.get_text(separator="\n", strip=True)
        return "본문 내용을 수집할 수 없습니다."
    except Exception as e:
        return f"데이터 수집 에러: {e}"

@st.cache_data(ttl=300)
def fetch_news_list():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_data = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    news_data.append({"title": a.text.strip(), "link": a['href']})
        return news_data[:60]
    except:
        return []

def get_s_class_indices(news_list):
    if not model or not news_list: return []
    titles = "\n".join([f"{i}: {n['title']}" for i, n in enumerate(news_list)])
    prompt = f"""
    당신은 100만 유튜버 기획자입니다.
    다음 뉴스 중 [방산, 반도체, 외신극찬, 국위선양, 일본반응] 등 조회수가 터질 S급 소재 5개의 번호만 리스트로 출력하세요.
    출력 형식: [1, 5, 12, 18, 24]
    뉴스 리스트:
    {titles}
    """
    try:
        response = model.generate_content(prompt)
        # JSON 형식만 추출
        match = re.search(r"\[.*\]", response.text)
        if match:
            return json.loads(match.group())
        return []
    except Exception as e:
        st.sidebar.error(f"AI 선별 실패: {e}")
        return []

# --- 메인 대시보드 ---
st.title("👑 VIRAL MASTER PRO v2.6")
st.caption("실시간 뉴스 랭킹 & S급 소재 자동 판별기")

tab1, tab2 = st.tabs(["🔥 뉴스 리스트", "🎯 대본 마스터"])

with tab1:
    news_items = fetch_news_list()
    
    if news_items:
        # S급 인덱스 생성
        if "s_idx" not in st.session_state:
            with st.spinner('🚀 AI가 떡상 소재를 선별 중...'):
                st.session_state.s_idx = get_s_class_indices(news_items)
        
        s_idx = st.session_state.s_idx
        
        col_list, col_view = st.columns([1.2, 1])
        
        with col_list:
            st.subheader("📰 실시간 랭킹 (S급 자동 강조)")
            if st.button("🔄 리스트 새로고침"):
                st.cache_data.clear()
                if "s_idx" in st.session_state: del st.session_state.s_idx
                st.rerun()
            
            # 리스트 렌더링
            for i, item in enumerate(news_items):
                is_s = i in s_idx
                btn_text = f"🏆 [S급] {item['title']}" if is_s else f"[{i+1}] {item['title']}"
                
                if st.button(btn_text, key=f"btn_{i}", use_container_width=True):
                    with st.spinner('소재 분석 중...'):
                        content = get_content_safe(item['link'])
                        if model:
                            try:
                                analysis = model.generate_content(f"다음 기사 분석해서 썸네일 카피 3개랑 시청 포인트 3개 짜줘:\n{content[:2000]}").text
                            except:
                                analysis = "AI 분석 서버 오류가 발생했습니다."
                        else:
                            analysis = "AI 모델 로드 실패"
                            
                        st.session_state.active_news = {
                            "title": item['title'],
                            "content": content,
                            "analysis": analysis,
                            "is_s": is_s
                        }

        with col_view:
            if "active_news" in st.session_state:
                res = st.session_state.active_news
                st.markdown(f"### {'🏆 S급' if res['is_s'] else '📊'} {res['title']}")
                with st.container():
                    st.success(res['analysis'])
                    st.divider()
                    st.markdown("**📄 기사 전문 (클라우드/GPT 복사용)**")
                    st.text_area("Full Text", res['content'], height=500)
            else:
                st.info("왼쪽 뉴스 제목을 클릭하면 분석이 시작됩니다.")

with tab2:
    st.header("🎯 초격차 원고 빌더")
    
    st.markdown("### 1️⃣ 캡처 이미지 분석 (Ctrl+V)")
    caps = st.file_uploader("뉴스 리스트 캡처본을 올려주세요.", accept_multiple_files=True)
    if caps and st.button("🔍 이미지 분석"):
        if model:
            with st.spinner("이미지 읽는 중..."):
                imgs = [PIL.Image.open(c) for c in caps]
                v_res = model.generate_content(["이 이미지에서 떡상할 소재를 찾고 제목을 제안해줘.", *imgs]).text
                st.success(v_res)
    
    st.divider()
    
    st.markdown("### 2️⃣ 마스터 프롬프트 생성")
    c1, c2 = st.columns(2)
    with c1:
        m_title = st.text_input("제목")
        m_news = st.text_area("뉴스 본문 합계", height=250)
    with c2:
        m_yt = st.text_input("벤치마킹 URL")
        m_comm = st.text_area("댓글 민심", height=200)
        if st.button("🔗 민심 자동 추론"):
            if model and m_title:
                m_comm = model.generate_content(f"{m_title} 소재에 대해 한국 시청자들이 보낼법한 열광적인 댓글 5개 써줘.").text
                st.info(m_comm)

    if st.button("🔥 클로드 전용 프롬프트 생성", use_container_width=True):
        if m_title and m_news:
            prompt = f"""당신은 100만 유튜버 작가입니다. 다음 주제로 8분 분량 대본을 쓰세요.\n주제: {m_title}\n팩트: {m_news}\n참고: {m_yt}\n민심: {m_comm}\n[지침] 5,000자 이상, [경악] [전율] 태그 사용, 후킹 강하게."""
            st.code(prompt, language="markdown")
