import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정 - 지원되는 정확한 모델명으로 수정
@st.cache_resource
def load_ai_model():
    try:
        model_name = 'gemini-2.5-flash-preview-09-2025'
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            return genai.GenerativeModel(model_name)
        else:
            # API 키가 없을 경우 빈 문자열로 설정 시도 (환경에서 자동 주입하는 경우 대비)
            genai.configure(api_key="")
            return genai.GenerativeModel(model_name)
    except Exception as e:
        st.error(f"AI 모델 초기화 실패: {e}")
        return None

model = load_ai_model()

# 2. API 호출을 위한 지수 백오프 함수 (429 에러 대응)
def call_gemini_with_retry(prompt, is_image=False, images=None):
    if not model:
        return None
    
    max_retries = 5
    for i in range(max_retries):
        try:
            if is_image and images:
                response = model.generate_content([prompt, *images])
            else:
                response = model.generate_content(prompt)
            return response
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower():
                wait_time = (2 ** i) + 1  # 1s, 2s, 4s, 8s, 16s 대기
                if i < max_retries - 1:
                    time.sleep(wait_time)
                    continue
            st.error(f"AI 호출 오류: {e}")
            return None
    return None

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- UI 스타일 커스터마이징 (S급 리스트 강조 강화) ---
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    
    /* 일반 뉴스 버튼 기본 스타일 */
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
        display: block !important;
    }
    
    /* S급 뉴스 버튼 스타일 강조 */
    div.stButton > button:has(div:contains("🏆")) {
        background-color: #fff9e6 !important;
        border: 2px solid #FFD700 !important;
        color: #856404 !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 10px rgba(255, 215, 0, 0.3) !important;
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
    다음 뉴스 중 [방산, 반도체, 외신극찬, 국위선양, 일본반응, 한국 기술력] 등 조회수가 터질 S급 소재 5개의 번호만 리스트로 출력하세요.
    출력 형식은 오직 JSON 리스트만 허용합니다. 예: [1, 5, 12, 18, 24]
    
    뉴스 리스트:
    {titles}
    """
    response = call_gemini_with_retry(prompt)
    if response:
        try:
            text = response.text
            match = re.search(r"\[\s*\d+\s*(?:,\s*\d+\s*)*\]", text)
            if match:
                indices = json.loads(match.group())
                return [int(i) for i in indices]
        except:
            pass
    return []

# --- 메인 대시보드 ---
st.title("👑 VIRAL MASTER PRO v2.6")
st.caption("실시간 뉴스 랭킹 & S급 소재 자동 판별 시스템")

tab1, tab2 = st.tabs(["🔥 뉴스 리스트 탐색", "🎯 대본 마스터 빌더"])

with tab1:
    news_items = fetch_news_list()
    
    if news_items:
        if "s_idx" not in st.session_state:
            with st.spinner('🚀 AI가 실시간으로 S급 떡상 소재를 선별 중입니다... (API 제한으로 지연될 수 있음)'):
                st.session_state.s_idx = get_s_class_indices(news_items)
        
        s_idx = st.session_state.s_idx or []
        
        col_list, col_view = st.columns([1.2, 1])
        
        with col_list:
            st.subheader("📰 실시간 랭킹 (S급 자동 강조)")
            if st.button("🔄 리스트 & AI 분석 갱신"):
                st.cache_data.clear()
                if "s_idx" in st.session_state: del st.session_state.s_idx
                st.rerun()
            
            for i, item in enumerate(news_items):
                is_s = i in s_idx
                btn_text = f"🏆 [S급] {item['title']}" if is_s else f"[{i+1}] {item['title']}"
                
                if st.button(btn_text, key=f"btn_{i}", use_container_width=True):
                    with st.spinner('소재 심층 분석 중...'):
                        content = get_content_safe(item['link'])
                        analysis_prompt = f"다음 기사를 분석하여 유튜브용 썸네일 카피 3개와 시청자 열광 포인트 3개를 정리해줘:\n\n제목: {item['title']}\n내용: {content[:2000]}"
                        response = call_gemini_with_retry(analysis_prompt)
                        
                        analysis_text = response.text if response else "AI 분석 호출 실패 (쿼터 초과). 잠시 후 다시 클릭하세요."
                            
                        st.session_state.active_news = {
                            "title": item['title'],
                            "content": content,
                            "analysis": analysis_text,
                            "is_s": is_s
                        }

        with col_view:
            if "active_news" in st.session_state:
                res = st.session_state.active_news
                title_icon = "🏆 [S급 황금 소재]" if res['is_s'] else "📊 [일반 소재 분석]"
                st.markdown(f"### {title_icon}")
                st.markdown(f"**{res['title']}**")
                
                with st.container():
                    st.success(res['analysis'])
                    st.divider()
                    st.markdown("**📄 기사 전문 (데이터 복사용)**")
                    st.text_area("Full Text", res['content'], height=500)
            else:
                st.info("왼쪽 뉴스 제목을 클릭하면 AI의 떡상 전략 분석이 시작됩니다.")

with tab2:
    st.header("🎯 초격차 원고 제작 프로젝트")
    
    st.markdown("### 1️⃣ 캡처 이미지 분석")
    caps = st.file_uploader("뉴스 리스트나 커뮤니티 캡처본을 올려주세요.", accept_multiple_files=True)
    if caps and st.button("🔍 비전 AI 분석 가동"):
        with st.spinner("이미지 내용 분석 중..."):
            imgs = [PIL.Image.open(c) for c in caps]
            prompt = "이 이미지들에서 다루는 주요 이슈를 파악하고 대박 날 썸네일 제목을 추천해줘."
            response = call_gemini_with_retry(prompt, is_image=True, images=imgs)
            if response:
                st.success(response.text)
    
    st.divider()
    
    st.markdown("### 2️⃣ 데이터 취합 및 프롬프트 생성")
    c1, c2 = st.columns(2)
    with c1:
        m_title = st.text_input("💎 영상 최종 제목")
        m_news = st.text_area("📰 수집된 뉴스 본문 전체", height=250)
    with c2:
        m_yt = st.text_input("📺 벤치마킹 타겟 URL")
        m_comm = st.text_area("💬 실시간 시청자 반응/댓글", height=200)
        if st.button("🔗 예상 민심 자동 생성"):
            if m_title:
                with st.spinner('추론 중...'):
                    prompt = f"주제 '{m_title}'에 대해 한국 시청자들이 보낼법한 국뽕 가득한 댓글 5개를 작성해줘."
                    response = call_gemini_with_retry(prompt)
                    if response:
                        st.info(response.text)

    if st.button("🔥 클로드(Claude) 전용 초격차 프롬프트 생성", use_container_width=True):
        if m_title and m_news:
            final_prompt = f"""
당신은 구독자 100만 명을 보유한 대한민국 최고의 이슈 채널 메인 작가입니다. 
아래 제공된 데이터를 바탕으로 시청자들의 도파민과 국뽕을 동시에 폭발시킬 8분 분량의 완성형 원고를 작성하세요.

[데이터 서머리]
1. 주제: {m_title}
2. 기사 팩트: {m_news}
3. 벤치마킹: {m_yt}
4. 시청자 여론: {m_comm}

[집필 가이드라인]
- 도입부에서 "지금 전 세계가 경악하고 있습니다"와 같은 강렬한 후킹 멘트로 시작할 것.
- 모든 문장 앞에 [전율], [경악], [냉소], [감동] 등의 감정 태그를 삽입할 것.
- 한국의 기술력이나 국격 상승을 강조하며 카타르시스를 선사할 것.
- 최소 5,000자 이상의 밀도 높은 대본으로 출력할 것.
"""
            st.code(final_prompt, language="markdown")
            st.success("위 프롬프트를 복사하여 클로드에 붙여넣으세요!")
