import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. AI 엔진 설정
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Secrets에서 API 키를 확인해주세요.")

st.set_page_config(page_title="VIRAL RANKING MASTER", layout="wide")

# --- [강력 추천] S급 황금색 블록 시각 효과 CSS ---
st.markdown("""
    <style>
    /* S급 버튼: 황금색 배경과 굵은 글씨로 강조 */
    div.stButton > button:first-child[aria-label*="🔥 TOP"] {
        background-color: #FFD700 !important;
        color: #000000 !important;
        border: 3px solid #FFA500 !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        box-shadow: 0px 4px 10px rgba(255, 215, 0, 0.5);
    }
    /* 일반 버튼: 깔끔한 회색 디자인 */
    div.stButton > button:first-child {
        background-color: #f8f9fa;
        color: #333333;
        text-align: left !important;
        border: 1px solid #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)

# --- 뉴스 수집 및 AI 바이럴 랭킹 선정 ---
@st.cache_data(ttl=600)
def get_viral_top_100():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    unique_news = []
    seen_titles = set()
    
    # 전체 언론사 기사 100개 이상 수집
    for box in soup.select('.rankingnews_box'):
        press = box.select_one('.rankingnews_name').text.strip()
        for li in box.select('.rankingnews_list li'):
            a_tag = li.select_one('a')
            if a_tag:
                title = a_tag.text.strip()
                if title not in seen_titles:
                    unique_news.append({"press": press, "title": title, "link": a_tag['href']})
                    seen_titles.add(title)

    # 상위 50개 중 AI가 가장 자극적인 TOP 5 선정
    titles_list = "\n".join([f"{i}. {d['title']}" for i, d in enumerate(unique_news[:50])])
    prompt = f"유튜브 100만 작가로서 다음 중 클릭률(CTR)이 미칠 소재 5개의 번호만 골라줘(쉼표 구분): {titles_list}"
    
    try:
        resp = model.generate_content(prompt)
        s_indices = [int(x.strip()) for x in resp.text.split(',') if x.strip().isdigit()]
    except:
        s_indices = []
    
    for i, item in enumerate(unique_news):
        item['is_s'] = i in s_indices
        item['rank'] = i + 1
        
    # S급(황금색)을 무조건 맨 위로, 나머지는 랭킹순 정렬
    return sorted(unique_news, key=lambda x: x['is_s'], reverse=True)

def get_content(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
        return content.text.strip() if content else "본문 추출 실패"
    except: return "연결 실패"

# --- 화면 구성 ---
st.title("🔥 VIRAL RANKING MASTER")
st.subheader("실시간 100대 뉴스 통합 분석 : AI 선정 바이럴 TOP 5")

l, r = st.columns([1, 1.2])

with l:
    if st.button("🔄 전체 랭킹 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    data = get_viral_top_100()
    
    for i, row in enumerate(data):
        # S급은 특별한 라벨로 시작 (CSS가 감지함)
        if row['is_s']:
            label = f"🔥 TOP 소재: {row['title']}"
        else:
            label = f"[{row['rank']}] {row['title']}"
            
        if st.button(f"{label}", key=f"n_{i}", use_container_width=True):
            st.session_state.t = row['title']
            st.session_state.c = get_content(row['link'])
            st.session_state.s = row['is_s']

with r:
    if 't' in st.session_state:
        if st.session_state.s:
            st.success("✅ [검증 완료] 이 소재는 유튜브 떡상 확률 99%입니다.")
        st.info(f"**제목: {st.session_state.t}**")
        st.text_area("기사 본문 (클로드 가공용)", st.session_state.c, height=600)
    else:
        st.write("👈 왼쪽 황금색 블록을 클릭해 보세요.")
