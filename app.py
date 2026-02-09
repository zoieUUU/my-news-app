import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import PIL.Image
import io
import json
import time
import re

# 1. AI 엔진 설정
@st.cache_resource
def load_ai_model():
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            # 더 안정적인 모델 버전 지정
            return genai.GenerativeModel('gemini-1.5-flash')
        else:
            st.error("API 키가 설정되지 않았습니다. Secrets를 확인해주세요.")
            return None
    except Exception as e:
        st.error(f"AI 모델 로드 실패: {e}")
        return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL MASTER PRO v2.6", layout="wide")

# --- 강력한 UI 커스터마이징 (UI 깨짐 방지 및 S급 강조) ---
st.markdown("""
    <style>
    /* 전체 배경 테마 */
    .main { background-color: #ffffff; }
    
    /* S급 소재 전용 카드 스타일 (리스트와 분리) */
    .s-class-container {
        background: linear-gradient(145deg, #1e1e1e, #3a3a3a);
        border: 3px solid #FFD700;
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 30px;
        box-shadow: 0 15px 35px rgba(255, 215, 0, 0.3);
    }
    
    .s-header {
        color: #FFD700;
        font-size: 24px;
        font-weight: 900;
        margin-bottom: 20px;
        text-align: center;
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
    }
    
    .s-item-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 215, 0, 0.3);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
        transition: transform 0.2s;
    }
    
    .s-item-card:hover {
        transform: scale(1.02);
        background: rgba(255, 215, 0, 0.1);
    }

    /* 버튼 스타일 강제 오버라이드 */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        border: 1px solid #ddd !important;
    }
    
    /* S급 분석 버튼 특수 스타일 */
    .stButton > button[kind="primary"] {
        background: #FFD700 !important;
        color: black !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4) !important;
    }

    /* 텍스트 영역 스타일 */
    .stTextArea textarea {
        background-color: #fdfdfd !important;
        font-family: 'Pretendard', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 유틸리티 함수 ---
def get_content_safe(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 뉴스 본문 선택자 강화
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('.article_body')
        return content.get_text(strip=True) if content else "본문 내용을 수집할 수 없습니다."
    except Exception as e:
        return f"데이터 수집 중 에러 발생: {e}"

@st.cache_data(ttl=600)
def fetch_news():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_list = []
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a = li.select_one('a')
                if a and a.text.strip():
                    news_list.append({"title": a.text.strip(), "link": a['href']})
        return news_list
    except:
        return []

def get_s_class_indices(news_data):
    if not model or not news_data: return []
    titles = [f"{i}: {n['title']}" for i, n in enumerate(news_data[:50])]
    prompt = f"""
    당신은 100만 유튜버 기획자입니다. 
    다음 뉴스 중 [방산, 반도체, 국격, 외신극찬, 일본반응, 스포츠] 관련 떡상 소재 5개를 골라 번호만 출력하세요.
    형식: [0, 5, 12, 18, 24]
    뉴스:
    {chr(10).join(titles)}
    """
    try:
        response = model.generate_content(prompt)
        match = re.search(r"\[.*\]", response.text)
        if match:
            return json.loads(match.group())
        return []
    except:
        return []

# --- 메인 대시보드 ---
st.title("👑 VIRAL MASTER PRO v2.6")
st.caption("초정밀 AI 필터링 시스템 (방산/반도체/국위선양 소재 전문)")

tab1, tab2 = st.tabs(["🔥 실시간 황금소재 탐색", "🎯 S급 빌더 & 원고 마스터"])

with tab1:
    news_items = fetch_news()
    
    if news_items:
        if "s_idx" not in st.session_state:
            with st.spinner('🚀 100만 유튜버 AI가 S급 소재를 선별하고 있습니다...'):
                st.session_state.s_idx = get_s_class_indices(news_items)
        
        s_idx = st.session_state.s_idx
        
        # UI 레이아웃
        left, right = st.columns([1, 1.2])
        
        with left:
            # 1. S급 섹션 (별도 카드로 강조)
            st.markdown('<div class="s-class-container"><div class="s-header">🏆 오늘자 떡상 보증 소재 (TOP 5)</div>', unsafe_allow_html=True)
            for i in s_idx:
                if i < len(news_items):
                    item = news_items[i]
                    with st.container():
                        st.markdown(f'<div class="s-item-card">✨ {item["title"]}</div>', unsafe_allow_html=True)
                        if st.button("S급 심층분석", key=f"sbtn_{i}", type="primary", use_container_width=True):
                            with st.spinner('전략 수립 중...'):
                                content = get_content_safe(item['link'])
                                analysis = model.generate_content(f"유튜브 썸네일 카피 3개와 시청자 열광 포인트를 정리해줘:\n{content[:1500]}").text
                                st.session_state.current_news = {"title": item['title'], "content": content, "analysis": analysis}
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 2. 일반 랭킹 리스트
            st.subheader("📰 실시간 인기 뉴스 (전체)")
            if st.button("🔄 리스트 새로고침"):
                st.cache_data.clear()
                if "s_idx" in st.session_state: del st.session_state.s_idx
                st.rerun()
                
            for i, item in enumerate(news_items[:40]):
                if i not in s_idx:
                    if st.button(f"[{i+1}] {item['title']}", key=f"nbtn_{i}", use_container_width=True):
                        with st.spinner('소재 분석 중...'):
                            content = get_content_safe(item['link'])
                            analysis = model.generate_content(f"유튜브 제작 포인트 요약:\n{content[:1500]}").text
                            st.session_state.current_news = {"title": item['title'], "content": content, "analysis": analysis}

        with right:
            if "current_news" in st.session_state:
                res = st.session_state.current_news
                st.markdown(f"### 📊 분석 결과: {res['title']}")
                st.success(res['analysis'])
                st.divider()
                st.markdown("**📝 클로드 입력용 원천 데이터**")
                st.text_area("Fact Data", res['content'], height=500)
            else:
                st.info("왼쪽 리스트에서 소재를 선택하면 100만 조회수 전략을 즉시 수립합니다.")

with tab2:
    st.header("🎯 초격차 원고 제작 프로젝트")
    
    # 1. 이미지 분석
    st.markdown("### 1️⃣ 타 채널/커뮤니티 캡처본 분석 (Ctrl+V)")
    st.info("💡 이미지 파일을 드래그하거나 선택하세요. (복수 선택 지원)")
    caps = st.file_uploader("네이버/더구루/유튜브 캡처 이미지 업로드", accept_multiple_files=True)
    if caps and st.button("🔍 이미지 속 S급 소재 발굴"):
        with st.spinner("비전 AI 가동 중..."):
            imgs = [PIL.Image.open(c) for c in caps]
            v_res = model.generate_content(["이 이미지들에서 유튜브로 만들면 대박 날 소재를 찾고, 썸네일 카피를 짜줘.", *imgs]).text
            st.success(v_res)

    st.divider()
    
    # 2. 대본 빌더
    st.markdown("### 2️⃣ 클로드 프로젝트용 데이터 입력")
    c1, c2 = st.columns(2)
    with c1:
        f_title = st.text_input("💎 확정 소재 제목", placeholder="예: [단독] 한국형 전투기 K-21, 폴란드서 역대급 찬사")
        f_news = st.text_area("📰 뉴스 기사 본문들 (복합 복붙 가능)", height=250, placeholder="여러 기사 본문을 여기에 다 붙여넣으세요.")
    with c2:
        f_yt = st.text_input("📺 벤치마킹 유튜브 링크", placeholder="https://www.youtube.com/...")
        f_comm = st.text_area("💬 시청자 민심/댓글 반응", height=200, placeholder="댓글창 내용을 긁어오거나 직접 입력하세요.")
        if st.button("🔗 링크 기반 민심 자동 추론"):
            if f_yt:
                with st.spinner('민심 분석 중...'):
                    inf = model.generate_content(f"이 유튜브 영상({f_yt})의 소재를 바탕으로 한국 시청자들이 가장 열광할만한 댓글 반응 5개를 가상으로 작성해줘.").text
                    st.info(inf)

    if st.button("🔥 클로드 초격차 마스터 프롬프트 생성", use_container_width=True):
        if not f_title or not f_news:
            st.error("제목과 뉴스 본문 데이터가 필요합니다.")
        else:
            master_prompt = f"""
# 지시사항: 100만 조회수 보증 '초격차 유튜브 원고' 집필 지침

당신은 대한민국 최고 이슈 채널의 메인 작가입니다. 다음 데이터를 바탕으로 시청자의 국뽕과 도파민을 동시에 폭발시키는 8분 분량의 완성형 대본을 작성하십시오.

## [입력 데이터]
- 확정 주제: {f_title}
- 팩트 데이터: {f_news}
- 벤치마킹 타겟: {f_yt}
- 시청자 여론: {f_comm}

## [대본 서사 구조 가이드]
1. [전율의 오프닝] "지금 전 세계가 경악하고 있습니다." 외신 반응 중 가장 자극적인 한마디로 30초 내에 시청자 고정.
2. [위기 상황 전개] 한국이 처했던 기술적/정치적 어려움과 주변국(일본/중국 등)의 비웃음을 구체적으로 묘사.
3. [압도적 역전] K-방산/반도체/기업이 보여준 '말도 안 되는 결과'를 팩트 기반으로 서술. (수치 강조)
4. [민심 대폭발] 실제 시청자 반응을 인용하며 "이게 바로 대한민국입니다"라는 카타르시스 선사.
5. [결론 및 구독] 국격 상승의 의미 부여와 함께 공격적인 구독 유도 멘트.

## [작성 규칙]
- 모든 문장 앞에 감정 태그 삽입 (예: [전율], [경악], [냉소], [감동])
- 화면 편집 지시사항 포함 (예: [Visual: 삼성 전자 수출 그래프가 수직 상승하는 CG 삽입])
- 클로드 답변은 최소 5,000자 이상의 초고밀도 상세 원고로 출력할 것.

지금 바로 집필을 시작하십시오.
            """
            st.markdown("### 📋 아래 내용을 복사하여 클로드(Claude)에 입력하세요")
            st.code(master_prompt, language="markdown")
            st.success("프롬프트가 생성되었습니다. 클로드에 붙여넣으면 즉시 제작이 시작됩니다.")
