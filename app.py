import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import re

# 1. AI 엔진 설정 (가용 모델 자동 탐색)
@st.cache_resource
def load_ai_model():
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
        return genai.GenerativeModel(target)
    except: return None

model = load_ai_model()

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 및 등급 판별 ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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
            resp = model.generate_content(f"유튜브 조회수 100만 기준 S급 소재 5개 번호만 골라(쉼표 구분): {titles}")
            s_indices = [int(n) for n in re.findall(r'\d+', resp.text)]
        except: s_indices = [0,1,2,3,4]
    
    for i, item in enumerate(unique_news):
        item['grade'] = "S" if i in s_indices else "A"
    return sorted(unique_news, key=lambda x: x['grade'], reverse=True)

# --- 뉴스 분석 함수 ---
def analyze_news(url):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://news.naver.com/"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
    text = content.get_text(strip=True) if content else "본문 수집 불가"
    
    analysis = "분석 실패"
    if model and text != "본문 수집 불가":
        prompt = f"이 기사의 핵심 요약 2줄과 핵심 키워드 5개를 뽑아줘:\n\n{text[:1500]}"
        try:
            analysis = model.generate_content(prompt).text
        except: pass
    return text, analysis

# --- 메인 화면 ---
st.title("🔥 VIRAL RANKING MASTER")

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
                with st.spinner('분석 중...'):
                    t, a = analyze_news(item['link'])
                    st.session_state.res = {"title":item['title'], "text":t, "analysis":a, "link":item['link']}
        else:
            if st.button(f"[{i+1}] {item['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = analyze_news(item['link'])
                    st.session_state.res = {"title":item['title'], "text":t, "analysis":a, "link":item['link']}

with r:
    st.subheader("📊 AI 분석 리포트")
    if "res" in st.session_state:
        # 요약 결과
        st.success(f"**💡 AI 인사이트**\n\n{st.session_state.res['analysis']}")
        
        # [핵심] 원문 링크 및 복사 버튼
        st.divider()
        st.markdown(f"🔗 **[네이버 원문 기사 읽기]({st.session_state.res['link']})**")
        
        st.info(f"**제목: {st.session_state.res['title']}**")
        st.text_area("기사 본문 (클로드 가공용)", st.session_state.res['text'], height=400)
        
        # 클로드용 통합 프롬프트
        st.markdown("### 📥 Claude 복사용 프롬프트")
        copy_text = f"제목: {st.session_state.res['title']}\n출처: {st.session_state.res['link']}\n\n내용: {st.session_state.res['text']}"
        st.code(copy_text, language="text")
    else:
        st.info("👈 소재를 선택하면 상세 분석과 링크가 나타납니다.")
