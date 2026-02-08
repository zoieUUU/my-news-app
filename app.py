import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Secrets에서 GOOGLE_API_KEY를 확인해주세요.")

# 페이지 제목 설정
st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# 버튼 스타일 커스텀 (노란색 강조를 위한 CSS)
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #ffffff;
    }
    /* S급 버튼용 스타일 */
    div[data-testid="stVerticalBlock"] > div:has(button[aria-label*="🚨"]) button {
        background-color: #FFD700 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: 2px solid #FF8C00 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 수집 및 AI 랭킹 분석 ---
@st.cache_data(ttl=600)
def get_ranked_news_system():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    raw_data = []
    for box in soup.select('.rankingnews_box')[:12]:
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li')[:5]:
            a_tag = li.select_one('a')
            if a_tag:
                raw_data.append({"press": press, "title": a_tag.text.strip(), "link": a_tag['href']})
    
    # AI에게 S급 소재 5개 추천 요청
    titles_for_ai = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(raw_data[:40])])
    prompt = f"유튜브 100만 기획자로서 다음 뉴스 중 가장 터질 소재 5개를 골라줘. 다른 설명 없이 선택한 뉴스 제목들만 한 줄에 하나씩 써줘:\n{titles_for_ai}"
    
    try:
        response = model.generate_content(prompt)
        s_titles = response.text.split('\n')
        for d in raw_data:
            # 제목이 포함되어 있는지 매칭
            d['is_s'] = any(st.strip() in d['title'] for st in s_titles if len(st.strip()) > 5)
    except:
        for d in raw_data: d['is_s'] = False
        
    return sorted(raw_data, key=lambda x: x['is_s'], reverse=True)

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문 내용을 가져올 수 없습니다."
    except:
        return "뉴스 연결에 실패했습니다."

# --- 화면 레이아웃 ---
st.title("🔥 VIRAL RANKING MASTER : 소재 발굴기")

left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.subheader("📊 실시간 랭킹 (AI S급 필터)")
    if st.button("🔄 리스트 새로고침"):
        st.cache_data.clear()
        st.rerun()

    news_list = get_ranked_news_system()
    
    for i, row in enumerate(news_list):
        # S급 표시: 🚨 아이콘을 넣어 CSS가 인식하게 함
        label = f"🚨 [S급 추천] {row['title']}" if row['is_s'] else row['title']
        
        if st.button(f"[{row['press']}] {label}", key=f"btn_{i}", use_container_width=True):
            st.session_state.current_title = row['title']
            st.session_state.current_content = get_content(row['link'])
            st.session_state.current_url = row['link']
            st.session_state.is_s_class = row['is_s']

with right_col:
    st.subheader("📄 뉴스 원문 전문")
    if 'current_title' in st.session_state:
        if st.session_state.is_s_class:
            st.warning("🎯 AI 기획자 코멘트: 이 소재는 노란색 뱃지가 붙은 '바이럴 S급'입니다. 클로드 작업 1순위!")
        
        st.info(f"**제목: {st.session_state.current_title}**")
        st.caption(f"링크: {st.session_state.current_url}")
        st.text_area("기사 본문 텍스트 (Ctrl+A로 전체 선택 가능)", st.session_state.current_content, height=550)
    else:
        st.write("👈 왼쪽 리스트에서 노란색 버튼(S급) 위주로 클릭해 보세요.")
