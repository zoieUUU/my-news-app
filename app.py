import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import re
import PIL.Image

# 1. AI 엔진 설정 (Gemini 1.5 Flash 사용)
@st.cache_resource
def load_ai_model():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return genai.GenerativeModel('models/gemini-1.5-flash')
    except: return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL MASTER PRO", layout="wide")

# --- 뉴스 수집 함수 ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    unique_news = []
    seen = set()
    for box in soup.select('.rankingnews_box'):
        for li in box.select('.rankingnews_list li'):
            a = li.select_one('a')
            if a and a.text.strip() not in seen:
                unique_news.append({"title": a.text.strip(), "link": a['href']})
                seen.add(a.text.strip())
    return unique_news

def analyze_news(url):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://news.naver.com/"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
    text = content.get_text(strip=True) if content else "본문 수집 불가"
    analysis = "분석 불가"
    if model and text != "본문 수집 불가":
        prompt = f"이 기사의 핵심 요약 2줄과 핵심 키워드 5개를 뽑아줘:\n\n{text[:1500]}"
        try: analysis = model.generate_content(prompt).text
        except: pass
    return text, analysis

# --- 메인 화면 구성 ---
st.title("🔥 VIRAL MASTER: S-Class Contents Builder")

tab1, tab2 = st.tabs(["📢 실시간 이슈 탐색", "🎯 소재 선별 & 대본 마스터링"])

# --- TAB 1: 실시간 뉴스 ---
with tab1:
    l, r = st.columns([1, 1.2])
    with l:
        if st.button("🔄 리스트 새로고침"):
            st.cache_data.clear()
            st.rerun()
        data = get_viral_top_100()
        for i, item in enumerate(data[:50]): # 상위 50개만 표시
            if st.button(f"[{i+1}] {item['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('기사 분석 중...'):
                    t, a = analyze_news(item['link'])
                    st.session_state.res = {"title":item['title'], "text":t, "analysis":a, "link":item['link']}
    with r:
        if "res" in st.session_state:
            st.subheader("📊 AI 뉴스 요약")
            st.success(st.session_state.res['analysis'])
            st.markdown(f"🔗 **[원문 기사 바로가기]({st.session_state.res['link']})**")
            st.text_area("클로드 입력용 본문", st.session_state.res['text'], height=400)
        else:
            st.info("👈 왼쪽 리스트에서 분석할 기사를 선택하세요.")

# --- TAB 2: 소재 선별 및 대본 생성 ---
with tab2:
    st.header("📸 S급 소재 판별 및 마스터링")
    
    # 1. 이미지 분석 섹션
    col_img1, col_img2 = st.columns([1, 1])
    with col_img1:
        st.markdown("### 1️⃣ 캡처본 업로드 (네이버/더구루 등)")
        uploaded_file = st.file_uploader("뉴스 리스트 캡처 이미지를 올려주세요.", type=['jpg', 'png', 'jpeg'])
        if uploaded_file and st.button("🔍 이미지 기반 S급 소재 추출"):
            img = PIL.Image.open(uploaded_file)
            with st.spinner("이미지 텍스트 분석 중..."):
                analysis_prompt = """
                이미지 속 뉴스 제목들을 분석하여 유튜브 조회수 50만~100만 이상 가능성이 높은 S급 소재 5개를 골라줘.
                각 소재별로 [순위/제목/선정이유(분노,국뽕,카타르시스 측면)]를 구체적으로 설명해라.
                """
                response = model.generate_content([analysis_prompt, img])
                st.session_state.s_class = response.text

    with col_img2:
        if "s_class" in st.session_state:
            st.markdown("### 🏆 AI 추천 황금 소재")
            st.write(st.session_state.s_class)

    st.divider()

    # 2. 클로드용 통합 프롬프트 생성기
    st.markdown("### 2️⃣ 클로드 프로젝트용 데이터 입력")
    c1, c2 = st.columns(2)
    with c1:
        topic = st.text_input("💎 확정 소재 제목")
        news_urls = st.text_area("📰 뉴스 기사 본문들 (최대 5개 복붙)", height=250)
    with c2:
        yt_ref = st.text_input("📺 벤치마킹 유튜브 링크")
        comments = st.text_area("💬 댓글 민심 데이터 (전부 복붙)", height=250)

    if st.button("🔥 클로드 마스터 프롬프트 생성", use_container_width=True):
        master_prompt = f"""
# 지시사항: 100만 바이럴 유튜브 작가 빙의 (하이엔드 스토리텔러 모드)
너는 '이슈서치'급 메인 작가다. 아래 자료를 바탕으로 시청자의 멱살을 잡는 8~9분 대본을 작성하라.

[입력 데이터]
- 소재: {topic}
- 뉴스 팩트: {news_urls}
- 벤치마킹 채널: {yt_ref}
- 댓글 민심: {comments}

[집필 가이드]
1. 실제 상황처럼 생생하게 묘사하라. "지금 현장에선 비명이 터져 나옵니다."
2. 능글맞고 유머러스하게 비꼬아라. "상대방의 낯빛이 흙빛이 됐네요."
3. 7단계 구조 준수: 훅(0~25s) -> CTA1 -> 배경 -> 팩트폭격 -> 민심공감 -> 반전/카타르시스 -> 결론/CTA2.
4. 나레이션용 감정 태그([분노], [비웃음], [진지])와 이미지 생성을 위한 [Visual: 설명] 가이드를 포함하라.
5. 초 공격형 바이럴 제목 3종과 썸네일 구도를 추천하라.
        """
        st.code(master_prompt, language="markdown")
        st.success("✅ 위 내용을 복사해서 클로드 프로젝트에 던지세요!")
