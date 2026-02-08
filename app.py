import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정 (404 에러 방지를 위한 범용 설정)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # 모델명을 'models/gemini-1.5-flash'로 명시하여 경로 에러 방지
    model = genai.GenerativeModel('models/gemini-1.5-flash')
except Exception as e:
    st.error(f"API 설정 오류: {e}")

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- 뉴스 수집 함수 ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
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

    # TOP 5 소재 선별 (에러 시 상위 5개 대체)
    try:
        titles_list = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:40])])
        prompt = f"유튜브 조회수 대박날 소재 5개의 번호만 골라줘(쉼표 구분): {titles_list}"
        resp = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in resp.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = [0, 1, 2, 3, 4]
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

# --- AI 분석 함수 (강화된 예외 처리) ---
def get_ai_analysis(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 뉴스 본문 추출 (가장 확률 높은 태그 순)
        content = soup.find('article', id='dic_area') or \
                  soup.find('div', id='newsct_article') or \
                  soup.find('div', id='articleBodyContents')
        
        if not content:
            return "본문 수집 실패 (네이버 뉴스 전용 형식 아님)", "분석 불가"
            
        text = content.get_text(strip=True)
        
        # AI 요약 요청
        analysis_prompt = f"다음 뉴스를 보고 [핵심 요약 2줄]과 [주요 키워드 5개]를 뽑아줘:\n\n{text[:2000]}"
        resp = model.generate_content(analysis_prompt)
        return text, resp.text
    except Exception as e:
        return f"데이터 로드 실패: {str(e)}", f"AI 분석 중 에러가 발생했습니다: {str(e)}"

# --- 화면 구성 ---
st.title("🔥 VIRAL RANKING MASTER")
st.markdown("### 🚀 실시간 통합 랭킹 : AI 선정 바이럴 S-CLASS")

l, r = st.columns([1, 1.2])

with l:
    if st.button("🔄 리스트 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    data = get_viral_top_100()
    
    for i, row in enumerate(data):
        if row['is_s']:
            st.markdown(f"""
                <div style="background-color: #FFD700; padding: 5px 10px; border-radius: 5px; border: 2px solid #FF8C00; margin-bottom: -10px;">
                    <b style="color: black; font-size: 13px;">👑 AI S-CLASS 바이럴 추천</b>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"🔥 {row['title']}", key=f"s_{i}", use_container_width=True):
                with st.spinner('AI 분석 중...'):
                    text, analysis = get_ai_analysis(row['link'])
                    st.session_state.cur_title = row['title']
                    st.session_state.cur_text = text
                    st.session_state.cur_analysis = analysis
            st.write("")
        else:
            if st.button(f"[{i+1}] {row['title']}", key=f"n_{i}", use_container_width=True):
                with st.spinner('일반 분석 중...'):
                    text, analysis = get_ai_analysis(row['link'])
                    st.session_state.cur_title = row['title']
                    st.session_state.cur_text = text
                    st.session_state.cur_analysis = analysis

with r:
    st.subheader("📄 AI 분석 리포트")
    if 'cur_title' in st.session_state:
        st.markdown("#### 💡 핵심 요약 및 키워드")
        st.success(st.session_state.cur_analysis)
        
        st.divider()
        st.info(f"**제목: {st.session_state.cur_title}**")
        st.text_area("기사 본문 (전체)", st.session_state.cur_text, height=500)
    else:
        st.info("👈 왼쪽 리스트에서 뉴스를 선택하면 AI 분석이 시작됩니다.")
