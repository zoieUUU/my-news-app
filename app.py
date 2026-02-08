import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import re

# 1. AI 엔진 설정
@st.cache_resource
def load_ai_model():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
        return genai.GenerativeModel(target)
    except: return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL MASTER v2", layout="wide")

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
    if model:
        try:
            titles = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:30])])
            resp = model.generate_content(f"조회수 100만 기준 S급 소재 5개 번호만 골라: {titles}")
            s_indices = [int(n) for n in re.findall(r'\d+', resp.text)]
        except: s_indices = [0,1,2,3,4]
    for i, item in enumerate(unique_news):
        item['grade'] = "S" if i in s_indices else "A"
    return sorted(unique_news, key=lambda x: x['grade'], reverse=True)

def analyze_news(url):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://news.naver.com/"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
    text = content.get_text(strip=True) if content else "본문 수집 불가"
    analysis = "분석 실패"
    if model and text != "본문 수집 불가":
        prompt = f"이 기사의 핵심 요약 2줄과 핵심 키워드 5개를 뽑아줘:\n\n{text[:1500]}"
        try: analysis = model.generate_content(prompt).text
        except: pass
    return text, analysis

# --- 메인 화면 탭 구성 ---
tab1, tab2 = st.tabs(["🔥 실시간 소재 발굴 (네이버)", "🎬 초격차 대본 빌더 (클로드 연동)"])

# --- TAB 1: 실시간 뉴스 ---
with tab1:
    l, r = st.columns([1, 1.2])
    with l:
        if st.button("🔄 리스트 새로고침"):
            st.cache_data.clear()
            st.rerun()
        data = get_viral_top_100()
        for i, item in enumerate(data):
            if item['grade'] == "S":
                st.markdown(f'<div style="background-color:#FFD700; padding:5px; border-radius:5px; border:2px solid #FFA500; font-weight:bold; color:black; font-size:12px; margin-bottom:-10px; width:fit-content;">👑 AI S-CLASS 추천</div>', unsafe_allow_html=True)
                if st.button(f"🔥 {item['title']}", key=f"s_{i}", use_container_width=True):
                    t, a = analyze_news(item['link'])
                    st.session_state.res = {"title":item['title'], "text":t, "analysis":a, "link":item['link']}
            else:
                if st.button(f"[{i+1}] {item['title']}", key=f"n_{i}", use_container_width=True):
                    t, a = analyze_news(item['link'])
                    st.session_state.res = {"title":item['title'], "text":t, "analysis":a, "link":item['link']}
    with r:
        st.subheader("📊 소재 분석 결과")
        if "res" in st.session_state:
            st.success(st.session_state.res['analysis'])
            st.markdown(f"🔗 **[원문 읽기]({st.session_state.res['link']})**")
            st.text_area("기사 본문 (복사용)", st.session_state.res['text'], height=400)
        else: st.info("왼쪽에서 소재를 선택하세요.")

# --- TAB 2: 전문 대본 빌더 ---
with tab2:
    st.subheader("✍️ 100만 조회수 대본 설계국")
    st.info("이슈서치 스타일의 8~9분 대본을 위한 모든 소스를 입력하세요.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        topic = st.text_input("💎 키워드/소재 제목", placeholder="예: KF-21 인도네시아 미납 사건의 반전")
        news_input = st.text_area("📰 참고 뉴스 링크 및 본문 (최대 5개)", height=300, placeholder="뉴스 원문을 여기에 다 붙여넣으세요.")
    with col_b:
        yt_link = st.text_input("📺 벤치마킹 유튜브 링크", value="https://www.youtube.com/watch?v=GkKYFpO8shk")
        comment_input = st.text_area("💬 댓글 민심 데이터 (민심 분석용)", height=300, placeholder="베스트 댓글들을 복사해 넣어주세요.")

    if st.button("🔥 클로드용 '이슈서치' 마스터 프롬프트 생성", use_container_width=True):
        if not topic or not news_input:
            st.warning("소재와 뉴스 내용은 필수입니다!")
        else:
            final_prompt = f"""
# 지시사항: 100만 바이럴 유튜브 작가 빙의 (이슈서치 스타일)
너는 대한민국 1등 이슈 분석 채널 '이슈서치'의 메인 작가다. 아래 데이터를 분석해서 8~9분 분량(3,500자 이상)의 떡상 대본을 작성해라.

## [입력 데이터]
- 키워드/소재: {topic}
- 뉴스 데이터: {news_input}
- 레퍼런스 영상: {yt_link}
- 댓글 민심: {comment_input}

## [집필 가이드]
1. 톤앤매너: 묵직한 전문성 + 팩트 기반 반전 서사 + 유머러스한 비꼼.
2. 7단계 구조:
   - 1단: [0~30s] 충격적 팩트 훅
   - 2단: 위기감 조성
   - 3단: 1차 CTA (좋아요 유도)
   - 4단: 뉴스 5개 교차 분석 (외신 인용 필수)
   - 5단: 댓글 민심 공감 (아쉬운 점 보완)
   - 6단: 한국의 반격 카드 (카타르시스)
   - 7단: 결론 및 댓글 유도 질문
3. 제목 제안: 벤치마킹 채널보다 자극적인 초 공격형 제목 3종 추천.

※ 반드시 감정 태그 [분노], [희망] 등을 포함하고 8분 이상의 분량을 확보하라.
            """
            st.code(final_prompt, language="markdown")
            st.success("✅ 위 내용을 복사해서 클로드에 붙여넣으세요!")
