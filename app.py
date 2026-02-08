import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정 (가용 모델 자동 탐색 로직)
@st.cache_resource
def load_ai_model():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # 현재 환경에서 사용 가능한 모델 목록 확인
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 1순위: gemini-1.5-flash, 2순위: gemini-pro, 3순위: 아무거나 첫 번째 모델
        target_model = ""
        if 'models/gemini-1.5-flash' in models: target_model = 'models/gemini-1.5-flash'
        elif 'models/gemini-pro' in models: target_model = 'models/gemini-pro'
        else: target_model = models[0]
        
        return genai.GenerativeModel(target_model)
    except Exception as e:
        st.error(f"모델 로드 실패: {e}")
        return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 함수 (네이버 차단 방지) ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        unique_news = []
        seen_titles = set()
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a_tag = li.select_one('a')
                if a_tag and a_tag.text.strip() not in seen_titles:
                    unique_news.append({"title": a_tag.text.strip(), "link": a_tag['href']})
                    seen_titles.add(a_tag.text.strip())
        
        # S급 추천 (AI 모델이 있을 때만 작동)
        s_indices = []
        if model:
            try:
                titles_list = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:30])])
                resp = model.generate_content(f"유튜브 조회수 터질 소재 5개의 번호만 골라줘: {titles_list}")
                import re
                s_indices = [int(n) for n in re.findall(r'\d+', resp.text)]
            except: s_indices = [0,1,2,3,4]
        
        for i, item in enumerate(unique_news):
            item['is_s'] = i in s_indices
        return sorted(unique_news, key=lambda x: x.get('is_s', False), reverse=True)
    except: return []

# --- AI 분석 함수 ---
def get_ai_analysis(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://news.naver.com/"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        
        if not content: return "본문 수집 실패", "분석 불가"
        text = content.get_text(strip=True)
        
        if model:
            resp = model.generate_content(f"다음 뉴스 요약 2줄, 키워드 5개 뽑아줘:\n\n{text[:1500]}")
            return text, resp.text
        return text, "AI 모델이 설정되지 않았습니다."
    except Exception as e:
        return f"연결 실패: {e}", "분석 불가"

# --- 메인 화면 ---
st.title("🔥 VIRAL RANKING MASTER")

l, r = st.columns([1, 1.2])

with l:
    if st.button("🔄 리스트 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    data = get_viral_top_100()
    for i, item in enumerate(data):
        if item.get('is_s'):
            st.markdown(f'<div style="background-color:#FFD700; padding:5px; border-radius:5px; border:2px solid #FFA500; font-weight:bold; color:black; font-size:12px; margin-bottom:-10px; width:fit-content;">👑 AI S-CLASS 추천</div>', unsafe_allow_html=True)
            if st.button(f"🔥 {item['title']}", key=f"s_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = get_ai_analysis(item['link'])
                    st.session_state.res = {"title": item['title'], "text": t, "analysis": a}
        else:
            if st.button(f"[{i+1}] {item['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = get_ai_analysis(item['link'])
                    st.session_state.res = {"title": item['title'], "text": t, "analysis": a}

with r:
    st.subheader("📊 AI 분석 리포트")
    if "res" in st.session_state:
        st.success(f"**💡 AI 분석 결과**\n\n{st.session_state.res['analysis']}")
        st.divider()
        st.info(f"**제목: {st.session_state.res['title']}**")
        st.text_area("기사 본문", st.session_state.res['text'], height=550)
    else:
        st.info("👈 왼쪽에서 뉴스를 선택하세요.")
