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

# 페이지 설정
st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- [중요] S급 노란색 버튼을 위한 시각 효과 설정 ---
st.markdown("""
    <style>
    /* 기본 버튼 스타일 */
    .stButton > button {
        border-radius: 5px;
        height: 3em;
        transition: all 0.3s;
    }
    /* S급(🚨 아이콘 포함) 버튼만 노란색으로 강제 지정 */
    div[data-testid="stVerticalBlock"] > div:has(button:contains("🚨")) button {
        background-color: #FFEB3B !important;
        color: #000000 !important;
        border: 2px solid #FFC107 !important;
        font-weight: bold !important;
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
    # 네이버 랭킹 뉴스 섹션에서 데이터 추출
    for box in soup.select('.rankingnews_box')[:12]:
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li')[:5]:
            a_tag = li.select_one('a')
            if a_tag:
                raw_data.append({"press": press, "title": a_tag.text.strip(), "link": a_tag['href']})
    
    # AI에게 상위 뉴스 중 가장 바이럴될 소재 5개 추천 요청
    # 정확도를 위해 40개 중 선정
    titles_for_ai = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(raw_data[:40])])
    prompt = f"유튜브 조회수 100만 기획자로서 다음 뉴스 리스트 중 가장 '초바이럴'이 될 S급 소재 5개를 골라줘. 다른 설명은 생략하고 오직 선정된 뉴스의 제목만 한 줄에 하나씩 적어줘:\n{titles_for_ai}"
    
    try:
        response = model.generate_content(prompt)
        s_titles = response.text.strip().split('\n')
        for d in raw_data:
            # AI가 출력한 제목이 실제 제목에 포함되는지 매칭
            d['is_s'] = any(stitle.strip() in d['title'] for stitle in s_titles if len(stitle.strip()) > 5)
    except:
        for d in raw_data: d['is_s'] = False
        
    # S급이 리스트 최상단에 오도록 정렬
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
    st.subheader("📊 실시간 뉴스 (🚨: AI 추천 S급)")
    if st.button("🔄 리스트 새로고침"):
        st.cache_data.clear()
        st.rerun()

    news_list = get_ranked_news_system()
    
    for i, row in enumerate(news_list):
        # S급은 🚨 아이콘을 붙여서 CSS가 인식하게 함
        btn_label = f"🚨 [S급 추천] {row['title']}" if row['is_s'] else row['title']
        
        if st.button(f"[{row['press']}] {btn_label}", key=f"btn_{i}", use_container_width=True):
            st.session_state.current_title = row['title']
            st.session_state.current_content = get_content(row['link'])
            st.session_state.current_url = row['link']
            st.session_state.is_s_class = row['is_s']

with right_col:
    st.subheader("📄 뉴스 원문 전문")
    if 'current_title' in st.session_state:
        if st.session_state.is_s_class:
            st.error("🎯 이 뉴스 소재는 유튜브에서 터질 확률이 매우 높은 S급입니다!")
        
        st.info(f"**제목: {st.session_state.current_title}**")
        st.caption(f"링크: {st.session_state.current_url}")
        st.text_area("내용 (복사해서 클로드에 붙여넣으세요)", st.session_state.current_content, height=600)
    else:
        st.write("👈 왼쪽 리스트에서 노란색 S급 버튼을 클릭해 보세요.")
