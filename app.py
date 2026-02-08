import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정 (404 에러 원천 차단 로직)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # 라이브러리 버전에 상관없이 가장 잘 잡히는 모델명 'gemini-1.5-flash' 사용
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"API 설정 오류: {e}")

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 함수 (차단 방지 헤더 강화) ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        unique_news = []
        seen_titles = set()
        for box in soup.select('.rankingnews_box'):
            for li in box.select('.rankingnews_list li'):
                a_tag = li.select_one('a')
                if a_tag:
                    title = a_tag.text.strip()
                    if title not in seen_titles:
                        unique_news.append({"title": title, "link": a_tag['href']})
                        seen_titles.add(title)
        
        # AI에게 S급 소재 5개 추천 요청
        titles_for_ai = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:40])])
        prompt = f"유튜브 조회수 100만 기획자로서 다음 뉴스 중 S급 소재 5개의 번호만 골라줘(쉼표 구분): {titles_for_ai}"
        resp = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in resp.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = [0, 1, 2, 3, 4] # 에러 발생 시 상위 5개 대체
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

# --- AI 분석 함수 (네이버 차단 우회 및 에러 핸들링) ---
def get_ai_analysis(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://news.naver.com/"
        }
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 뉴스 본문 태그 우선순위 수집
        content = soup.select_one('#dic_area') or soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        
        if not content:
            return "본문을 수집할 수 없습니다. (비로그인 제한 등)", "분석 불가"
            
        text = content.get_text(strip=True)
        # AI 분석 요청
        analysis_prompt = f"다음 뉴스를 분석해서 [핵심 요약 2줄]과 [중요 키워드 5개]를 뽑아줘:\n\n{text[:1800]}"
        resp = model.generate_content(analysis_prompt)
        return text, resp.text
    except Exception as e:
        return f"연결 문제 발생: {str(e)}", f"분석 에러: {str(e)}"

# --- UI 레이아웃 ---
st.title("🔥 VIRAL RANKING MASTER")

left, right = st.columns([1, 1.2])

with left:
    if st.button("🔄 리스트 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    news_data = get_viral_top_100()
    for i, item in enumerate(news_data):
        if item['is_s']:
            st.markdown(f'<div style="background-color:#FFD700; padding:5px; border-radius:5px; border:2px solid #FFA500; font-weight:bold; color:black; font-size:12px; margin-bottom:-10px;">👑 AI S-CLASS 추천</div>', unsafe_allow_html=True)
            if st.button(f"🔥 {item['title']}", key=f"s_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = get_ai_analysis(item['link'])
                    st.session_state.res = {"title": item['title'], "text": t, "analysis": a}
        else:
            if st.button(f"[{i+1}] {item['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('분석 중...'):
                    t, a = get_ai_analysis(item['link'])
                    st.session_state.res = {"title": item['title'], "text": t, "analysis": a}

with right:
    st.subheader("📊 AI 분석 및 기사 전문")
    if "res" in st.session_state:
        st.success(f"**💡 AI 요약 및 키워드**\n\n{st.session_state.res['analysis']}")
        st.divider()
        st.info(f"**제목: {st.session_state.res['title']}**")
        st.text_area("기사 전문", st.session_state.res['text'], height=550)
    else:
        st.info("👈 왼쪽에서 뉴스를 골라주세요. AI가 즉시 분석합니다.")
